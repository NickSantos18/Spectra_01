"""Testes da camada web.

Todos rodam em modo offline (``offline: true`` no corpo), então a suíte
continua sem abrir conexão de rede nem consumir cota de API de terceiro.
O banco é isolado por teste (conftest.py).
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi", reason="extra 'web' não instalado")
from fastapi.testclient import TestClient  # noqa: E402

from spectra_link_guard.web.app import app, limitador  # noqa: E402


@pytest.fixture
def cliente() -> TestClient:
    # Estado do processo é compartilhado entre testes: zeramos antes de cada um.
    limitador._por_ip.clear()
    return TestClient(app)


def entrar(cliente: TestClient, email: str = "ana@exemplo.com.br") -> None:
    """Cria a conta e deixa a sessão no cookie deste cliente."""
    resp = cliente.post(
        "/api/auth/cadastrar",
        json={"nome": "Pessoa de Teste", "email": email, "senha": "senha-forte-123"},
    )
    assert resp.status_code == 201


def analisar(cliente: TestClient, url: str):
    return cliente.post("/api/analisar", json={"url": url, "offline": True})


# --------------------------------------------------------------------------- #
# Páginas
# --------------------------------------------------------------------------- #


def test_raiz_redireciona_para_a_entrada(cliente):
    """A raiz não serve mais painel próprio — o produto é um só."""
    resp = cliente.get("/", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"] == "/inicio"


def test_v2_antigo_aponta_para_o_painel(cliente):
    resp = cliente.get("/v2", follow_redirects=False)
    assert resp.status_code == 308
    assert resp.headers["location"] == "/painel"


@pytest.mark.parametrize("rota", ["/painel", "/painel/visao-geral", "/painel/historico", "/painel/aprender"])
def test_telas_do_painel_exigem_sessao(cliente, rota):
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


def test_visao_geral_traz_indicadores_e_graficos(cliente):
    entrar(cliente)
    html = cliente.get("/painel/visao-geral").text
    for alvo in ("kpi-total", "kpi-perigosos", "kpi-risco", "kpi-seguras",
                 "g-tempo", "g-niveis", "g-sinais", "vg-vazio"):
        assert f'id="{alvo}"' in html
    assert "visao-geral.js?v=" in html


# --------------------------------------------------------------------------- #
# Análise
# --------------------------------------------------------------------------- #


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


def test_url_vazia_e_rejeitada(cliente):
    assert cliente.post("/api/analisar", json={"url": ""}).status_code == 422


def test_url_absurdamente_longa_e_rejeitada(cliente):
    resp = cliente.post("/api/analisar", json={"url": "https://x.com/" + "a" * 4000})
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# Histórico por usuário
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "metodo,rota",
    [
        ("get", "/api/painel"),
        ("get", "/api/painel/historico"),
        ("get", "/api/painel/estatisticas"),
        ("delete", "/api/painel"),
        ("delete", "/api/painel/abcdef123456"),
    ],
)
def test_rotas_do_historico_exigem_sessao(cliente, metodo, rota):
    resp = getattr(cliente, metodo)(rota)
    assert resp.status_code == 401
    assert "erro" in resp.json()


def test_analise_sem_sessao_nao_entra_no_historico(cliente):
    analisar(cliente, "https://exemplo.com")
    entrar(cliente)
    assert cliente.get("/api/painel/historico").json() == {"itens": []}


def test_painel_acumula_historico(cliente):
    entrar(cliente)
    analisar(cliente, "https://itau.seguranca-cliente.top/senha/login")
    analisar(cliente, "https://exemplo.com")
    painel = cliente.get("/api/painel").json()
    assert painel["total"] == 2
    assert painel["perigosos"] >= 1


def test_historico_nao_guarda_a_url_completa(cliente):
    """A query pode carregar token de sessão — só host e nota são retidos."""
    entrar(cliente)
    analisar(cliente, "https://exemplo.com/pagina?token=segredo-do-usuario")
    recente = cliente.get("/api/painel").json()["recentes"][0]
    assert recente["host"] == "exemplo.com"
    assert "segredo-do-usuario" not in str(recente)
    assert set(recente) == {"id", "host", "dominio", "risco", "nivel", "quando"}


def test_api_historico_completo_tem_mesmo_formato_do_resumo(cliente):
    entrar(cliente)
    analisar(cliente, "https://exemplo.com/pagina?token=segredo-do-usuario")
    itens = cliente.get("/api/painel/historico").json()["itens"]
    assert len(itens) == 1
    assert set(itens[0]) == {"id", "host", "dominio", "risco", "nivel", "quando"}
    assert "segredo-do-usuario" not in str(itens[0])


def test_excluir_entrada_do_historico(cliente):
    entrar(cliente)
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
    entrar(cliente)
    resp = cliente.delete("/api/painel/abcdef123456")
    assert resp.status_code == 404
    assert "erro" in resp.json()


def test_excluir_id_malformado_e_rejeitado(cliente):
    # Só hexadecimal: fecha a porta para path traversal e lixo na rota.
    entrar(cliente)
    assert cliente.delete("/api/painel/..%2Fetc").status_code in (404, 422)
    assert cliente.delete("/api/painel/ZZZZ").status_code == 422


def test_cada_analise_recebe_id_proprio(cliente):
    entrar(cliente)
    analisar(cliente, "https://exemplo.com")
    analisar(cliente, "https://exemplo.com")
    ids = [r["id"] for r in cliente.get("/api/painel").json()["recentes"]]
    assert len(set(ids)) == 2


def test_um_usuario_nao_ve_nem_apaga_o_historico_do_outro(cliente):
    entrar(cliente, "ana@exemplo.com.br")
    analisar(cliente, "https://exemplo.com")
    item_da_ana = cliente.get("/api/painel/historico").json()["itens"][0]["id"]

    bruno = TestClient(app)
    entrar(bruno, "bruno@exemplo.com.br")
    assert bruno.get("/api/painel/historico").json() == {"itens": []}
    assert bruno.get("/api/painel/estatisticas").json()["total"] == 0
    assert bruno.delete(f"/api/painel/{item_da_ana}").status_code == 404

    itens_da_ana = cliente.get("/api/painel/historico").json()["itens"]
    assert [i["id"] for i in itens_da_ana] == [item_da_ana]


def test_apagar_todo_o_historico(cliente):
    entrar(cliente)
    analisar(cliente, "https://exemplo.com")
    analisar(cliente, "https://outro-exemplo.com")
    assert cliente.delete("/api/painel").status_code == 204
    assert cliente.get("/api/painel/historico").json() == {"itens": []}


def test_estatisticas_tem_o_formato_do_dashboard(cliente):
    entrar(cliente)
    analisar(cliente, "https://itau.seguranca-cliente.top/atualizar/senha")
    analisar(cliente, "https://exemplo.com")
    estat = cliente.get("/api/painel/estatisticas").json()
    assert set(estat) == {
        "total", "perigosos", "risco_medio", "pct_seguras",
        "por_nivel", "por_dia", "sinais_frequentes",
    }
    assert estat["total"] == 2
    assert len(estat["por_dia"]) == 30
    assert estat["por_dia"][-1]["total"] == 2
    assert any(s["codigo"] == "marca_em_subdominio" for s in estat["sinais_frequentes"])


# --------------------------------------------------------------------------- #
# Saúde e limite
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# Partes compartilhadas
# --------------------------------------------------------------------------- #

ITENS_DO_MENU = ["verificar", "visao-geral", "historico", "aprender"]
TELAS_DO_PAINEL = [("/painel", "verificar"), ("/painel/visao-geral", "visao-geral"),
                   ("/painel/historico", "historico"), ("/painel/aprender", "aprender")]


def test_telas_do_painel_trazem_parciais_e_marcam_o_item_ativo(cliente):
    entrar(cliente)
    for rota, ativo in TELAS_DO_PAINEL:
        html = cliente.get(rota).text
        assert "<!--PARCIAL" not in html, rota
        assert 'class="trilho"' in html, rota
        assert 'class="rodape-spectra"' in html, rota
        assert 'id="a11y-painel"' in html, rota
        assert f'data-menu="{ativo}" aria-current="page"' in html, rota
        for outro in ITENS_DO_MENU:
            if outro != ativo:
                assert f'data-menu="{outro}" aria-current' not in html, (rota, outro)


@pytest.mark.parametrize("rota", ["/inicio", "/privacidade", "/termos"])
def test_paginas_publicas_trazem_rodape_e_acessibilidade_sem_menu(cliente, rota):
    html = cliente.get(rota).text
    assert "<!--PARCIAL" not in html
    assert 'class="rodape-spectra"' in html
    assert 'id="a11y-painel"' in html
    assert 'class="trilho"' not in html


def test_rodape_e_acessibilidade_moram_so_nos_parciais():
    from spectra_link_guard.web.app import ESTATICOS

    for pagina in ESTATICOS.glob("*.html"):
        html = pagina.read_text(encoding="utf-8")
        assert 'class="rodape-spectra"' not in html, pagina.name
        assert 'id="a11y-painel"' not in html, pagina.name


@pytest.mark.parametrize("pagina,outra", [("privacidade", "termos"), ("termos", "privacidade")])
def test_rodape_marca_a_pagina_legal_atual(cliente, pagina, outra):
    html = cliente.get(f"/{pagina}").text
    assert html.count(f'data-menu="{pagina}" aria-current="page"') == 1
    assert f'data-menu="{outra}" aria-current' not in html


def test_item_da_gaveta_tambem_fica_ativo(cliente):
    entrar(cliente)
    html = cliente.get("/painel/aprender").text
    assert html.count('data-menu="aprender" aria-current="page"') == 2  # menu lateral + gaveta


def test_aba_do_celular_tambem_fica_ativa(cliente):
    entrar(cliente)
    html = cliente.get("/painel/historico").text
    assert html.count('data-menu="historico" aria-current="page"') == 2  # menu lateral + barra de abas
