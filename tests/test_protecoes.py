"""Regressões das vulnerabilidades confirmadas na auditoria local."""
import asyncio
import base64
import hashlib
import socket
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from spectra_link_guard import saida
from spectra_link_guard.auth import bd, fluxos, google, protecao, seguranca
from spectra_link_guard.web.app import app
from spectra_link_guard.web.midias import validar_imagem


def conta():
    c=TestClient(app)
    r=c.post('/api/auth/cadastrar',json={'nome':'Pessoa Teste','email':'pessoa@example.com','senha':'Senha-forte123!'})
    assert r.status_code==201
    return c, bd.buscar_por_email('pessoa@example.com')


@pytest.mark.parametrize('valor',['AA.A','..','A.A','!'*5000])
def test_cookie_malformado_nao_derruba_api(valor):
    c=TestClient(app)
    c.cookies.set('spectra_sessao',valor)
    assert c.get('/api/auth/eu').json()=={'usuario':None}


def test_cookie_unicode_invalido():
    assert seguranca.abrir_assinado('é.a') is None


def test_csrf_uniforme_antes_de_qualquer_mutacao():
    c,_=conta()
    for url in ['/api/auth/sair','/api/auth/recuperar','/api/analises','/api/analisar']:
        assert c.post(url,json={},headers={'Origin':'https://invasor.example'}).status_code==403
    c.headers.pop('origin')
    assert c.post('/api/auth/sair').status_code==403
    assert c.post('/api/auth/sair',headers={'Origin':'http://testserver'}).status_code==200


def test_cabecalhos_nonce_e_limite_corpo():
    c=TestClient(app)
    pagina=c.get('/inicio')
    csp=pagina.headers['content-security-policy']
    nonce=csp.split("'nonce-")[1].split("'")[0]
    assert f'<script nonce="{nonce}"' in pagina.text
    assert 'unsafe-eval' not in csp and "script-src 'self' 'unsafe-inline'" not in csp
    assert c.get('/inicio').headers['content-security-policy']!=csp
    r=c.get('/api/auth/eu')
    assert r.headers['cache-control']=='no-store'
    assert r.headers['x-frame-options']=='DENY'
    assert r.headers['x-content-type-options']=='nosniff'
    assert c.post('/api/auth/cadastrar',content='x'*(1024*1024+1),headers={'Content-Type':'application/json'}).status_code==413
    assert c.post('/api/auth/cadastrar',content='{}',headers={'Content-Type':'text/plain'}).status_code==415


def test_editor_nao_verificado_nao_recebe_privilegios(monkeypatch):
    monkeypatch.setenv('SPECTRA_EDITOR_EMAILS','pessoa@example.com')
    c,u=conta()
    assert c.post('/api/blog/convites',json={'email':'autor@example.com'}).status_code==403
    assert c.post('/api/comunidade/blog',json={'titulo':'Título de teste','texto':'Publicação de teste.'}).status_code==403
    assert bd.buscar_por_id(u['id'])['email_verificado']==0


@pytest.mark.parametrize('ip',['127.0.0.1','10.0.0.1','169.254.169.254','192.168.1.1','100.64.0.1','0.0.0.0','224.0.0.1','::1','fc00::1','fe80::1','::ffff:127.0.0.1','64:ff9b::7f00:1','2002:7f00:1::'])
def test_ssrf_bloqueia_ips_internos_e_especiais(ip):
    assert not saida.ip_publico(ip)


def test_dns_misto_e_porta_alternativa_bloqueados(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,'',('8.8.8.8',443)),(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,'',('127.0.0.1',443))])
    with pytest.raises(saida.DestinoBloqueado): saida.resolver_publico('example.com',443)
    with pytest.raises(saida.DestinoBloqueado): saida.resolver_publico('example.com',8443)


def test_socket_usa_ip_validado_sem_resolver_novamente(monkeypatch):
    chamadas=[]
    class Socket:
        def settimeout(self,t): pass
        def connect(self,endereco): chamadas.append(endereco)
    monkeypatch.setattr(socket,'socket',lambda *a:Socket())
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:pytest.fail('Segunda resolução DNS'))
    saida.conectar([(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,('8.8.8.8',443))],3)
    assert chamadas==[('8.8.8.8',443)]


def test_imagem_truncada_recusada():
    falso=b'\x89PNG\r\n\x1a\n'+b'\0'*32
    with pytest.raises(ValueError): validar_imagem(falso,'image/png')


def test_imagens_simultaneas_limitadas_e_slot_liberado():
    from spectra_link_guard.web.midias import _PROCESSAMENTO, ImagemOcupada
    assert _PROCESSAMENTO.acquire(blocking=False)
    assert _PROCESSAMENTO.acquire(blocking=False)
    try:
        with pytest.raises(ImagemOcupada): validar_imagem(b'invalida','image/png')
    finally:
        _PROCESSAMENTO.release(); _PROCESSAMENTO.release()
    with pytest.raises(ValueError): validar_imagem(b'invalida','image/png')
    assert _PROCESSAMENTO.acquire(blocking=False)
    _PROCESSAMENTO.release()


def test_tls_reutiliza_dns_validado_no_diagnostico(monkeypatch):
    import ssl
    from types import SimpleNamespace
    from spectra_link_guard import tls
    destinos=[(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,('8.8.8.8',443))]
    resolucoes=[]; chamadas=[]
    def resolver(*args): resolucoes.append(args);return destinos
    def handshake(host,porta,timeout,verificar,alvos):
        chamadas.append((verificar,alvos))
        if verificar:
            erro=ssl.SSLCertVerificationError(1,'Certificado inválido')
            erro.verify_message='Certificado inválido'
            raise erro
        return None,None,'TLSv1.3','CIFRA'
    monkeypatch.setattr(tls,'resolver_publico',resolver)
    monkeypatch.setattr(tls,'_handshake',handshake)
    info=asyncio.run(tls.inspecionar_tls(SimpleNamespace(host_ascii='example.com',porta=443,esquema='https')))
    assert info.disponivel and not info.cadeia_valida
    assert len(resolucoes)==1
    assert chamadas==[(True,destinos),(False,destinos)]


def test_redefinicao_token_unico_revoga_todas_sessoes():
    c,u=conta()
    sessao=bd.abrir_sessao(u['id'])
    token=fluxos.emitir(u,'redefinir')
    with bd.conexao() as con:
        assert con.execute('SELECT hash FROM tokens_conta').fetchone()[0]!=token
    r=c.post('/api/auth/redefinir-senha',json={'token':token,'senha':'Outra-senha123!'})
    assert r.status_code==200
    assert bd.usuario_da_sessao(sessao) is None
    assert seguranca.conferir_senha('Outra-senha123!',bd.buscar_por_id(u['id'])['senha_hash'])
    assert c.post('/api/auth/redefinir-senha',json={'token':token,'senha':'Outra-senha123!'}).status_code==400


def test_confirmacao_expirada_e_finalidade_incorreta():
    _,u=conta()
    token=fluxos.emitir(u,'verificar')
    assert fluxos.consumir(token,'redefinir','x') is None
    with bd.conexao() as c: c.execute('UPDATE tokens_conta SET expira_em=?',((bd.agora()-timedelta(minutes=1)).isoformat(),))
    assert fluxos.consumir(token,'verificar') is None
    assert not bd.buscar_por_id(u['id'])['email_verificado']


def test_confirmacao_substitui_token_anterior_e_consume_uma_vez():
    _,u=conta()
    anterior=fluxos.emitir(u,'verificar')
    novo=fluxos.emitir(u,'verificar')
    assert fluxos.consumir(anterior,'verificar') is None
    assert fluxos.consumir(novo,'verificar')==u['id']
    assert bd.buscar_por_id(u['id'])['email_verificado']==1
    assert fluxos.consumir(novo,'verificar') is None


def test_sessao_tem_limite_absoluto():
    _,u=conta()
    sessao=bd.abrir_sessao(u['id'])
    with bd.conexao() as c: c.execute('UPDATE sessoes SET criado_em=? WHERE id=?',((bd.agora()-timedelta(days=31)).isoformat(),sessao))
    assert bd.usuario_da_sessao(sessao) is None
    assert not bd.renovar_sessao(sessao)


def test_scrypt_antigo_migra_no_login():
    from spectra_link_guard.auth.rotas import freio
    freio._por_ip.clear()
    sal=b'1234567890123456'
    chave=hashlib.scrypt(b'Senha-forte123!',salt=sal,n=16384,r=8,p=1,dklen=32)
    u=bd.criar_usuario(nome='Pessoa',email='antiga@example.com',senha_hash=f'scrypt$16384$8$1${sal.hex()}${chave.hex()}')
    r=TestClient(app).post('/api/auth/entrar',json={'email':u['email'],'senha':'Senha-forte123!'})
    assert r.status_code==200
    assert bd.buscar_por_id(u['id'])['senha_hash'].startswith('$argon2id$')


def test_google_pkce_contexto_unico(monkeypatch):
    monkeypatch.setenv('SPECTRA_GOOGLE_CLIENT_ID','cliente')
    monkeypatch.setenv('SPECTRA_GOOGLE_CLIENT_SECRET','segredo')
    state,nonce,verificador=fluxos.iniciar_google()
    q=parse_qs(urlsplit(google.url_de_autorizacao(state,nonce,verificador)).query)
    assert q['code_challenge_method']==['S256']
    assert q['code_challenge']==[base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).decode().rstrip('=')]
    assert fluxos.consumir_google(state)['nonce']==nonce
    assert fluxos.consumir_google(state) is None


@pytest.mark.parametrize('mudanca',[{'aud':'outro'},{'azp':'outro'},{'nonce':'diferente'},{'email_verified':False},{'email_verified':'true'},{'sub':''}])
def test_google_recusa_claims_invalidas(monkeypatch,mudanca):
    monkeypatch.setenv('SPECTRA_GOOGLE_CLIENT_ID','cliente')
    claims={'aud':'cliente','nonce':'nonce','sub':'123','email':'pessoa@example.com','email_verified':True,**mudanca}
    monkeypatch.setattr(google.id_token,'verify_oauth2_token',lambda *a,**k:claims)
    with pytest.raises(ValueError): google.verificar_token('jwt','nonce')


def test_google_vinculo_exige_conta_autenticada_e_mesmo_email(monkeypatch):
    c,u=conta()
    state,_,_=fluxos.iniciar_google(u['id'])
    c.cookies.set('spectra_oauth_state',seguranca.assinar(state))
    async def perfil(*args): return {'sub':'google-pessoa','email':u['email'],'nome':u['nome'],'email_verificado':True}
    monkeypatch.setattr(google,'trocar_codigo',perfil)
    r=c.get('/auth/google/callback',params={'code':'codigo','state':state},follow_redirects=False)
    assert r.headers['location']=='/painel'
    assert bd.buscar_por_id(u['id'])['google_sub']=='google-pessoa'
    assert bd.buscar_por_id(u['id'])['email_verificado']==1
    # O mesmo contexto não pode abrir outra sessão.
    c.cookies.set('spectra_oauth_state',seguranca.assinar(state))
    assert c.get('/auth/google/callback',params={'code':'codigo','state':state},follow_redirects=False).headers['location']=='/inicio?erro=google_estado'


@pytest.mark.parametrize('autenticado,mesmo_email',[(False,True),(True,False)])
def test_google_vinculo_recusa_sessao_ausente_e_email_diferente(monkeypatch,autenticado,mesmo_email):
    c,u=conta()
    state,_,_=fluxos.iniciar_google(u['id'])
    if not autenticado: c.cookies.clear()
    c.cookies.set('spectra_oauth_state',seguranca.assinar(state))
    async def perfil(*args): return {'sub':'google-pessoa','email':u['email'] if mesmo_email else 'outra@example.com','nome':u['nome'],'email_verificado':True}
    monkeypatch.setattr(google,'trocar_codigo',perfil)
    r=c.get('/auth/google/callback',params={'code':'codigo','state':state},follow_redirects=False)
    assert r.headers['location']=='/inicio?erro=google_vinculo_invalido'
    assert bd.buscar_por_id(u['id'])['google_sub'] is None


def test_google_cria_conta_nova_verificada(monkeypatch):
    c=TestClient(app)
    state,_,_=fluxos.iniciar_google()
    c.cookies.set('spectra_oauth_state',seguranca.assinar(state))
    async def perfil(*args): return {'sub':'google-nova','email':'nova@example.com','nome':'Pessoa Google','email_verificado':True}
    monkeypatch.setattr(google,'trocar_codigo',perfil)
    r=c.get('/auth/google/callback',params={'code':'codigo','state':state},follow_redirects=False)
    assert r.headers['location']=='/painel'
    u=c.get('/api/auth/eu').json()['usuario']
    assert u['email_verificado'] and u['tem_google'] and not u['tem_senha']


def test_producao_rejeita_configuracao_insegura(monkeypatch):
    monkeypatch.setenv('SPECTRA_AMBIENTE','producao')
    monkeypatch.setenv('SPECTRA_SEGREDO','curto')
    with pytest.raises(RuntimeError): protecao.validar_configuracao()
    monkeypatch.setenv('SPECTRA_SEGREDO','x'*40)
    monkeypatch.setenv('SPECTRA_ORIGEM_PUBLICA','http://example.com')
    with pytest.raises(RuntimeError): protecao.validar_configuracao()
    monkeypatch.setenv('SPECTRA_ORIGEM_PUBLICA','https://example.com')
    protecao.validar_configuracao()
    assert protecao.cookie_seguro()
