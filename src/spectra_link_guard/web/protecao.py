"""Cabeçalhos, origem, tamanho e limites das APIs, inclusive em erros."""
import asyncio
import os
import secrets
from contextvars import ContextVar
from urllib.parse import urlsplit
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException
from ..auth import protecao

class CorpoGrande(Exception): pass
NONCE=ContextVar('spectra_csp_nonce',default='')

class ProtecaoHTTP:
    def __init__(self,app): self.app=app

    async def __call__(self,scope,receive,send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        token=NONCE.set(secrets.token_urlsafe(24))
        try: return await self.proteger(scope,receive,send)
        finally: NONCE.reset(token)

    async def proteger(self,scope,receive,send):
        request=Request(scope)
        caminho=request.url.path
        nonce=NONCE.get()
        scope.setdefault('state',{})['csp_nonce']=nonce
        async def seguro(message):
            if message['type']=='http.response.start':
                headers=dict(message.get('headers',[]))
                headers[b'x-content-type-options']=b'nosniff'
                headers[b'x-frame-options']=b'DENY'
                headers[b'referrer-policy']=b'no-referrer'
                headers[b'permissions-policy']=b'camera=(), microphone=(), geolocation=()'
                headers[b'content-security-policy']=(f"default-src 'self'; script-src 'self' 'nonce-{nonce}' https://unpkg.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'").encode()
                if caminho.startswith(('/api/','/painel','/auth/','/redefinir-senha','/confirmar-email')):
                    headers[b'cache-control']=b'no-store'
                if protecao.producao(): headers[b'strict-transport-security']=b'max-age=31536000'
                message['headers']=list(headers.items())
            await send(message)
        async def erro(status,texto,headers=None):
            return await JSONResponse({'erro':texto},status_code=status,headers=headers)(scope,receive,seguro)
        # Em produção, Host nunca define a origem confiável.
        if protecao.producao() and request.url.hostname != urlsplit(protecao.origem_publica()).hostname:
            return await erro(400,'Host não autorizado.')
        mutacao=request.method in ('POST','PUT','PATCH','DELETE') and caminho.startswith('/api/')
        if mutacao:
            if not protecao.origem_permitida(request): return await erro(403,'Origem inválida.')
            tipo=request.headers.get('content-type','').split(';')[0].strip().lower()
            # Ações sem corpo (sair, seguir, excluir) continuam válidas.
            if caminho!='/api/midias' and tipo and tipo!='application/json':
                return await erro(415,'Envie dados em JSON.')
            try:
                acao,maximo,janela='api-escrita',120,60
                if caminho=='/api/auth/cadastrar': acao,maximo,janela='cadastro',8,3600
                elif caminho in ('/api/auth/recuperar','/api/auth/verificar-email'): acao,maximo,janela=caminho,5,900
                elif caminho.startswith('/api/auth/redefinir'): acao,maximo,janela='redefinicao',8,900
                elif caminho=='/api/midias': acao,maximo,janela='upload',12,300
                elif caminho.startswith('/api/chat'): acao,maximo,janela='mensagem',40,60
                elif caminho=='/api/analisar': acao,maximo,janela='analise',30,300
                elif caminho=='/api/assistente': acao,maximo,janela='assistente',40,300
                await asyncio.to_thread(protecao.limitar,request,acao,maximo,janela)
            except HTTPException as e:
                return await erro(e.status_code,e.detail,e.headers)
        limite=(40*1024*1024 if caminho=='/api/midias' else 1024*1024)
        try:
            declarado=int(request.headers.get('content-length','0'))
            if declarado<0: return await erro(400,'Tamanho inválido.')
            if declarado>limite: return await erro(413,'Corpo da solicitação muito grande.')
        except ValueError: return await erro(400,'Tamanho inválido.')
        tamanho=0
        async def receber():
            nonlocal tamanho
            message=await receive()
            if message['type']=='http.request':
                tamanho+=len(message.get('body',b''))
                if tamanho>limite: raise CorpoGrande()
            return message
        try: await self.app(scope,receber,seguro)
        except CorpoGrande: await erro(413,'Corpo da solicitação muito grande.')
