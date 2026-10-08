"""Testes de ponta a ponta do orquestrador, sempre em modo offline.

O modo offline (``verificar_tls=False``, ``verificar_reputacao=False``) é o que
garante que a suíte não abra nenhuma conexão — importante tanto para CI quanto
para deixar explícito que a ferramenta funciona sem tocar em servidor de
terceiro.
"""

from __future__ import annotations

import json

from spectra_link_guard import ConfiguracaoLinkGuard, NivelRisco, analisar_url
from spectra_link_guard.models import CertificadoTLS, Severidade
from spectra_link_guard.sintaxe import normalizar
from spectra_link_guard.tls import achados_de_tls

OFFLINE = ConfiguracaoLinkGuard(
    verificar_tls=False, verificar_reputacao=False, verificar_registro=False
)


def analisar(url: str):
    return analisar_url(url, OFFLINE)


def test_link_legitimo_fica_em_risco_baixo():
    r = analisar("https://www.itau.com.br/pf/conta-corrente")
    assert r.nivel in (NivelRisco.SEGURO, NivelRisco.BAIXO)
    assert r.dominio_registravel == "itau.com.br"


def test_phishing_classico_e_critico():
    r = analisar("https://itau.seguranca-cliente.top/atualizar/senha/login")
    assert r.nivel in (NivelRisco.ALTO, NivelRisco.CRITICO)
    assert r.risco >= 55
    assert {"marca_em_subdominio", "tld_de_risco"} <= {a.codigo for a in r.achados}


def test_relatorio_serializa_em_json():
    r = analisar("https://exemplo.com/pagina")
    bruto = json.dumps(r.to_dict(), ensure_ascii=False)
    devolta = json.loads(bruto)
    assert devolta["url_original"] == "https://exemplo.com/pagina"
    assert devolta["nivel"] == r.nivel.value
    assert isinstance(devolta["achados"], list)


def test_url_invalida_nao_quebra():
    r = analisar("http://[::1")
    assert r.nivel is NivelRisco.CRITICO
    assert r.achados[0].codigo == "url_invalida"


def test_esquema_javascript_nao_dispara_rede():
    # Config online, mas o esquema não tem host: o analisador precisa parar antes.
    r = analisar_url("javascript:alert(1)", ConfiguracaoLinkGuard())
    assert r.achados[0].codigo == "esquema_perigoso"
    assert r.tls is None
    assert r.reputacao == []


def test_modo_offline_nao_preenche_tls_nem_reputacao():
    r = analisar("https://exemplo.com")
    assert r.tls is None
    assert r.reputacao == []


# --------------------------------------------------------------------------- #
# Achados derivados do certificado (com dados simulados, sem handshake real)
# --------------------------------------------------------------------------- #


def test_http_puro_gera_achado_de_falta_de_https():
    ctx = normalizar("http://exemplo.com/login")
    achados = achados_de_tls(ctx, CertificadoTLS(erro="sem tls"))
    assert achados[0].codigo == "sem_https"
    assert achados[0].severidade is Severidade.ALTA


def test_certificado_expirado():
    ctx = normalizar("https://exemplo.com")
    info = CertificadoTLS(
        disponivel=True, cadeia_valida=True, dias_para_expirar=-3,
        valido_ate="2020-01-01T00:00:00+00:00",
    )
    codigos = {a.codigo for a in achados_de_tls(ctx, info)}
    assert "certificado_expirado" in codigos


def test_certificado_com_host_divergente():
    ctx = normalizar("https://exemplo.com")
    info = CertificadoTLS(
        disponivel=True, cadeia_valida=True, host_confere=False,
        nomes_alternativos=["outro.test"],
    )
    codigos = {a.codigo for a in achados_de_tls(ctx, info)}
    assert "certificado_host_divergente" in codigos


def test_tls_obsoleto():
    ctx = normalizar("https://exemplo.com")
    info = CertificadoTLS(disponivel=True, cadeia_valida=True, versao_tls="TLSv1")
    codigos = {a.codigo for a in achados_de_tls(ctx, info)}
    assert "tls_obsoleto" in codigos


def test_certificado_saudavel_nao_gera_achado():
    ctx = normalizar("https://exemplo.com")
    info = CertificadoTLS(
        disponivel=True, cadeia_valida=True, versao_tls="TLSv1.3",
        dias_para_expirar=60, host_confere=True,
        valido_de="2020-01-01T00:00:00+00:00",
    )
    assert achados_de_tls(ctx, info) == []
