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
import hmac
from datetime import datetime,timezone
from threading import BoundedSemaphore
from urllib.parse import urlsplit
from collections import deque
from threading import Lock
from typing import Any

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from . import bd, google, seguranca, protecao,fluxos,correio

router = APIRouter()

COOKIE_SESSAO = "spectra_sessao"
COOKIE_ESTADO = "spectra_oauth_state"

#: Em produção (HTTPS) marque como 1 para o cookie não trafegar em claro.
COOKIE_SEGURO = os.getenv("SPECTRA_COOKIE_SEGURO", "0") == "1"
_SENHAS=BoundedSemaphore(2)

async def trabalho_senha(funcao,*args):
    if not _SENHAS.acquire(blocking=False): raise HTTPException(429,'Muitas autenticações em andamento. Tente novamente.')
    try: return await asyncio.to_thread(funcao,*args)
    finally: _SENHAS.release()

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
        secure=protecao.cookie_seguro(),
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
    if len(pedido.nome.strip())<3: raise HTTPException(422,'Informe seu nome.')
    senha_hash = await trabalho_senha(seguranca.gerar_hash, pedido.senha)
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
    await asyncio.to_thread(protecao.limitar,request,'login-ip',8,600)
    await asyncio.to_thread(protecao.limitar,request,'login-conta',20,600,conta=str(pedido.email).lower())
    if not freio.permitido(ip):
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Espere alguns minutos antes de tentar de novo.",
        )

    usuario = await asyncio.to_thread(bd.buscar_por_email, pedido.email)
    confere = await trabalho_senha(
        seguranca.conferir_senha, pedido.senha, usuario["senha_hash"] if usuario else None
    )
    if not usuario or not confere:
        # Mesma mensagem nos dois casos, de propósito.
        raise HTTPException(status_code=401, detail="E-mail ou senha não conferem.")
    if seguranca.precisa_atualizar(usuario['senha_hash']):
        novo=await trabalho_senha(seguranca.gerar_hash,pedido.senha)
        await asyncio.to_thread(bd.atualizar_senha,usuario['id'],novo)

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
    resposta.delete_cookie(COOKIE_SESSAO, path="/",secure=protecao.cookie_seguro(),httponly=True,samesite='lax')
    return {"estado": "sessao encerrada"}


@router.get("/api/auth/eu", summary="Quem está logado")
async def eu(resposta: Response, spectra_sessao: str | None = Cookie(default=None)) -> dict[str, Any]:
    """Toda tela do painel chama esta rota: é aqui que a sessão se renova.

    Vencimento deslizante — enquanto a pessoa usa o painel, a sessão (no banco
    e no cookie) ganha mais DIAS_DE_SESSAO. Só o botão "Sair" encerra.
    """
    usuario = usuario_atual(spectra_sessao)
    if usuario is None:
        return {"usuario": None}
    sessao_id = seguranca.abrir_assinado(spectra_sessao or "")
    if sessao_id and await asyncio.to_thread(bd.renovar_sessao, sessao_id):
        _gravar_sessao(resposta, sessao_id)
    return {"usuario": bd.publico(usuario)}


class PedidoRecuperacao(BaseModel):
    email: EmailStr


@router.post("/api/auth/recuperar", summary="Pede o link de redefinição")
async def recuperar(pedido: PedidoRecuperacao, tarefas: BackgroundTasks) -> dict[str, str]:
    if not correio.configurado():
        raise HTTPException(503,'Recuperação por e-mail ainda não configurada. Entre com Google, se sua conta já estiver conectada.')
    tarefas.add_task(correio.solicitar,str(pedido.email).lower(),'redefinir')
    return {
        "estado": "enviado",
        "mensagem": "Se houver uma conta, você receberá as instruções de recuperação.",
    }

@router.post('/api/auth/verificar-email')
async def verificar_email(request: Request,tarefas: BackgroundTasks):
    u=usuario_atual(request.cookies.get(COOKIE_SESSAO))
    if not u: raise HTTPException(401,'Entre na sua conta.')
    if not correio.configurado(): raise HTTPException(503,'Envio de e-mail ainda não configurado.')
    tarefas.add_task(correio.solicitar,u['email'],'verificar')
    return {'mensagem':'Se necessário, enviaremos as instruções para seu e-mail.'}

class PedidoToken(BaseModel):
    token: str=Field(min_length=40,max_length=100)

class PedidoNovaSenha(PedidoToken):
    senha: str=Field(min_length=8,max_length=200)

@router.post('/api/auth/confirmar-email')
async def confirmar_email(pedido: PedidoToken):
    if not await asyncio.to_thread(fluxos.consumir,pedido.token,'verificar'):
        raise HTTPException(400,'Link inválido, expirado ou já utilizado.')
    return {'mensagem':'E-mail confirmado. Você já pode voltar ao perfil.'}

@router.post('/api/auth/redefinir-senha')
async def redefinir_senha(pedido: PedidoNovaSenha,resposta: Response):
    novo=await trabalho_senha(seguranca.gerar_hash,pedido.senha)
    if not await asyncio.to_thread(fluxos.consumir,pedido.token,'redefinir',novo):
        raise HTTPException(400,'Link inválido, expirado ou já utilizado.')
    resposta.delete_cookie(COOKIE_SESSAO,path='/',secure=protecao.cookie_seguro(),httponly=True,samesite='lax')
    return {'mensagem':'Senha alterada. Entre novamente; as sessões anteriores foram encerradas.'}


# --------------------------------------------------------------------------- #
# Google
# --------------------------------------------------------------------------- #


@router.get("/api/auth/provedores", summary="Quais formas de entrar estão ativas")
async def provedores() -> dict[str, bool]:
    return {"senha": True, "google": google.configurado(),"email":correio.configurado()}


@router.get('/auth/google',include_in_schema=False)
async def google_iniciar(request: Request):
    if not google.configurado(): return RedirectResponse('/inicio?erro=google_indisponivel',status_code=303)
    await asyncio.to_thread(protecao.limitar,request,'google-inicio',15,600)
    alvo=urlsplit(google.redirect_uri())
    canonica=f'{alvo.scheme}://{alvo.netloc}'
    if protecao.origem(str(request.base_url))!=protecao.origem(canonica):
        return RedirectResponse(canonica+'/auth/google'+('?vincular=1' if request.query_params.get('vincular')=='1' else ''),status_code=303)
    usuario_id=None
    if request.query_params.get('vincular')=='1':
        u=usuario_atual(request.cookies.get(COOKIE_SESSAO))
        if not u or not u.get('ultimo_acesso') or (bd.agora()-datetime.fromisoformat(u['ultimo_acesso'])).total_seconds()>600:
            return RedirectResponse('/inicio?erro=google_reautenticar',status_code=303)
        usuario_id=u['id']
    state,nonce,verificador=await asyncio.to_thread(fluxos.iniciar_google,usuario_id)
    resposta=RedirectResponse(google.url_de_autorizacao(state,nonce,verificador),status_code=303)
    resposta.set_cookie(COOKIE_ESTADO,seguranca.assinar(state),max_age=600,httponly=True,samesite='lax',secure=protecao.cookie_seguro(),path='/')
    return resposta

@router.get('/auth/google/callback',include_in_schema=False)
async def google_retorno(request: Request,code: str|None=None,state: str|None=None,error: str|None=None):
    def voltar(destino):
        resposta=RedirectResponse(destino,status_code=303)
        resposta.delete_cookie(COOKIE_ESTADO,path='/',httponly=True,samesite='lax',secure=protecao.cookie_seguro())
        return resposta
    esperado=seguranca.abrir_assinado(request.cookies.get(COOKIE_ESTADO,''))
    if error or not code: return voltar('/inicio?erro=google_cancelado')
    if not state or not state.isascii() or len(state)>100 or len(code)>2048 or not esperado or not hmac.compare_digest(state,esperado):
        return voltar('/inicio?erro=google_estado')
    fluxo=await asyncio.to_thread(fluxos.consumir_google,state)
    if not fluxo: return voltar('/inicio?erro=google_estado')
    try: perfil=await google.trocar_codigo(code,fluxo['nonce'],fluxo['verificador'])
    except Exception: return voltar('/inicio?erro=google_falhou')
    if not perfil.get('email_verificado'): return voltar('/inicio?erro=google_email_nao_verificado')
    usuario=await asyncio.to_thread(bd.buscar_por_google,perfil['sub'])
    if fluxo['usuario_id']:
        atual=usuario_atual(request.cookies.get(COOKIE_SESSAO))
        if (not atual or atual['id']!=fluxo['usuario_id'] or atual['email']!=perfil['email'] or
            (usuario and usuario['id']!=atual['id']) or (atual['google_sub'] and atual['google_sub']!=perfil['sub'])):
            return voltar('/inicio?erro=google_vinculo_invalido')
        try: await asyncio.to_thread(bd.vincular_google,atual['id'],perfil['sub'],email_verificado=True)
        except sqlite3.IntegrityError: return voltar('/inicio?erro=google_vinculo_invalido')
        usuario=await asyncio.to_thread(bd.buscar_por_id,atual['id'])
    elif not usuario:
        existente=await asyncio.to_thread(bd.buscar_por_email,perfil['email'])
        if existente: return voltar('/inicio?erro=google_vinculo_necessario')
        try:
            usuario=await asyncio.to_thread(bd.criar_usuario,nome=perfil['nome'],email=perfil['email'],google_sub=perfil['sub'],email_verificado=True)
        except sqlite3.IntegrityError: return voltar('/inicio?erro=google_vinculo_necessario')
    if usuario['email']!=perfil['email']: return voltar('/inicio?erro=google_vinculo_invalido')
    anterior=seguranca.abrir_assinado(request.cookies.get(COOKIE_SESSAO,''))
    if anterior: await asyncio.to_thread(bd.fechar_sessao,anterior)
    sessao=await asyncio.to_thread(bd.abrir_sessao,usuario['id'])
    await asyncio.to_thread(bd.marcar_acesso,usuario['id'])
    resposta=voltar('/painel')
    _gravar_sessao(resposta,sessao)
    return resposta
