"""Etapa 3 — Consulta a listas públicas de reputação.

ESCOPO: apenas **leitura** de bases públicas mantidas por terceiros
(Google Safe Browsing, VirusTotal, PhishTank). Enviamos a URL a ser checada e
lemos o veredito já publicado. Em nenhum momento pedimos a esses serviços que
*visitem*, *baixem* ou *analisem ativamente* o alvo — o cliente do VirusTotal,
por exemplo, usa deliberadamente o endpoint de consulta (``GET /urls/{id}``) e
nunca o de submissão (``POST /urls``), que dispararia uma coleta no site.

Sem chave de API configurada, cada provedor devolve ``NAO_CONFIGURADO`` e a
análise segue normalmente com as etapas 1 e 2.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import time
from dataclasses import dataclass, field

import httpx

from .models import Achado, ResultadoReputacao, Severidade, StatusReputacao

_GSB_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
_VT_URL = "https://www.virustotal.com/api/v3/urls/{id}"
_PHISHTANK_URL = "https://checkurl.phishtank.com/checkurl/"


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #


@dataclass
class _CacheTTL:
    """Cache em memória para poupar cota das APIs e evitar consultas repetidas.

    Guarda apenas o hash da URL como chave — nada que identifique o usuário.
    """

    ttl: float = 900.0
    _itens: dict[str, tuple[float, ResultadoReputacao]] = field(default_factory=dict)

    def obter(self, chave: str) -> ResultadoReputacao | None:
        item = self._itens.get(chave)
        if not item:
            return None
        gravado_em, valor = item
        if time.monotonic() - gravado_em > self.ttl:
            self._itens.pop(chave, None)
            return None
        return valor

    def gravar(self, chave: str, valor: ResultadoReputacao) -> None:
        if valor.status in (StatusReputacao.ERRO, StatusReputacao.NAO_CONFIGURADO):
            return  # não cacheia falhas transitórias
        self._itens[chave] = (time.monotonic(), valor)


def _chave(provedor: str, url: str) -> str:
    return f"{provedor}:{hashlib.sha256(url.encode('utf-8')).hexdigest()}"


# --------------------------------------------------------------------------- #
# Provedores
# --------------------------------------------------------------------------- #


async def consultar_google_safe_browsing(
    cliente: httpx.AsyncClient, url: str, chave_api: str | None
) -> ResultadoReputacao:
    """Google Safe Browsing v4 — ``threatMatches:find`` (somente leitura).

    Documentação: https://developers.google.com/safe-browsing/v4/lookup-api
    """
    provedor = "google_safe_browsing"
    if not chave_api:
        return ResultadoReputacao(
            provedor, StatusReputacao.NAO_CONFIGURADO,
            mensagem="Defina SPECTRA_GSB_API_KEY para habilitar.",
        )
    corpo = {
        "client": {"clientId": "spectra-link-guard", "clientVersion": "0.1.0"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION",
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }
    try:
        resp = await cliente.post(_GSB_URL, params={"key": chave_api}, json=corpo)
        resp.raise_for_status()
        dados = resp.json()
    except httpx.HTTPError as exc:
        return ResultadoReputacao(provedor, StatusReputacao.ERRO, mensagem=str(exc))

    ocorrencias = dados.get("matches") or []
    if not ocorrencias:
        # Resposta vazia = não consta nas listas do Google (não é prova de idoneidade).
        return ResultadoReputacao(
            provedor, StatusReputacao.LIMPO, mensagem="Sem correspondência nas listas do Google."
        )
    categorias = sorted({m.get("threatType", "DESCONHECIDO") for m in ocorrencias})
    return ResultadoReputacao(
        provedor,
        StatusReputacao.MALICIOSO,
        categorias=categorias,
        mensagem="URL listada pelo Google Safe Browsing.",
        referencia="https://transparencyreport.google.com/safe-browsing/search",
    )


def _id_virustotal(url: str) -> str:
    """Identificador da URL no VirusTotal: base64url sem preenchimento."""
    return base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").strip("=")


async def consultar_virustotal(
    cliente: httpx.AsyncClient, url: str, chave_api: str | None
) -> ResultadoReputacao:
    """VirusTotal v3 — leitura do relatório já existente para a URL.

    Usa apenas ``GET /api/v3/urls/{id}``. Um 404 significa "esta URL nunca foi
    submetida"; **não** submetemos, para não provocar uma coleta ativa no alvo.
    """
    provedor = "virustotal"
    if not chave_api:
        return ResultadoReputacao(
            provedor, StatusReputacao.NAO_CONFIGURADO,
            mensagem="Defina SPECTRA_VT_API_KEY para habilitar.",
        )
    try:
        resp = await cliente.get(
            _VT_URL.format(id=_id_virustotal(url)), headers={"x-apikey": chave_api}
        )
        if resp.status_code == 404:
            return ResultadoReputacao(
                provedor, StatusReputacao.DESCONHECIDO,
                mensagem="URL ainda não catalogada pelo VirusTotal.",
            )
        if resp.status_code == 429:
            return ResultadoReputacao(
                provedor, StatusReputacao.ERRO, mensagem="Cota da API excedida (429)."
            )
        resp.raise_for_status()
        atributos = resp.json()["data"]["attributes"]
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        return ResultadoReputacao(provedor, StatusReputacao.ERRO, mensagem=str(exc))

    estatisticas = atributos.get("last_analysis_stats", {}) or {}
    maliciosos = int(estatisticas.get("malicious", 0))
    suspeitos = int(estatisticas.get("suspicious", 0))
    total = sum(int(v) for v in estatisticas.values()) or None
    positivos = maliciosos + suspeitos
    categorias = sorted({str(c) for c in (atributos.get("categories") or {}).values()})
    referencia = f"https://www.virustotal.com/gui/url/{_id_virustotal(url)}"

    if positivos > 0:
        return ResultadoReputacao(
            provedor, StatusReputacao.MALICIOSO,
            categorias=categorias, positivos=positivos, total_motores=total,
            mensagem=f"{positivos} de {total} motores classificam como nocivo.",
            referencia=referencia,
        )
    return ResultadoReputacao(
        provedor, StatusReputacao.LIMPO,
        categorias=categorias, positivos=0, total_motores=total,
        mensagem="Nenhum motor sinalizou a URL.", referencia=referencia,
    )


async def consultar_phishtank(
    cliente: httpx.AsyncClient, url: str, chave_app: str | None
) -> ResultadoReputacao:
    """PhishTank — base colaborativa de páginas de phishing confirmadas.

    A API exige uma ``app_key`` (cadastro em phishtank.org). Sem chave, o
    provedor é simplesmente ignorado.
    """
    provedor = "phishtank"
    if not chave_app:
        return ResultadoReputacao(
            provedor, StatusReputacao.NAO_CONFIGURADO,
            mensagem="Defina SPECTRA_PHISHTANK_APP_KEY para habilitar.",
        )
    dados = {
        "url": base64.b64encode(url.encode("utf-8")).decode("ascii"),
        "format": "json",
        "app_key": chave_app,
    }
    try:
        resp = await cliente.post(
            _PHISHTANK_URL, data=dados, headers={"User-Agent": "phishtank/spectra-link-guard"}
        )
        resp.raise_for_status()
        resultado = resp.json().get("results", {})
    except (httpx.HTTPError, ValueError) as exc:
        return ResultadoReputacao(provedor, StatusReputacao.ERRO, mensagem=str(exc))

    if not resultado.get("in_database"):
        return ResultadoReputacao(
            provedor, StatusReputacao.DESCONHECIDO, mensagem="URL não consta na base."
        )
    if resultado.get("valid"):
        return ResultadoReputacao(
            provedor, StatusReputacao.MALICIOSO,
            categorias=["phishing"],
            mensagem="Phishing confirmado por revisores do PhishTank.",
            referencia=resultado.get("phish_detail_page"),
        )
    return ResultadoReputacao(
        provedor, StatusReputacao.LIMPO, mensagem="Consta na base, mas não confirmado."
    )


# --------------------------------------------------------------------------- #
# Orquestração e tradução em achados
# --------------------------------------------------------------------------- #


def achados_de_reputacao(resultados: list[ResultadoReputacao]) -> list[Achado]:
    """Converte os vereditos das listas públicas em achados."""
    achados: list[Achado] = []
    maliciosos = [r for r in resultados if r.malicioso]
    if maliciosos:
        provedores = ", ".join(r.provedor for r in maliciosos)
        categorias = sorted({c for r in maliciosos for c in r.categorias})
        achados.append(
            Achado(
                codigo="listado_como_malicioso",
                titulo="Endereço já denunciado em lista pública de ameaças",
                severidade=Severidade.CRITICA,
                detalhe=(
                    f"Marcado por: {provedores}."
                    + (f" Categorias: {', '.join(categorias)}." if categorias else "")
                ),
                recomendacao="Não abra o link e alerte quem o enviou.",
                evidencia={
                    "provedores": [r.provedor for r in maliciosos],
                    "categorias": categorias,
                    "referencias": [r.referencia for r in maliciosos if r.referencia],
                },
            )
        )
        return achados

    consultados = [
        r for r in resultados
        if r.status in (StatusReputacao.LIMPO, StatusReputacao.DESCONHECIDO)
    ]
    if not consultados:
        achados.append(
            Achado(
                codigo="reputacao_indisponivel",
                titulo="Não foi possível consultar as listas de ameaças",
                severidade=Severidade.INFO,
                detalhe="Nenhum provedor de reputação respondeu ou estava configurado.",
                recomendacao="A análise ficou restrita à estrutura da URL e ao certificado.",
                evidencia={"status": [r.status.value for r in resultados]},
            )
        )
    return achados


async def consultar_reputacao(
    url: str,
    *,
    chave_gsb: str | None = None,
    chave_vt: str | None = None,
    chave_phishtank: str | None = None,
    timeout: float = 8.0,
    cache: _CacheTTL | None = None,
) -> list[ResultadoReputacao]:
    """Consulta todos os provedores configurados em paralelo."""
    cache = cache if cache is not None else _CACHE_PADRAO
    tarefas: dict[str, tuple] = {
        "google_safe_browsing": (consultar_google_safe_browsing, chave_gsb),
        "virustotal": (consultar_virustotal, chave_vt),
        "phishtank": (consultar_phishtank, chave_phishtank),
    }

    resultados: list[ResultadoReputacao] = []
    pendentes: list[tuple[str, object]] = []

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as cliente:
        for nome, (funcao, chave) in tarefas.items():
            em_cache = cache.obter(_chave(nome, url))
            if em_cache is not None:
                resultados.append(em_cache)
                continue
            pendentes.append((nome, funcao(cliente, url, chave)))

        if pendentes:
            obtidos = await asyncio.gather(
                *(coro for _, coro in pendentes), return_exceptions=True
            )
            for (nome, _), obtido in zip(pendentes, obtidos):
                if isinstance(obtido, BaseException):
                    obtido = ResultadoReputacao(
                        nome, StatusReputacao.ERRO, mensagem=repr(obtido)
                    )
                cache.gravar(_chave(nome, url), obtido)
                resultados.append(obtido)

    return resultados


#: Cache compartilhado pelo processo (TTL de 15 minutos).
_CACHE_PADRAO = _CacheTTL()
