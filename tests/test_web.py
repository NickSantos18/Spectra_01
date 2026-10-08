"""Testes da camada web.

Todos rodam em modo offline (``offline: true`` no corpo), então a suíte
continua sem abrir conexão de rede nem consumir cota de API de terceiro.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi", reason="extra 'web' não instalado")
from fastapi.testclient import TestClient  # noqa: E402

from spectra_link_guard.web.app import app, historico, limitador  # noqa: E402


@pytest.fixture
def cliente() -> TestClient:
    # Estado do processo é compartilhado entre testes: zeramos antes de cada um.
    historico._itens.clear()
    limitador._por_ip.clear()
    return TestClient(app)


def analisar(cliente: TestClient, url: str):
    return cliente.post("/api/analisar", json={"url": url, "offline": True})


def test_raiz_redireciona_para_a_entrada(cliente):
    """A raiz não serve mais painel próprio — o produto é um só."""
    resp = cliente.get("/", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"] == "/inicio"


def test_v2_antigo_aponta_para_o_painel(cliente):
    resp = cliente.get("/v2", follow_redirects=False)
    assert resp.status_code == 308
    assert resp.headers["location"] == "/painel"


def test_painel_exige_sessao(cliente):
    resp = cliente.get("/painel", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/inicio?erro=entre_primeiro"


@pytest.mark.parametrize("rota", ["/painel/historico", "/painel/aprender"])
def test_novas_telas_do_painel_exigem_sessao(cliente, rota):
    resp = cliente.get(rota, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/inicio?erro=entre_primeiro"


@pytest.mark.parametrize("rota", ["/privacidade", "/termos"])
def test_paginas_legais_sao_publicas(cliente, rota):
    resp = cliente.get(rota)
    assert resp.status_code == 200
    assert "Spectra" in resp.text


def test_tela_de_entrada_responde(cliente):
    resp = cliente.get("/inicio")
    assert resp.status_code == 200
    assert "inicio.js?v=" in resp.text  # ativo versionado contra cache
    for marco in ("Cadastrar-se", "Esqueci minha senha", "Aceito os", "Assistente Spectra"):
        assert marco in resp.text


def test_analise_devolve_relatorio_completo(cliente):
    resp = analisar(cliente, "https://itau.seguranca-cliente.top/atualizar/senha")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["nivel"] in ("alto", "critico")
    assert corpo["dominio_registravel"] == "seguranca-cliente.top"
    assert any(a["codigo"] == "marca_em_subdominio" for a in corpo["achados"])


def test_modo_offline_nao_traz_tls_nem_reputacao(cliente):
    corpo = analisar(cliente, "https://exemplo.com").json()
    assert corpo["tls"] is None
    assert corpo["reputacao"] == []


def test_analise_traz_checklist_heuristico(cliente):
    corpo = analisar(cliente, "https://exemplo.com").json()
    assert len(corpo["checklist"]) == 11
    assert all({"codigo", "rotulo", "passou", "motivo"} == set(c) for c in corpo["checklist"])


def test_api_historico_completo_tem_mesmo_formato_do_resumo(cliente):
    analisar(cliente, "https://exemplo.com/pagina?token=segredo-do-usuario")
    itens = cliente.get("/api/painel/historico").json()["itens"]
    assert len(itens) == 1
    assert set(itens[0]) == {"id", "host", "dominio", "risco", "nivel", "quando"}
    assert "segredo-do-usuario" not in str(itens[0])


def test_url_vazia_e_rejeitada(cliente):
    assert cliente.post("/api/analisar", json={"url": ""}).status_code == 422


def test_url_absurdamente_longa_e_rejeitada(cliente):
    resp = cliente.post("/api/analisar", json={"url": "https://x.com/" + "a" * 4000})
    assert resp.status_code == 422


def test_painel_acumula_historico(cliente):
    analisar(cliente, "https://itau.seguranca-cliente.top/senha/login")
    analisar(cliente, "https://exemplo.com")
    painel = cliente.get("/api/painel").json()
    assert painel["total"] == 2
    assert painel["perigosos"] >= 1


def test_historico_nao_guarda_a_url_completa(cliente):
    """A query pode carregar token de sessão — só host e nota são retidos."""
    analisar(cliente, "https://exemplo.com/pagina?token=segredo-do-usuario")
    recente = cliente.get("/api/painel").json()["recentes"][0]
    assert recente["host"] == "exemplo.com"
    assert "segredo-do-usuario" not in str(recente)
    assert set(recente) == {"id", "host", "dominio", "risco", "nivel", "quando"}


def test_excluir_entrada_do_historico(cliente):
    analisar(cliente, "https://exemplo.com")
    analisar(cliente, "https://outro-exemplo.com")
    recentes = cliente.get("/api/painel").json()["recentes"]
    assert len(recentes) == 2

    alvo = recentes[0]["id"]
    assert cliente.delete(f"/api/painel/{alvo}").status_code == 204

    restantes = cliente.get("/api/painel").json()
    assert restantes["total"] == 1
    assert alvo not in [r["id"] for r in restantes["recentes"]]


def test_excluir_id_inexistente_devolve_404(cliente):
    resp = cliente.delete("/api/painel/abcdef123456")
    assert resp.status_code == 404
    assert "erro" in resp.json()


def test_excluir_id_malformado_e_rejeitado(cliente):
    # Só hexadecimal: fecha a porta para path traversal e lixo na rota.
    assert cliente.delete("/api/painel/..%2Fetc").status_code in (404, 422)
    assert cliente.delete("/api/painel/ZZZZ").status_code == 422


def test_cada_analise_recebe_id_proprio(cliente):
    analisar(cliente, "https://exemplo.com")
    analisar(cliente, "https://exemplo.com")
    ids = [r["id"] for r in cliente.get("/api/painel").json()["recentes"]]
    assert len(set(ids)) == 2


def test_saude_nao_vaza_chaves(cliente):
    corpo = cliente.get("/api/saude").json()
    assert set(corpo["provedores"]) == {"google_safe_browsing", "virustotal", "phishtank"}
    # Só booleanos: nunca o valor da chave.
    assert all(isinstance(v, bool) for v in corpo["provedores"].values())


def test_limite_de_requisicoes(cliente):
    limitador._por_ip.clear()
    for _ in range(limitador.maximo):
        assert analisar(cliente, "https://exemplo.com").status_code == 200
    excedente = analisar(cliente, "https://exemplo.com")
    assert excedente.status_code == 429
    assert "erro" in excedente.json()
