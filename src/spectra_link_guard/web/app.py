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

import time
import uuid
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
from ..models import NivelRisco

ESTATICOS = Path(__file__).parent / "static"

#: Ativos que toda página carrega; entram no cache-busting de _pagina().
_ATIVOS_BASE = ("tokens.css", "rodape.css", "movimento.js", "acessibilidade.js")

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


@dataclass
class _Historico:
    """Últimas análises da sessão, para alimentar os indicadores do painel.

    PRIVACIDADE: guarda apenas host, domínio registrável, nota e horário.
    A URL completa **não** é retida — caminho e query podem conter tokens,
    identificadores de sessão ou dados pessoais.
    """

    limite: int = 50

    def __post_init__(self) -> None:
        self._itens: deque[dict[str, Any]] = deque(maxlen=self.limite)
        self._trava = Lock()

    def registrar(self, relatorio) -> str:
        """Guarda a análise e devolve o id usado para removê-la depois."""
        item_id = uuid.uuid4().hex[:12]
        with self._trava:
            self._itens.appendleft(
                {
                    "id": item_id,
                    "host": relatorio.host,
                    "dominio": relatorio.dominio_registravel,
                    "risco": relatorio.risco,
                    "nivel": relatorio.nivel.value,
                    "quando": relatorio.analisado_em,
                }
            )
        return item_id

    def remover(self, item_id: str) -> bool:
        """Apaga uma entrada. Devolve ``False`` se o id não existia."""
        with self._trava:
            for item in self._itens:
                if item["id"] == item_id:
                    self._itens.remove(item)
                    return True
        return False

    def resumo(self) -> dict[str, Any]:
        with self._trava:
            itens = list(self._itens)
        contagem = {n.value: 0 for n in NivelRisco}
        for item in itens:
            contagem[item["nivel"]] = contagem.get(item["nivel"], 0) + 1
        perigosos = sum(
            contagem[n] for n in (NivelRisco.ALTO.value, NivelRisco.CRITICO.value)
        )
        return {
            "total": len(itens),
            "por_nivel": contagem,
            "perigosos": perigosos,
            "recentes": itens[:12],
        }

    def todos(self) -> list[dict[str, Any]]:
        """Lista completa (até `limite`), para a tela de Histórico."""
        with self._trava:
            return list(self._itens)


limitador = _Limitador()
historico = _Historico()
guard = LinkGuard()

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

    historico.registrar(relatorio)
    return relatorio.to_dict()


@app.get("/api/painel", summary="Indicadores da sessão")
async def painel() -> dict[str, Any]:
    return historico.resumo()


@app.get("/api/painel/historico", summary="Lista completa do histórico da sessão")
async def historico_completo() -> dict[str, Any]:
    """Todas as análises guardadas (até 50), para busca e filtro na tela de Histórico."""
    return {"itens": historico.todos()}


@app.delete(
    "/api/painel/{item_id}",
    status_code=204,
    summary="Remove uma análise do histórico da sessão",
)
async def remover_do_historico(
    item_id: str = ParamPath(min_length=1, max_length=32, pattern=r"^[0-9a-f]+$"),
) -> Response:
    if not historico.remover(item_id):
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


def _pagina(arquivo: str, *ativos: str) -> HTMLResponse:
    """Serve uma página injetando ?v=<mtime> nos ativos que ela referencia."""
    html = (ESTATICOS / arquivo).read_text(encoding="utf-8")
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
        "laudo.html", *_ATIVOS_BASE, "laudo.css",
        "glossario.js", "caminhos.js", "melhorias.js", "laudo.js",
    )


@app.get("/painel/historico", include_in_schema=False)
async def painel_historico(request: Request) -> Response:
    """Histórico das análises feitas nesta sessão."""
    if usuario_atual(request.cookies.get("spectra_sessao")) is None:
        return RedirectResponse("/inicio?erro=entre_primeiro", status_code=303)
    return _pagina("historico.html", *_ATIVOS_BASE, "laudo.css", "historico.js")


@app.get("/painel/aprender", include_in_schema=False)
async def painel_aprender(request: Request) -> Response:
    """Conteúdo educativo sobre phishing e leitura de URLs."""
    if usuario_atual(request.cookies.get("spectra_sessao")) is None:
        return RedirectResponse("/inicio?erro=entre_primeiro", status_code=303)
    return _pagina("aprender.html", *_ATIVOS_BASE, "laudo.css", "glossario.js")


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
