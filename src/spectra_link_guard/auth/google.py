"""Login com o Google — fluxo de código de autorização (OAuth 2.0 / OIDC).

Por que o fluxo de *código* e não o implícito: o segredo do cliente nunca sai
do servidor, e o token nunca passa pela URL do navegador (onde ficaria no
histórico e no Referer).

Configuração (as três variáveis são obrigatórias para o botão funcionar)::

    SPECTRA_GOOGLE_CLIENT_ID=...apps.googleusercontent.com
    SPECTRA_GOOGLE_CLIENT_SECRET=...
    SPECTRA_GOOGLE_REDIRECT=http://localhost:8000/auth/google/callback

No Google Cloud Console → Credenciais → ID do cliente OAuth (aplicativo da
Web), o valor de ``SPECTRA_GOOGLE_REDIRECT`` precisa estar cadastrado em
"URIs de redirecionamento autorizados", idêntico, incluindo o esquema.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

import httpx

_AUTORIZAR = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN = "https://oauth2.googleapis.com/token"
_USUARIO = "https://openidconnect.googleapis.com/v1/userinfo"

_ESCOPOS = "openid email profile"


class GoogleNaoConfigurado(RuntimeError):
    """O botão foi acionado sem as variáveis de ambiente definidas."""


def _cfg(nome: str) -> str | None:
    return os.getenv(nome) or None


def client_id() -> str | None:
    return _cfg("SPECTRA_GOOGLE_CLIENT_ID")


def redirect_uri() -> str:
    return _cfg("SPECTRA_GOOGLE_REDIRECT") or "http://localhost:8000/auth/google/callback"


def configurado() -> bool:
    return bool(client_id() and _cfg("SPECTRA_GOOGLE_CLIENT_SECRET"))


def url_de_autorizacao(state: str) -> str:
    """Monta a URL para onde o navegador é enviado."""
    if not configurado():
        raise GoogleNaoConfigurado(
            "Defina SPECTRA_GOOGLE_CLIENT_ID e SPECTRA_GOOGLE_CLIENT_SECRET."
        )
    parametros = {
        "client_id": client_id(),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": _ESCOPOS,
        "state": state,
        "access_type": "online",
        # Força a tela de escolha de conta em vez de reusar a última em silêncio.
        "prompt": "select_account",
    }
    return f"{_AUTORIZAR}?{urlencode(parametros)}"


async def trocar_codigo(codigo: str) -> dict[str, Any]:
    """Troca o código pelo perfil do usuário.

    Duas chamadas ao Google, ambas servidor-a-servidor sobre TLS: o token e
    depois o `userinfo`. Como o token veio direto do Google nesta conexão, os
    dados de `userinfo` são confiáveis sem validar a assinatura do id_token.
    """
    if not configurado():
        raise GoogleNaoConfigurado("Login com Google não está configurado no servidor.")

    async with httpx.AsyncClient(timeout=10.0) as cliente:
        resp = await cliente.post(
            _TOKEN,
            data={
                "code": codigo,
                "client_id": client_id(),
                "client_secret": _cfg("SPECTRA_GOOGLE_CLIENT_SECRET"),
                "redirect_uri": redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        acesso = resp.json().get("access_token")
        if not acesso:
            raise RuntimeError("O Google não devolveu access_token.")

        perfil = await cliente.get(_USUARIO, headers={"Authorization": f"Bearer {acesso}"})
        perfil.raise_for_status()
        dados = perfil.json()

    if not dados.get("email"):
        raise RuntimeError("A conta do Google não expôs um e-mail.")

    return {
        "sub": dados["sub"],
        "email": dados["email"],
        "nome": dados.get("name") or dados["email"].split("@")[0],
        # O Google diz se ele mesmo já verificou o e-mail — aproveitamos.
        "email_verificado": bool(dados.get("email_verified")),
    }
