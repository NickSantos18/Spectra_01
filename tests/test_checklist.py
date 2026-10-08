"""Testes da checklist heurística (item 7/8 da tela de resultado).

100% offline: reaproveita `analisar_sintaxe`, que já não toca a rede.
"""

from __future__ import annotations

from spectra_link_guard.sintaxe import analisar_sintaxe, checklist_heuristico


def linha(url: str, codigo: str):
    ctx, achados = analisar_sintaxe(url)
    checklist = checklist_heuristico(ctx, achados)
    return next(c for c in checklist if c.codigo == codigo)


def test_checklist_tem_onze_criterios():
    ctx, achados = analisar_sintaxe("https://www.itau.com.br/pf")
    assert len(checklist_heuristico(ctx, achados)) == 11


def test_checklist_vazia_para_url_invalida():
    ctx, achados = analisar_sintaxe("http://[::1")
    assert checklist_heuristico(ctx, achados) == []


def test_ip_no_lugar_do_dominio():
    c = linha("http://192.0.2.10/boleto", "ip_no_lugar_do_dominio")
    assert c.passou is False
    c_ok = linha("https://exemplo.com", "ip_no_lugar_do_dominio")
    assert c_ok.passou is True


def test_arroba_na_url():
    c = linha("https://www.itau.com.br@evil.example/login", "arroba_na_url")
    assert c.passou is False
    assert "evil.example" in c.motivo


def test_excesso_de_subdominios():
    c = linha("https://a.b.c.d.pagamento.xyz/pix", "excesso_de_subdominios")
    assert c.passou is False
    c_ok = linha("https://exemplo.com", "excesso_de_subdominios")
    assert c_ok.passou is True


def test_excesso_de_hifens():
    c = linha("https://oferta-imperdivel-clique-aqui.com/x", "excesso_de_hifens")
    assert c.passou is False


def test_url_muito_longa():
    longa = "https://exemplo.com/" + "a" * 120
    c = linha(longa, "url_muito_longa")
    assert c.passou is False
    c_ok = linha("https://exemplo.com", "url_muito_longa")
    assert c_ok.passou is True


def test_ausencia_de_https():
    c = linha("http://exemplo.com/login", "ausencia_de_https")
    assert c.passou is False
    c_ok = linha("https://exemplo.com/login", "ausencia_de_https")
    assert c_ok.passou is True


def test_tld_suspeito():
    c = linha("https://pagamento.xyz/pix", "tld_suspeito")
    assert c.passou is False
    c_ok = linha("https://exemplo.com.br", "tld_suspeito")
    assert c_ok.passou is True


def test_palavras_de_phishing_qualquer_ocorrencia():
    # Um único termo já falha aqui, diferente do achado `palavras_isca` (>=2).
    c = linha("https://exemplo.com/login", "palavras_de_phishing")
    assert c.passou is False
    assert "login" in c.motivo


def test_imitacao_de_marca():
    c = linha("https://bradosco.com.br/login", "imitacao_de_marca")
    assert c.passou is False
    c_ok = linha("https://www.itau.com.br/pf", "imitacao_de_marca")
    assert c_ok.passou is True


def test_punycode():
    c = linha("https://xn--ggle-0nda.com", "punycode")
    assert c.passou is False


def test_encurtador_de_link():
    c = linha("https://bit.ly/3xYzAbC", "encurtador_de_link")
    assert c.passou is False
    c_ok = linha("https://exemplo.com", "encurtador_de_link")
    assert c_ok.passou is True
