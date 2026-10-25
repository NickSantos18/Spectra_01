"""Configuração e limites persistentes, compartilhados pelos processos do app."""
import hashlib
import os
from urllib.parse import urlsplit
from fastapi import HTTPException, Request
from . import bd

bd.registrar_esquema('''
CREATE TABLE IF NOT EXISTS limites_uso (
 chave TEXT NOT NULL, instante REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_limites_uso ON limites_uso(chave,instante);
CREATE INDEX IF NOT EXISTS idx_limites_instante ON limites_uso(instante);
''')

def producao():
    return os.getenv('SPECTRA_AMBIENTE','desenvolvimento') == 'producao'

def origem_publica():
    return os.getenv('SPECTRA_ORIGEM_PUBLICA','http://127.0.0.1:8000').rstrip('/')

def origem(valor):
    try:
        p=urlsplit(valor)
        if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:
            return None
        return p.scheme, p.hostname.lower(), p.port or (443 if p.scheme=='https' else 80)
    except ValueError:
        return None

def cookie_seguro():
    return producao() or os.getenv('SPECTRA_COOKIE_SEGURO','0') == '1'

def validar_configuracao():
    if not producao(): return
    segredo=os.getenv('SPECTRA_SEGREDO','')
    if len(segredo)<32 or segredo.startswith('troque-'):
        raise RuntimeError('Produção exige SPECTRA_SEGREDO aleatório com pelo menos 32 caracteres.')
    try: p=urlsplit(origem_publica())
    except ValueError: raise RuntimeError('Origem pública inválida.') from None
    if origem(origem_publica()) is None or p.scheme!='https' or p.path or p.query or p.fragment:
        raise RuntimeError('Produção exige SPECTRA_ORIGEM_PUBLICA com a origem HTTPS do site.')

def origem_permitida(request: Request):
    """JSON same-origin + SameSite + Origin/Fetch Metadata; sem CORS permissivo.

    Clientes sem Origin são aceitos só sem cookies de autenticação. Com cookie,
    exigir Origin ou Referer; clientes de API podem enviar Origin explicitamente.
    """
    permitidas={origem(origem_publica())} if producao() else {origem(str(request.base_url)),origem(origem_publica())}
    fonte=request.headers.get('origin') or request.headers.get('referer')
    if request.headers.get('sec-fetch-site') == 'cross-site': return False
    if fonte: return origem(fonte) in permitidas
    return 'spectra_sessao' not in request.cookies

def limitar(request, acao, maximo, segundos, *, conta=None):
    """Janela SQLite, transação atômica; não mantém IP puro no banco."""
    ip=request.client.host if request.client else 'desconhecido'
    quem=conta or ip
    digest=hashlib.sha256(str(quem).encode()).hexdigest()
    chave=f'{acao}:{digest}'
    agora=bd.agora().timestamp()
    with bd.conexao() as con:
        con.execute('BEGIN IMMEDIATE')
        con.execute('DELETE FROM limites_uso WHERE instante<?',(agora-86400,))
        total=con.execute('SELECT count(*) FROM limites_uso WHERE chave=? AND instante>?',(chave,agora-segundos)).fetchone()[0]
        if total>=maximo:
            raise HTTPException(429,'Muitas solicitações. Aguarde alguns minutos.',headers={'Retry-After':str(segundos)})
        con.execute('INSERT INTO limites_uso VALUES (?,?)',(chave,agora))
