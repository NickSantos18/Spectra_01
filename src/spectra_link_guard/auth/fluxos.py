"""Tokens de uso único, armazenados por hash, e contextos OAuth no servidor."""
import hashlib
import secrets
from datetime import timedelta
from . import bd

bd.registrar_esquema('''
CREATE TABLE IF NOT EXISTS tokens_conta (
 hash TEXT PRIMARY KEY, usuario_id TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 email TEXT NOT NULL, finalidade TEXT NOT NULL, expira_em TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fluxos_google (
 hash TEXT PRIMARY KEY, nonce TEXT NOT NULL, verificador TEXT NOT NULL,
 usuario_id TEXT, expira_em TEXT NOT NULL);
''')

def resumo(token): return hashlib.sha256(token.encode()).hexdigest()

def emitir(usuario,finalidade):
    token=secrets.token_urlsafe(32)
    with bd.conexao() as c:
        c.execute('DELETE FROM tokens_conta WHERE expira_em<=? OR (usuario_id=? AND finalidade=?)',(bd.agora().isoformat(),usuario['id'],finalidade))
        c.execute('INSERT INTO tokens_conta VALUES (?,?,?,?,?)',(resumo(token),usuario['id'],usuario['email'],finalidade,(bd.agora()+timedelta(minutes=20)).isoformat()))
    return token

def consumir(token,finalidade,senha_hash=None):
    with bd.conexao() as c:
        c.execute('BEGIN IMMEDIATE')
        r=c.execute('''SELECT t.* FROM tokens_conta t JOIN usuarios u ON u.id=t.usuario_id AND u.email=t.email
          WHERE t.hash=? AND t.finalidade=? AND t.expira_em>?''',(resumo(token),finalidade,bd.agora().isoformat())).fetchone()
        if not r: return None
        c.execute('DELETE FROM tokens_conta WHERE hash=?',(r['hash'],))
        if finalidade=='verificar': c.execute('UPDATE usuarios SET email_verificado=1 WHERE id=?',(r['usuario_id'],))
        elif finalidade=='redefinir' and senha_hash:
            c.execute('UPDATE usuarios SET senha_hash=? WHERE id=?',(senha_hash,r['usuario_id']))
            c.execute('DELETE FROM sessoes WHERE usuario_id=?',(r['usuario_id'],))
        else: raise ValueError('Finalidade inválida.')
        return r['usuario_id']

def iniciar_google(usuario_id=None):
    state=secrets.token_urlsafe(32); nonce=secrets.token_urlsafe(32); verificador=secrets.token_urlsafe(48)
    with bd.conexao() as c:
        c.execute('DELETE FROM fluxos_google WHERE expira_em<=?',(bd.agora().isoformat(),))
        c.execute('INSERT INTO fluxos_google VALUES (?,?,?,?,?)',(resumo(state),nonce,verificador,usuario_id,(bd.agora()+timedelta(minutes=10)).isoformat()))
    return state,nonce,verificador

def consumir_google(state):
    with bd.conexao() as c:
        c.execute('BEGIN IMMEDIATE')
        r=c.execute('SELECT * FROM fluxos_google WHERE hash=? AND expira_em>?',(resumo(state),bd.agora().isoformat())).fetchone()
        if r: c.execute('DELETE FROM fluxos_google WHERE hash=?',(r['hash'],))
        return dict(r) if r else None
