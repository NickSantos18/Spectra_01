"""Rotas de autenticação.

Decisões que valem registro:

* **Mensagem única para login errado.** "E-mail ou senha não conferem" tanto
  para e-mail inexistente quanto para senha errada — dizer qual dos dois falhou
  entrega a lista de contas válidas a quem estiver testando.
* **Recuperação sempre responde igual.** Mesma resposta com ou sem conta.
* **scrypt roda em thread.** ~100 ms de CPU por verificação travariam o laço de
  eventos; `asyncio.to_thread` mantém o servidor respondendo.
* **Sessão em cookie HttpOnly.** O JavaScript da página não lê o cookie, então
  um XSS não rouba a sessão direto do `document.cookie`.
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import time
from collections import deque
from threading import Lock
from typing import Any

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from . import bd, google, seguranca

router = APIRouter()

COOKIE_SESSAO = "spectra_sessao"
COOKIE_ESTADO = "spectra_oauth_state"

#: Em produção (HTTPS) marque como 1 para o cookie não trafegar em claro.
COOKIE_SEGURO = os.getenv("SPECTRA_COOKIE_SEGURO", "0") == "1"

#: Tentativas de login por IP antes de travar, e por quanto tempo.
_MAX_TENTATIVAS = 8
_JANELA_S = 600.0


class _Freio:
    """Limita tentativas de login por IP. Janela deslizante em memória."""

    def __init__(self) -> None:
        self._por_ip: dict[str, deque[float]] = {}
        self._trava = Lock()

    def permitido(self, ip: str) -> bool:
        agora = time.monotonic()
        with self._trava:
            marcas = self._por_ip.setdefault(ip, deque())
            while marcas and agora - marcas[0] > _JANELA_S:
                marcas.popleft()
            if len(marcas) >= _MAX_TENTATIVAS:
                return False
            marcas.append(agora)
            return True

    def liberar(self, ip: str) -> None:
        """Login bem-sucedido zera o contador daquele IP."""
        with self._trava:
            self._por_ip.pop(ip, None)


freio = _Freio()


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def _gravar_sessao(resposta: Response, sessao_id: str) -> None:
    resposta.set_cookie(
        COOKIE_SESSAO,
        seguranca.assinar(sessao_id),
        max_age=bd.DIAS_DE_SESSAO * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SEGURO,
        path="/",
    )


def usuario_atual(spectra_sessao: str | None = Cookie(default=None)) -> dict[str, Any] | None:
    """Dependência: devolve o usuário logado, ou ``None``."""
    if not spectra_sessao:
        return None
    sessao_id = seguranca.abrir_assinado(spectra_sessao)
    return bd.usuario_da_sessao(sessao_id) if sessao_id else None


# --------------------------------------------------------------------------- #
# Cadastro e login por senha
# --------------------------------------------------------------------------- #


class PedidoCadastro(BaseModel):
    nome: str = Field(min_length=3, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=200)


class PedidoLogin(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=200)


@router.post("/api/auth/cadastrar", status_code=201, summary="Cria uma conta")
async def cadastrar(pedido: PedidoCadastro, resposta: Response) -> dict[str, Any]:
    senha_hash = await asyncio.to_thread(seguranca.gerar_hash, pedido.senha)
    try:
        usuario = await asyncio.to_thread(
            bd.criar_usuario, nome=pedido.nome, email=pedido.email, senha_hash=senha_hash
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Já existe uma conta com este e-mail.")

    sessao = await asyncio.to_thread(bd.abrir_sessao, usuario["id"])
    _gravar_sessao(resposta, sessao)
    await asyncio.to_thread(bd.marcar_acesso, usuario["id"])
    return {"usuario": bd.publico(usuario)}


@router.post("/api/auth/entrar", summary="Entra com e-mail e senha")
async def entrar(pedido: PedidoLogin, request: Request, resposta: Response) -> dict[str, Any]:
    ip = _ip(request)
    if not freio.permitido(ip):
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Espere alguns minutos antes de tentar de novo.",
        )

    usuario = await asyncio.to_thread(bd.buscar_por_email, pedido.email)
    confere = await asyncio.to_thread(
        seguranca.conferir_senha, pedido.senha, usuario["senha_hash"] if usuario else None
    )
    if not usuario or not confere:
        # Mesma mensagem nos dois casos, de propósito.
        raise HTTPException(status_code=401, detail="E-mail ou senha não conferem.")

    freio.liberar(ip)
    sessao = await asyncio.to_thread(bd.abrir_sessao, usuario["id"])
    _gravar_sessao(resposta, sessao)
    await asyncio.to_thread(bd.marcar_acesso, usuario["id"])
    return {"usuario": bd.publico(usuario)}


@router.post("/api/auth/sair", summary="Encerra a sessão")
async def sair(resposta: Response, spectra_sessao: str | None = Cookie(default=None)) -> dict[str, str]:
    if spectra_sessao:
        sessao_id = seguranca.abrir_assinado(spectra_sessao)
        if sessao_id:
            await asyncio.to_thread(bd.fechar_sessao, sessao_id)
    resposta.delete_cookie(COOKIE_SESSAO, path="/")
    return {"estado": "sessao encerrada"}


@router.get("/api/auth/eu", summary="Quem está logado")
async def eu(spectra_sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    usuario = usuario_atual(spectra_sessao)
    return {"usuario": bd.publico(usuario) if usuario else None}


class PedidoRecuperacao(BaseModel):
    email: EmailStr


@router.post("/api/auth/recuperar", summary="Pede o link de redefinição")
async def recuperar(pedido: PedidoRecuperacao) -> dict[str, str]:
    # TODO: gerar token de uso único com validade curta e enviar por e-mail.
    # A resposta é intencionalmente idêntica exista ou não a conta.
    return {
        "estado": "enviado",
        "mensagem": f"Se houver conta para {pedido.email}, o link chega em alguns minutos.",
    }


# --------------------------------------------------------------------------- #
# Google
# --------------------------------------------------------------------------- #


@router.get("/api/auth/provedores", summary="Quais formas de entrar estão ativas")
async def provedores() -> dict[str, bool]:
    return {"senha": True, "google": google.configurado()}


@router.get("/auth/google", include_in_schema=False)
async def google_iniciar() -> RedirectResponse:
    """Manda o navegador para o Google, guardando o `state` num cookie."""
    if not google.configurado():
        return RedirectResponse("/inicio?erro=google_indisponivel", status_code=303)

    estado = seguranca.token_aleatorio()
    resposta = RedirectResponse(google.url_de_autorizacao(estado), status_code=303)
    # O `state` volta na URL; comparamos com este cookie para saber que o
    # pedido saiu daqui, e não de um site de terceiro (CSRF no OAuth).
    resposta.set_cookie(
        COOKIE_ESTADO,
        seguranca.assinar(estado),
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SEGURO,
        path="/",
    )
    return resposta


@router.get("/auth/google/callback", include_in_schema=False)
async def google_retorno(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    esperado = seguranca.abrir_assinado(request.cookies.get(COOKIE_ESTADO, ""))

    if error or not code:
        return RedirectResponse("/inicio?erro=google_cancelado", status_code=303)
    if not state or not esperado or state != esperado:
        return RedirectResponse("/inicio?erro=google_estado", status_code=303)

    try:
        perfil = await google.trocar_codigo(code)
    except Exception:
        return RedirectResponse("/inicio?erro=google_falhou", status_code=303)

    usuario = await asyncio.to_thread(bd.buscar_por_google, perfil["sub"])
    if not usuario:
        # Já existe conta com este e-mail? Vincula em vez de duplicar.
        usuario = await asyncio.to_thread(bd.buscar_por_email, perfil["email"])
        if usuario:
            await asyncio.to_thread(bd.vincular_google, usuario["id"], perfil["sub"])
            usuario = await asyncio.to_thread(bd.buscar_por_id, usuario["id"])
        else:
            usuario = await asyncio.to_thread(
                bd.criar_usuario,
                nome=perfil["nome"],
                email=perfil["email"],
                google_sub=perfil["sub"],
                email_verificado=perfil["email_verificado"],
            )

    sessao = await asyncio.to_thread(bd.abrir_sessao, usuario["id"])
    await asyncio.to_thread(bd.marcar_acesso, usuario["id"])

    resposta = RedirectResponse("/painel", status_code=303)
    _gravar_sessao(resposta, sessao)
    resposta.delete_cookie(COOKIE_ESTADO, path="/")
    return resposta
