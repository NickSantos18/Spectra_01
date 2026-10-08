"""Testes dos clientes de blacklist, com transporte simulado (sem rede real)."""

from __future__ import annotations

import asyncio

import httpx

from spectra_link_guard.models import Severidade, StatusReputacao
from spectra_link_guard.reputacao import (
    achados_de_reputacao,
    consultar_google_safe_browsing,
    consultar_phishtank,
    consultar_virustotal,
)

URL = "https://exemplo.test/pagina"


def cliente_falso(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def rodar(coro):
    return asyncio.run(coro)


async def _chamar(handler, funcao, chave="chave-de-teste"):
    async with cliente_falso(handler) as cliente:
        return await funcao(cliente, URL, chave)


# --------------------------------------------------------------------------- #
# Google Safe Browsing
# --------------------------------------------------------------------------- #


def test_gsb_sem_chave_nao_faz_requisicao():
    def handler(request):  # pragma: no cover - não deve ser chamado
        raise AssertionError("não deveria acessar a rede sem chave de API")

    r = rodar(_chamar(handler, consultar_google_safe_browsing, chave=None))
    assert r.status is StatusReputacao.NAO_CONFIGURADO


def test_gsb_url_listada():
    def handler(request):
        return httpx.Response(
            200, json={"matches": [{"threatType": "SOCIAL_ENGINEERING"}]}
        )

    r = rodar(_chamar(handler, consultar_google_safe_browsing))
    assert r.status is StatusReputacao.MALICIOSO
    assert r.categorias == ["SOCIAL_ENGINEERING"]


def test_gsb_url_limpa():
    r = rodar(_chamar(lambda req: httpx.Response(200, json={}), consultar_google_safe_browsing))
    assert r.status is StatusReputacao.LIMPO


def test_gsb_erro_http_vira_status_erro():
    r = rodar(_chamar(lambda req: httpx.Response(500), consultar_google_safe_browsing))
    assert r.status is StatusReputacao.ERRO


# --------------------------------------------------------------------------- #
# VirusTotal
# --------------------------------------------------------------------------- #


def test_vt_url_desconhecida():
    r = rodar(_chamar(lambda req: httpx.Response(404), consultar_virustotal))
    assert r.status is StatusReputacao.DESCONHECIDO


def test_vt_usa_somente_get_de_consulta():
    """Garante o escopo passivo: nunca submetemos a URL para análise ativa."""
    chamadas: list[str] = []

    def handler(request):
        chamadas.append(request.method)
        return httpx.Response(404)

    rodar(_chamar(handler, consultar_virustotal))
    assert chamadas == ["GET"]


def test_vt_positivos():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 7,
                            "suspicious": 1,
                            "harmless": 60,
                            "undetected": 2,
                        },
                        "categories": {"motor": "phishing"},
                    }
                }
            },
        )

    r = rodar(_chamar(handler, consultar_virustotal))
    assert r.status is StatusReputacao.MALICIOSO
    assert r.positivos == 8
    assert r.total_motores == 70


def test_vt_cota_excedida():
    r = rodar(_chamar(lambda req: httpx.Response(429), consultar_virustotal))
    assert r.status is StatusReputacao.ERRO
    assert "429" in (r.mensagem or "")


# --------------------------------------------------------------------------- #
# PhishTank
# --------------------------------------------------------------------------- #


def test_phishtank_confirmado():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "results": {
                    "in_database": True,
                    "valid": True,
                    "phish_detail_page": "https://phishtank.org/phish_detail.php?phish_id=1",
                }
            },
        )

    r = rodar(_chamar(handler, consultar_phishtank))
    assert r.status is StatusReputacao.MALICIOSO
    assert r.referencia.endswith("phish_id=1")


def test_phishtank_fora_da_base():
    handler = lambda req: httpx.Response(200, json={"results": {"in_database": False}})  # noqa: E731
    r = rodar(_chamar(handler, consultar_phishtank))
    assert r.status is StatusReputacao.DESCONHECIDO


# --------------------------------------------------------------------------- #
# Tradução em achados
# --------------------------------------------------------------------------- #


def test_achado_critico_quando_alguem_lista_como_malicioso():
    from spectra_link_guard.models import ResultadoReputacao

    resultados = [
        ResultadoReputacao("virustotal", StatusReputacao.MALICIOSO, categorias=["phishing"]),
        ResultadoReputacao("phishtank", StatusReputacao.DESCONHECIDO),
    ]
    achados = achados_de_reputacao(resultados)
    assert achados[0].codigo == "listado_como_malicioso"
    assert achados[0].severidade is Severidade.CRITICA


def test_sem_provedor_configurado_gera_apenas_aviso_informativo():
    from spectra_link_guard.models import ResultadoReputacao

    resultados = [
        ResultadoReputacao("virustotal", StatusReputacao.NAO_CONFIGURADO),
        ResultadoReputacao("phishtank", StatusReputacao.NAO_CONFIGURADO),
    ]
    achados = achados_de_reputacao(resultados)
    assert achados[0].codigo == "reputacao_indisponivel"
    assert achados[0].severidade is Severidade.INFO
