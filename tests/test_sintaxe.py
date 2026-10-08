"""Testes da etapa offline. Nenhum deles toca a rede."""

from __future__ import annotations

import pytest

from spectra_link_guard.models import Severidade
from spectra_link_guard.sintaxe import (
    analisar_sintaxe,
    distancia_damerau_levenshtein,
    dominio_registravel,
    esqueleto_visual,
    normalizar,
)


def codigos(url: str) -> set[str]:
    _, achados = analisar_sintaxe(url)
    return {a.codigo for a in achados}


def achado(url: str, codigo: str):
    _, achados = analisar_sintaxe(url)
    return next((a for a in achados if a.codigo == codigo), None)


# --------------------------------------------------------------------------- #
# Utilitários
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "host,esperado",
    [
        ("www.itau.com.br", "itau.com.br"),
        ("itau.com.br", "itau.com.br"),
        ("a.b.c.exemplo.com", "exemplo.com"),
        ("loterias.caixa.gov.br", "caixa.gov.br"),
        ("exemplo.com", "exemplo.com"),
        ("localhost", "localhost"),
    ],
)
def test_dominio_registravel(host, esperado):
    assert dominio_registravel(host) == esperado


@pytest.mark.parametrize(
    "a,b,esperado",
    [
        ("bradesco", "bradesco", 0),
        ("bradosco", "bradesco", 1),
        ("bradseco", "bradesco", 1),  # transposição
        ("nubank", "nubunk", 1),
        ("google", "microsoft", 4),   # saturado no limite+1
    ],
)
def test_distancia(a, b, esperado):
    assert distancia_damerau_levenshtein(a, b, limite=3) == esperado


def test_esqueleto_visual_colapsa_homoglifos():
    # "а" cirílico (U+0430) e o dígito 4 devem virar "a"
    assert esqueleto_visual("nubаnk") == "nubank"
    assert esqueleto_visual("nub4nk") == "nubank"
    assert esqueleto_visual("rnercadolivre") == "mercadolivre"


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


def test_url_sem_esquema_e_aceita():
    ctx = normalizar("itau.com.br/pf")
    assert ctx.valida
    assert ctx.host == "itau.com.br"
    assert ctx.esquema is None


def test_url_vazia_e_invalida():
    ctx = normalizar("   ")
    assert not ctx.valida
    assert "vazia" in (ctx.erro or "")


def test_subdominios_extraidos():
    ctx = normalizar("https://a.b.itau.com.br/x")
    assert ctx.dominio_registravel == "itau.com.br"
    assert ctx.subdominios == ["a", "b"]


# --------------------------------------------------------------------------- #
# Regras
# --------------------------------------------------------------------------- #


def test_dominio_legitimo_nao_gera_alarme_de_marca():
    encontrados = codigos("https://www.itau.com.br/pf/conta-corrente")
    assert "typosquatting" not in encontrados
    assert "marca_em_subdominio" not in encontrados


def test_typosquatting_detectado():
    a = achado("https://bradosco.com.br/login", "typosquatting")
    assert a is not None
    assert a.evidencia["oficial"] == "bradesco.com.br"
    assert a.evidencia["distancia"] == 1
    assert a.severidade is Severidade.CRITICA


def test_dominio_sosia_tem_prioridade_sobre_typosquatting():
    # "bradesc0" com zero no lugar do "o": mesma silhueta na tela.
    a = achado("https://bradesc0.com.br/login", "dominio_sosia")
    assert a is not None
    assert a.evidencia["oficial"] == "bradesco.com.br"
    assert a.severidade is Severidade.CRITICA


def test_marca_em_subdominio_de_terceiro():
    a = achado("https://itau.seguranca-cliente.top/atualizar", "marca_em_subdominio")
    assert a is not None
    assert a.evidencia["dominio_real"] == "seguranca-cliente.top"
    assert a.severidade is Severidade.ALTA


def test_userinfo_ofusca_destino():
    a = achado("https://www.itau.com.br@evil.example/login", "userinfo_no_host")
    assert a is not None
    assert a.evidencia["host_real"] == "evil.example"


def test_ip_literal():
    assert "host_ip_literal" in codigos("http://192.0.2.10/boleto")


def test_esquema_perigoso_interrompe_analise():
    encontrados = codigos("javascript:alert(document.cookie)")
    assert encontrados == {"esquema_perigoso"}


def test_encurtador():
    assert "encurtador" in codigos("https://bit.ly/3xYzAbC")


def test_url_embutida_em_parametro():
    assert "url_embutida" in codigos("https://exemplo.com/r?destino=https://evil.example")


def test_download_executavel():
    assert "download_executavel" in codigos("http://exemplo.com/nota-fiscal.exe")


def test_tld_de_risco_e_subdominios_excessivos():
    encontrados = codigos("https://a.b.c.d.pagamento.xyz/pix")
    assert "tld_de_risco" in encontrados
    assert "subdominios_excessivos" in encontrados


def test_palavras_isca():
    a = achado("https://exemplo.com/login/verificar/senha", "palavras_isca")
    assert a is not None
    assert "login" in a.evidencia["termos"]


def test_porta_incomum():
    assert "porta_incomum" in codigos("https://exemplo.com:8443/painel")


def test_url_invalida_gera_achado_critico():
    ctx, achados = analisar_sintaxe("http://[::1")
    assert not ctx.valida
    assert achados[0].codigo == "url_invalida"
    assert achados[0].severidade is Severidade.CRITICA
