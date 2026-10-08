"""Aplicação web do Spectra Link Guard.

Serve duas coisas:

  * a API JSON (``/api/...``) que expõe o analisador passivo;
  * o painel estático (``/``), a versão funcional do protótipo do Stitch.

Rodar em desenvolvimento::

    uvicorn spectra_link_guard.web.app:app --reload --port 8000

A análise usa a configuração padrão — ou seja, **com** handshake TLS e **com**
consulta às listas públicas de reputação. O modo offline continua disponível
por requisição (campo ``offline`` do corpo), mas não é o padrão.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException, Path as ParamPath, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import __version__
from ..analisador import ConfiguracaoLinkGuard, LinkGuard
from ..auth import bd as bd_auth
from ..auth import router as router_auth
from ..auth import usuario_atual
from . import analises

ESTATICOS = Path(__file__).parent / "static"

#: Ativos que toda página carrega; entram no cache-busting de _pagina().
_ATIVOS_BASE = ("tokens.css", "rodape.css", "movimento.js", "acessibilidade.js")

#: Ativos das telas com menu lateral (painel).
_ATIVOS_PAINEL = _ATIVOS_BASE + ("laudo.css", "menu.js")

#: Partes de HTML compartilhadas, encaixadas por _pagina() no lugar de
#: <!--PARCIAL:nome-->. Ficam fora de static/: não são servidas sozinhas.
PARCIAIS = Path(__file__).parent / "parciais"
_MARCADOR_PARCIAL = re.compile(r"<!--PARCIAL:([a-z-]+)-->")

#: Limite por IP: a análise consome cota de APIs de terceiros e abre uma
#: conexão TLS por chamada, então o endpoint precisa de freio.
_JANELA_S = 300.0
_MAX_POR_JANELA = 30


@dataclass
class _Limitador:
    """Janela deslizante simples, em memória. Suficiente para um processo só.

    Em produção com várias réplicas, troque por Redis ou pelo rate limit do
    proxy reverso (nginx / Cloudflare).
    """

    janela: float = _JANELA_S
    maximo: int = _MAX_POR_JANELA

    def __post_init__(self) -> None:
        self._por_ip: dict[str, deque[float]] = {}
        self._trava = Lock()

    def permitido(self, ip: str) -> bool:
        agora = time.monotonic()
        with self._trava:
            marcas = self._por_ip.setdefault(ip, deque())
            while marcas and agora - marcas[0] > self.janela:
                marcas.popleft()
            if len(marcas) >= self.maximo:
                return False
            marcas.append(agora)
            return True


limitador = _Limitador()
guard = LinkGuard()


def _usuario_ou_401(request: Request) -> dict[str, Any]:
    """Dono da sessão, ou 401: o histórico é sempre de alguém."""
    usuario = usuario_atual(request.cookies.get("spectra_sessao"))
    if usuario is None:
        raise HTTPException(status_code=401, detail="Entre na sua conta para ver o histórico.")
    return usuario


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    """Prepara o banco na subida e limpa sessões vencidas."""
    bd_auth.preparar()
    bd_auth.limpar_sessoes_vencidas()
    yield


app = FastAPI(
    lifespan=ciclo_de_vida,
    title="Spectra Link Guard",
    version=__version__,
    description=(
        "Análise passiva de risco de links para proteção ao consumidor. "
        "Não realiza invasão, varredura de portas nem exploração de falhas."
    ),
)


app.include_router(router_auth, tags=["acesso"])


class PedidoAnalise(BaseModel):
    url: str = Field(min_length=1, max_length=2048, description="Link a analisar")
    offline: bool = Field(
        default=False,
        description="Se verdadeiro, só a etapa sintática: não abre conexão nem consulta APIs.",
    )


@app.post("/api/analisar", summary="Analisa um link de forma passiva")
async def analisar(pedido: PedidoAnalise, request: Request) -> dict[str, Any]:
    ip = request.client.host if request.client else "desconhecido"
    if not limitador.permitido(ip):
        raise HTTPException(
            status_code=429,
            detail="Muitas análises em pouco tempo. Aguarde alguns minutos.",
        )

    if pedido.offline:
        config = ConfiguracaoLinkGuard.do_ambiente(
            verificar_tls=False, verificar_reputacao=False, verificar_registro=False
        )
        relatorio = await LinkGuard(config).analisar(pedido.url)
    else:
        relatorio = await guard.analisar(pedido.url)

    # Sem sessão (CLI, testes, integração) a análise funciona, mas não é salva.
    usuario = usuario_atual(request.cookies.get("spectra_sessao"))
    if usuario is not None:
        await asyncio.to_thread(analises.registrar, usuario["id"], relatorio)
    return relatorio.to_dict()


@app.get("/api/painel", summary="Indicadores do usuário")
async def painel(request: Request) -> dict[str, Any]:
    usuario = _usuario_ou_401(request)
    return await asyncio.to_thread(analises.resumo, usuario["id"])


@app.get("/api/painel/historico", summary="Histórico completo do usuário")
async def historico_completo(request: Request) -> dict[str, Any]:
    """Todas as análises guardadas (até 500), para busca e filtro na tela de Histórico."""
    usuario = _usuario_ou_401(request)
    return {"itens": await asyncio.to_thread(analises.listar, usuario["id"])}


@app.get("/api/painel/estatisticas", summary="Números da Visão geral")
async def estatisticas(request: Request) -> dict[str, Any]:
    usuario = _usuario_ou_401(request)
    return await asyncio.to_thread(analises.estatisticas, usuario["id"])


@app.delete("/api/painel", status_code=204, summary="Apaga todo o histórico do usuário")
async def apagar_historico(request: Request) -> Response:
    usuario = _usuario_ou_401(request)
    await asyncio.to_thread(analises.remover_todas, usuario["id"])
    return Response(status_code=204)


@app.delete(
    "/api/painel/{item_id}",
    status_code=204,
    summary="Remove uma análise do histórico do usuário",
)
async def remover_do_historico(
    request: Request,
    item_id: str = ParamPath(min_length=1, max_length=32, pattern=r"^[0-9a-f]+$"),
) -> Response:
    usuario = _usuario_ou_401(request)
    # 404 também quando o item é de outra pessoa: não revela que ele existe.
    if not await asyncio.to_thread(analises.remover, usuario["id"], item_id):
        raise HTTPException(status_code=404, detail="Entrada não encontrada.")
    return Response(status_code=204)


@app.get("/api/saude", summary="Estado do serviço e dos provedores")
async def saude() -> dict[str, Any]:
    cfg = guard.config
    return {
        "versao": __version__,
        "modo": "online",
        "verificar_tls": cfg.verificar_tls,
        "verificar_reputacao": cfg.verificar_reputacao,
        # Apenas se a chave existe — o valor nunca é exposto.
        "provedores": {
            "google_safe_browsing": bool(cfg.chave_gsb),
            "virustotal": bool(cfg.chave_vt),
            "phishtank": bool(cfg.chave_phishtank),
        },
    }


@app.exception_handler(HTTPException)
async def erro_json(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"erro": exc.detail})


@app.middleware("http")
async def revalidar_estaticos(request: Request, proximo):
    """`no-cache` no painel e nos estáticos.

    Não é "não guarde": é "guarde, mas revalide sempre". Com o ETag que o
    Starlette já emite, a resposta vira 304 quando nada mudou — barato — e uma
    edição no CSS aparece no primeiro F5, sem precisar limpar o cache.
    """
    resposta = await proximo(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        resposta.headers["Cache-Control"] = "no-cache"
    return resposta


def _pagina(arquivo: str, *ativos: str, menu: str | None = None) -> HTMLResponse:
    """Serve uma página: encaixa os parciais, marca o item ativo do menu e
    injeta ?v=<mtime> nos ativos que ela referencia (cache-busting)."""
    html = (ESTATICOS / arquivo).read_text(encoding="utf-8")
    html = _MARCADOR_PARCIAL.sub(
        lambda marcador: (PARCIAIS / f"{marcador.group(1)}.html").read_text(encoding="utf-8"),
        html,
    )
    if menu is not None:
        html = html.replace(f'data-menu="{menu}"', f'data-menu="{menu}" aria-current="page"')
    for ativo in ativos:
        html = html.replace(f"/static/{ativo}", f"/static/{ativo}?v={_carimbo(ativo)}")
    return HTMLResponse(html)


def _carimbo(nome: str) -> str:
    """Timestamp do arquivo, usado para invalidar o cache do navegador."""
    try:
        return str(int((ESTATICOS / nome).stat().st_mtime))
    except OSError:  # pragma: no cover - arquivo removido em runtime
        return "0"


@app.get("/", include_in_schema=False)
async def raiz() -> RedirectResponse:
    """A raiz não serve mais painel próprio — a porta de entrada é /inicio."""
    return RedirectResponse("/inicio", status_code=307)


@app.get("/inicio", include_in_schema=False)
async def inicio() -> HTMLResponse:
    """Porta de entrada: hero, acesso e assistente."""
    return _pagina("inicio.html", *_ATIVOS_BASE, "caminhos.js", "inicio.js", "cubos.js")


@app.get("/painel", include_in_schema=False)
async def painel_app(request: Request) -> Response:
    """O produto: verificar um link. Sem sessão, volta para a porta de entrada."""
    if usuario_atual(request.cookies.get("spectra_sessao")) is None:
        return RedirectResponse("/inicio?erro=entre_primeiro", status_code=303)
    return _pagina(
        "laudo.html", *_ATIVOS_PAINEL,
        "glossario.js", "caminhos.js", "melhorias.js", "laudo.js", menu="verificar",
    )


@app.get("/painel/historico", include_in_schema=False)
async def painel_historico(request: Request) -> Response:
    """Histórico das análises do usuário."""
    if usuario_atual(request.cookies.get("spectra_sessao")) is None:
        return RedirectResponse("/inicio?erro=entre_primeiro", status_code=303)
    return _pagina("historico.html", *_ATIVOS_PAINEL, "historico.js", menu="historico")


@app.get("/painel/aprender", include_in_schema=False)
async def painel_aprender(request: Request) -> Response:
    """Conteúdo educativo sobre phishing e leitura de URLs."""
    if usuario_atual(request.cookies.get("spectra_sessao")) is None:
        return RedirectResponse("/inicio?erro=entre_primeiro", status_code=303)
    return _pagina("aprender.html", *_ATIVOS_PAINEL, "glossario.js", menu="aprender")


@app.get("/privacidade", include_in_schema=False)
async def privacidade() -> HTMLResponse:
    """Política de Privacidade — texto modelo, editável em static/privacidade.html."""
    return _pagina("privacidade.html", *_ATIVOS_BASE, "laudo.css")


@app.get("/termos", include_in_schema=False)
async def termos() -> HTMLResponse:
    """Termos de Uso — texto modelo, editável em static/termos.html."""
    return _pagina("termos.html", *_ATIVOS_BASE, "laudo.css")


@app.get("/v2", include_in_schema=False)
async def v2_antigo() -> RedirectResponse:
    """Endereço antigo — mantido só para não quebrar link já compartilhado."""
    return RedirectResponse("/painel", status_code=308)


app.mount("/static", StaticFiles(directory=ESTATICOS), name="static")
