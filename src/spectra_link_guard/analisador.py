"""Orquestrador do Spectra Link Guard.

Junta as três etapas passivas — sintaxe (offline), protocolo/certificado
(um handshake TLS) e reputação (leitura de listas públicas) — em um único
relatório serializável.

    from spectra_link_guard import analisar_url
    relatorio = analisar_url("https://itau.seguranca-cliente.top/login")
    print(relatorio.nivel, relatorio.risco)

Nada aqui executa ação ofensiva: não há varredura de portas, não há envio de
payload, não há tentativa de autenticação. A ferramenta olha para o link do
mesmo jeito que um usuário atento olharia, só que sistematicamente.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from .models import AnaliseLink, CertificadoTLS, ResultadoReputacao
from .pontuacao import calcular
from .rede import (
    DNS,
    Hospedagem,
    RegistroDominio,
    achados_de_dns,
    achados_de_registro,
    consultar_rede,
)
from .reputacao import achados_de_reputacao, consultar_reputacao
from .sintaxe import ContextoURL, analisar_sintaxe, checklist_heuristico
from .tls import achados_de_tls, inspecionar_tls


@dataclass
class ConfiguracaoLinkGuard:
    """Parâmetros de execução. Chaves de API vêm de variáveis de ambiente.

    As chaves nunca são registradas em log nem devolvidas no relatório.
    """

    chave_gsb: str | None = None
    chave_vt: str | None = None
    chave_phishtank: str | None = None
    verificar_tls: bool = True
    verificar_reputacao: bool = True
    verificar_registro: bool = True
    timeout_tls: float = 6.0
    timeout_http: float = 8.0

    @classmethod
    def do_ambiente(cls, **sobrescritas) -> "ConfiguracaoLinkGuard":
        base = cls(
            chave_gsb=os.getenv("SPECTRA_GSB_API_KEY") or None,
            chave_vt=os.getenv("SPECTRA_VT_API_KEY") or None,
            chave_phishtank=os.getenv("SPECTRA_PHISHTANK_APP_KEY") or None,
        )
        for nome, valor in sobrescritas.items():
            setattr(base, nome, valor)
        return base


def _url_para_consulta(ctx: ContextoURL) -> str:
    """Reconstrói a URL absoluta usada nas consultas de reputação."""
    if ctx.esquema in ("http", "https"):
        return ctx.url_normalizada
    autoridade = ctx.host_ascii + (f":{ctx.porta}" if ctx.porta else "")
    cauda = ctx.caminho + (f"?{ctx.query}" if ctx.query else "")
    return f"https://{autoridade}{cauda}"


class LinkGuard:
    """Analisador reutilizável (mantém o cache de reputação entre chamadas)."""

    def __init__(self, config: ConfiguracaoLinkGuard | None = None) -> None:
        self.config = config or ConfiguracaoLinkGuard.do_ambiente()

    async def analisar(self, url: str) -> AnaliseLink:
        cfg = self.config
        ctx, achados = analisar_sintaxe(url)

        relatorio = AnaliseLink(
            url_original=ctx.url_original,
            url_normalizada=ctx.url_normalizada or None,
            host=ctx.host or None,
            dominio_registravel=ctx.dominio_registravel or None,
            checklist=checklist_heuristico(ctx, achados),
        )

        # URL irrecuperável ou esquema que sequer aponta para um site: paramos
        # aqui — não há host para consultar e não faria sentido tocar a rede.
        if not ctx.valida or not ctx.host_ascii:
            relatorio.achados = achados
            relatorio.risco, relatorio.nivel, relatorio.resumo = calcular(achados)
            return relatorio

        alvo = _url_para_consulta(ctx)

        async def _tls() -> CertificadoTLS | None:
            if not cfg.verificar_tls:
                return None
            return await inspecionar_tls(ctx, timeout=cfg.timeout_tls)

        async def _reputacao() -> list[ResultadoReputacao]:
            if not cfg.verificar_reputacao:
                return []
            return await consultar_reputacao(
                alvo,
                chave_gsb=cfg.chave_gsb,
                chave_vt=cfg.chave_vt,
                chave_phishtank=cfg.chave_phishtank,
                timeout=cfg.timeout_http,
            )

        async def _rede() -> tuple[RegistroDominio, Hospedagem, DNS] | None:
            if not cfg.verificar_registro or ctx.e_ip:
                return None
            return await consultar_rede(
                ctx.dominio_registravel, ctx.host_ascii, timeout=cfg.timeout_http
            )

        info_tls, reputacao, rede = await asyncio.gather(_tls(), _reputacao(), _rede())

        if info_tls is not None:
            relatorio.tls = info_tls
            achados += achados_de_tls(ctx, info_tls)
        if cfg.verificar_reputacao:
            relatorio.reputacao = reputacao
            achados += achados_de_reputacao(reputacao)
        if rede is not None:
            relatorio.registro, relatorio.hospedagem, relatorio.dns = rede
            achados += achados_de_registro(relatorio.registro)
            achados += achados_de_dns(relatorio.dns, relatorio.registro)

        relatorio.achados = achados
        relatorio.risco, relatorio.nivel, relatorio.resumo = calcular(achados)
        return relatorio


def analisar_url(url: str, config: ConfiguracaoLinkGuard | None = None) -> AnaliseLink:
    """Versão síncrona, para scripts e testes.

    Em código já assíncrono (FastAPI, por exemplo), use ``LinkGuard.analisar``.
    """
    return asyncio.run(LinkGuard(config).analisar(url))
