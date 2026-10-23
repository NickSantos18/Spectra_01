"""Testes de cadastro, login, sessão e Google.

O banco é isolado por teste pelo fixture em ``conftest.py``. Nenhuma chamada
sai para a rede: o Google entra só pelos caminhos de configuração ausente.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi", reason="extra 'web' não instalado")
from fastapi.testclient import TestClient  # noqa: E402

from spectra_link_guard.auth import bd, seguranca  # noqa: E402
from spectra_link_guard.auth.rotas import freio  # noqa: E402
from spectra_link_guard.web.app import app  # noqa: E402

CONTA = {"nome": "Ana Ribeiro", "email": "ana@exemplo.com.br", "senha": "senha-forte-123"}


@pytest.fixture
def cliente() -> TestClient:
    freio._por_ip.clear()
    return TestClient(app)


def cadastrar(cliente: TestClient, **campos):
    return cliente.post("/api/auth/cadastrar", json={**CONTA, **campos})


# --------------------------------------------------------------------------- #
# Hash de senha
# --------------------------------------------------------------------------- #


def test_hash_nunca_repete_para_a_mesma_senha():
    """Sal aleatório: dois cadastros com a mesma senha geram hashes diferentes."""
    a = seguranca.gerar_hash("mesma-senha-123")
    b = seguranca.gerar_hash("mesma-senha-123")
    assert a != b
    assert seguranca.conferir_senha("mesma-senha-123", a)
    assert seguranca.conferir_senha("mesma-senha-123", b)


def test_hash_guarda_os_parametros():
    assert seguranca.gerar_hash("x" * 12).startswith("scrypt$16384$8$1$")


def test_senha_errada_nao_confere():
    guardado = seguranca.gerar_hash("certa-123456")
    assert not seguranca.conferir_senha("errada-123456", guardado)


def test_conta_sem_senha_nunca_confere():
    """Conta criada pelo Google tem senha_hash NULL e não pode logar por senha."""
    assert not seguranca.conferir_senha("qualquer-coisa", None)


def test_hash_corrompido_nao_derruba():
    assert not seguranca.conferir_senha("x", "lixo-que-nao-e-hash")


# --------------------------------------------------------------------------- #
# Cookie assinado
# --------------------------------------------------------------------------- #


def test_cookie_forjado_e_recusado():
    token = seguranca.assinar("sessao-123")
    assert seguranca.abrir_assinado(token) == "sessao-123"
    assert seguranca.abrir_assinado(token[:-4] + "AAAA") is None
    assert seguranca.abrir_assinado("sem-ponto") is None


# --------------------------------------------------------------------------- #
# Cadastro
# --------------------------------------------------------------------------- #


def test_cadastro_cria_conta_e_abre_sessao(cliente):
    resp = cadastrar(cliente)
    assert resp.status_code == 201
    assert resp.json()["usuario"]["email"] == "ana@exemplo.com.br"
    assert cliente.get("/api/auth/eu").json()["usuario"]["nome"] == "Ana Ribeiro"


def test_resposta_nunca_traz_o_hash(cliente):
    corpo = cadastrar(cliente).json()["usuario"]
    assert set(corpo) == {
        "id", "nome", "email", "email_verificado", "tem_senha", "tem_google", "criado_em"
    }


def test_email_repetido_e_recusado_ignorando_maiusculas(cliente):
    cadastrar(cliente)
    repetido = cadastrar(cliente, email="ANA@Exemplo.COM.BR", nome="Outra Pessoa")
    assert repetido.status_code == 409


def test_senha_curta_e_recusada(cliente):
    assert cadastrar(cliente, senha="curta").status_code == 422


def test_email_invalido_e_recusado(cliente):
    assert cadastrar(cliente, email="nao-e-email").status_code == 422


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #


def test_login_com_senha_certa(cliente):
    cadastrar(cliente)
    cliente.post("/api/auth/sair")
    resp = cliente.post("/api/auth/entrar", json={"email": CONTA["email"], "senha": CONTA["senha"]})
    assert resp.status_code == 200
    assert cliente.get("/api/auth/eu").json()["usuario"] is not None


def test_mensagem_e_identica_para_senha_errada_e_conta_inexistente(cliente):
    """Não revelar qual dos dois falhou — senão o login vira lista de contas."""
    cadastrar(cliente)
    cliente.post("/api/auth/sair")
    errada = cliente.post("/api/auth/entrar", json={"email": CONTA["email"], "senha": "outra-senha"})
    inexistente = cliente.post("/api/auth/entrar", json={"email": "zzz@exemplo.com", "senha": "outra-senha"})
    assert errada.status_code == inexistente.status_code == 401
    assert errada.json()["erro"] == inexistente.json()["erro"]


def test_freio_trava_apos_muitas_tentativas(cliente):
    for _ in range(8):
        cliente.post("/api/auth/entrar", json={"email": "x@exemplo.com", "senha": "errada"})
    travado = cliente.post("/api/auth/entrar", json={"email": "x@exemplo.com", "senha": "errada"})
    assert travado.status_code == 429


def test_login_certo_zera_o_freio(cliente):
    cadastrar(cliente)
    cliente.post("/api/auth/sair")
    for _ in range(5):
        cliente.post("/api/auth/entrar", json={"email": CONTA["email"], "senha": "errada"})
    assert cliente.post("/api/auth/entrar", json={"email": CONTA["email"], "senha": CONTA["senha"]}).status_code == 200
    for _ in range(5):
        cliente.post("/api/auth/entrar", json={"email": CONTA["email"], "senha": "errada"})
    assert cliente.post("/api/auth/entrar", json={"email": CONTA["email"], "senha": "errada"}).status_code == 401


# --------------------------------------------------------------------------- #
# Sessão
# --------------------------------------------------------------------------- #


def test_sair_revoga_a_sessao_no_servidor(cliente):
    """O cookie continua no navegador; a sessão é que deixa de existir."""
    cadastrar(cliente)
    cookie = cliente.cookies.get("spectra_sessao")
    sessao_id = seguranca.abrir_assinado(cookie)
    assert bd.usuario_da_sessao(sessao_id) is not None

    cliente.post("/api/auth/sair")
    assert bd.usuario_da_sessao(sessao_id) is None


def test_sessao_vencida_nao_vale(cliente):
    cadastrar(cliente)
    usuario = bd.buscar_por_email(CONTA["email"])
    vencida = bd.abrir_sessao(usuario["id"], dias=-1)
    assert bd.usuario_da_sessao(vencida) is None


def test_sessao_em_uso_se_renova(cliente):
    """Vencimento deslizante: quem usa o painel não é deslogado sozinho."""
    cadastrar(cliente)
    sessao_id = seguranca.abrir_assinado(cliente.cookies.get("spectra_sessao"))
    with bd.conexao() as con:
        con.execute("UPDATE sessoes SET expira_em = ? WHERE id = ?",
                    ((bd.agora() + bd.timedelta(hours=1)).isoformat(timespec="seconds"), sessao_id))

    resp = cliente.get("/api/auth/eu")
    assert resp.json()["usuario"]["email"] == CONTA["email"]
    assert "max-age" in resp.headers["set-cookie"].lower()
    with bd.conexao() as con:
        expira = con.execute("SELECT expira_em FROM sessoes WHERE id = ?", (sessao_id,)).fetchone()[0]
    assert expira > (bd.agora() + bd.timedelta(days=bd.DIAS_DE_SESSAO - 1)).isoformat()


def test_sessao_vencida_nao_se_renova():
    usuario = bd.criar_usuario(nome="X", email="x@exemplo.com")
    vencida = bd.abrir_sessao(usuario["id"], dias=-1)
    assert not bd.renovar_sessao(vencida)
    assert bd.usuario_da_sessao(vencida) is None


def test_entrada_devolve_ao_painel_quem_tem_sessao(cliente):
    """Só o botão Sair tira a pessoa de dentro."""
    cadastrar(cliente)
    resp = cliente.get("/inicio", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/painel"

    cliente.post("/api/auth/sair")
    assert cliente.get("/inicio", follow_redirects=False).status_code == 200


def test_cookie_e_httponly_e_samesite(cliente):
    cabecalho = cadastrar(cliente).headers["set-cookie"].lower()
    assert "httponly" in cabecalho
    assert "samesite=lax" in cabecalho


def test_painel_abre_com_sessao(cliente):
    cadastrar(cliente)
    assert cliente.get("/painel", follow_redirects=False).status_code == 200


# --------------------------------------------------------------------------- #
# Recuperação e Google
# --------------------------------------------------------------------------- #


def test_recuperacao_responde_igual_exista_ou_nao_a_conta(cliente):
    cadastrar(cliente)
    com = cliente.post("/api/auth/recuperar", json={"email": CONTA["email"]})
    sem = cliente.post("/api/auth/recuperar", json={"email": "ninguem@exemplo.com"})
    assert com.status_code == sem.status_code == 200
    assert com.json()["estado"] == sem.json()["estado"] == "enviado"


def test_google_desligado_quando_falta_configuracao(cliente, monkeypatch):
    monkeypatch.delenv("SPECTRA_GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPECTRA_GOOGLE_CLIENT_SECRET", raising=False)
    assert cliente.get("/api/auth/provedores").json()["google"] is False
    resp = cliente.get("/auth/google", follow_redirects=False)
    assert resp.headers["location"] == "/inicio?erro=google_indisponivel"


def test_callback_recusa_state_divergente(cliente, monkeypatch):
    """Sem o `state` do cookie bater, o retorno é descartado (CSRF no OAuth)."""
    monkeypatch.setenv("SPECTRA_GOOGLE_CLIENT_ID", "id-de-teste")
    monkeypatch.setenv("SPECTRA_GOOGLE_CLIENT_SECRET", "segredo-de-teste")
    resp = cliente.get(
        "/auth/google/callback?code=abc&state=inventado", follow_redirects=False
    )
    assert resp.headers["location"] == "/inicio?erro=google_estado"


def test_callback_sem_codigo_volta_com_erro(cliente):
    resp = cliente.get("/auth/google/callback?error=access_denied", follow_redirects=False)
    assert resp.headers["location"] == "/inicio?erro=google_cancelado"


def _retorno_do_google(cliente, monkeypatch, perfil):
    """Simula a volta do Google com `state` válido e o perfil informado."""
    from spectra_link_guard.auth import google

    async def perfil_falso(_codigo):
        return perfil

    monkeypatch.setattr(google, "trocar_codigo", perfil_falso)
    cliente.cookies.set("spectra_oauth_state", seguranca.assinar("estado-ok"))
    return cliente.get("/auth/google/callback?code=abc&state=estado-ok", follow_redirects=False)


def _perfil(email_verificado: bool) -> dict:
    return {
        "sub": "google-123",
        "email": CONTA["email"],
        "nome": "Quem Diz Ser Ana",
        "email_verificado": email_verificado,
    }


def test_google_com_email_nao_verificado_nao_toma_conta_existente(cliente, monkeypatch):
    """Sem o Google atestar o e-mail, ninguém entra na conta de quem tem esse e-mail."""
    bd.criar_usuario(nome=CONTA["nome"], email=CONTA["email"], senha_hash="x")

    resp = _retorno_do_google(cliente, monkeypatch, _perfil(email_verificado=False))

    assert resp.headers["location"] == "/inicio?erro=google_email_nao_verificado"
    assert "spectra_sessao" not in resp.headers.get("set-cookie", "")
    conta = bd.buscar_por_email(CONTA["email"])
    assert conta["google_sub"] is None
    assert conta["email_verificado"] == 0


def test_google_com_email_nao_verificado_nao_cria_conta(cliente, monkeypatch):
    """Criar conta com e-mail não verificado deixaria alguém 'reservar' o e-mail alheio."""
    resp = _retorno_do_google(cliente, monkeypatch, _perfil(email_verificado=False))

    assert resp.headers["location"] == "/inicio?erro=google_email_nao_verificado"
    assert bd.buscar_por_email(CONTA["email"]) is None


def test_google_com_email_verificado_vincula_conta_existente(cliente, monkeypatch):
    bd.criar_usuario(nome=CONTA["nome"], email=CONTA["email"], senha_hash="x")

    resp = _retorno_do_google(cliente, monkeypatch, _perfil(email_verificado=True))

    assert resp.headers["location"] == "/painel"
    conta = bd.buscar_por_email(CONTA["email"])
    assert conta["google_sub"] == "google-123"
    assert conta["email_verificado"] == 1
    assert cliente.get("/api/auth/eu").json()["usuario"]["id"] == conta["id"]


def test_vincular_google_so_marca_verificado_se_o_google_confirmou():
    conta = bd.criar_usuario(nome=CONTA["nome"], email=CONTA["email"], senha_hash="x")

    bd.vincular_google(conta["id"], "google-123", email_verificado=False)
    assert bd.buscar_por_id(conta["id"])["email_verificado"] == 0

    bd.vincular_google(conta["id"], "google-123", email_verificado=True)
    assert bd.buscar_por_id(conta["id"])["email_verificado"] == 1
