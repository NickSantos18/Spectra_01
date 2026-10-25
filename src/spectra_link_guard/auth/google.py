"""OAuth de código com PKCE e validação OIDC pelo SDK oficial do Google."""
import asyncio
import hashlib
import hmac
import os
from base64 import urlsafe_b64encode
from urllib.parse import urlencode, urlsplit
import httpx
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from . import protecao

class GoogleNaoConfigurado(RuntimeError): pass

def client_id(): return os.getenv('SPECTRA_GOOGLE_CLIENT_ID') or None
def redirect_uri(): return os.getenv('SPECTRA_GOOGLE_REDIRECT') or protecao.origem_publica()+'/auth/google/callback'
def configurado():
    try: uri=urlsplit(redirect_uri())
    except ValueError: return False
    segura=uri.scheme=='https' or (not protecao.producao() and uri.scheme=='http' and uri.hostname in ('localhost','127.0.0.1','::1'))
    return bool(client_id() and os.getenv('SPECTRA_GOOGLE_CLIENT_SECRET') and segura and uri.path=='/auth/google/callback' and not uri.query and not uri.fragment and not uri.username and protecao.origem(redirect_uri()) == protecao.origem(protecao.origem_publica()))

def url_de_autorizacao(state,nonce,verificador):
    if not configurado(): raise GoogleNaoConfigurado('Configure as credenciais OAuth do Google.')
    desafio=urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).decode().rstrip('=')
    return 'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({
        'client_id':client_id(),'redirect_uri':redirect_uri(),'response_type':'code',
        'scope':'openid email profile','state':state,'nonce':nonce,
        'code_challenge':desafio,'code_challenge_method':'S256','prompt':'select_account'})

def verificar_token(token,nonce):
    request=GoogleRequest()
    def transporte(*args,**kwargs):
        kwargs['timeout']=10
        return request(*args,**kwargs)
    dados=id_token.verify_oauth2_token(token,transporte,client_id())
    if (dados.get('aud')!=client_id() or dados.get('azp',client_id())!=client_id() or
        not isinstance(dados.get('nonce'),str) or not hmac.compare_digest(dados['nonce'],nonce) or
        not isinstance(dados.get('sub'),str) or not dados['sub'] or dados.get('email_verified') is not True):
        raise ValueError('Token de identidade inválido.')
    from pydantic import TypeAdapter,EmailStr
    email=str(TypeAdapter(EmailStr).validate_python(dados.get('email'))).lower()
    return {'sub':dados['sub'],'email':email,'nome':str(dados.get('name') or email.split('@')[0])[:120], 'email_verificado':True}

async def trocar_codigo(codigo,nonce,verificador):
    if not configurado(): raise GoogleNaoConfigurado('Google não configurado.')
    async with httpx.AsyncClient(timeout=10,trust_env=False) as c:
        r=await c.post('https://oauth2.googleapis.com/token',data={
            'code':codigo,'client_id':client_id(),'client_secret':os.environ['SPECTRA_GOOGLE_CLIENT_SECRET'],
            'redirect_uri':redirect_uri(),'grant_type':'authorization_code','code_verifier':verificador})
        r.raise_for_status()
        token=r.json().get('id_token')
        if not isinstance(token,str) or len(token)>20000: raise ValueError('ID token ausente.')
    return await asyncio.to_thread(verificar_token,token,nonce)
