"""Mídias autenticadas e listas de conexões do Explorar."""
import re
import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, Response
from ..auth import bd
from .comunidade import exigir, data
from .midias import validar_imagem, ImagemOcupada
import asyncio

router = APIRouter()
bd.registrar_esquema("""
CREATE TABLE IF NOT EXISTS midias (
 id TEXT PRIMARY KEY, usuario_id TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 mime TEXT NOT NULL, arquivo BLOB NOT NULL, criado_em TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS publicacao_midias (
 publicacao TEXT NOT NULL REFERENCES publicacoes(id) ON DELETE CASCADE,
 midia TEXT NOT NULL UNIQUE REFERENCES midias(id) ON DELETE CASCADE,
 posicao INTEGER NOT NULL, PRIMARY KEY(publicacao,midia));
CREATE INDEX IF NOT EXISTS idx_midias_usuario ON midias(usuario_id,criado_em);
""")


@router.get('/api/conexoes/{tipo}')
def conexoes(tipo: str, request: Request):
    u = exigir(request)
    if tipo not in ('seguindo', 'seguidores'):
        raise HTTPException(404, 'Lista não encontrada.')
    lado, outro = ('seguidor', 'seguido') if tipo == 'seguindo' else ('seguido', 'seguidor')
    with bd.conexao() as con:
        rows = con.execute(f"""SELECT u.id,u.nome,COALESCE(p.foto,'') AS foto,
          EXISTS(SELECT 1 FROM seguidores x WHERE x.seguidor=? AND x.seguido=u.id) AS seguindo
          FROM seguidores s JOIN usuarios u ON u.id=s.{outro}
          LEFT JOIN perfis p ON p.usuario_id=u.id WHERE s.{lado}=? ORDER BY s.criado_em DESC,u.nome""", (u['id'],u['id'])).fetchall()
    return [dict(r) for r in rows]


def identificar(raw, mime):
    validos = {
        'image/png': raw.startswith(b'\x89PNG\r\n\x1a\n'),
        'image/jpeg': raw.startswith(b'\xff\xd8\xff'),
        'image/webp': raw[:4] == b'RIFF' and raw[8:12] == b'WEBP',
        'video/mp4': len(raw) >= 16 and raw[4:8] == b'ftyp' and raw[8:12] in (b'isom',b'iso2',b'mp41',b'mp42',b'avc1',b'dash',b'M4V ',b'msdh',b'iso5',b'iso6'),
        'video/webm': raw.startswith(b'\x1a\x45\xdf\xa3') and b'webm' in raw[:4096],
    }
    return validos.get(mime, False)


@router.post('/api/midias', status_code=201)
async def upload(request: Request):
    u = exigir(request)
    mime = request.headers.get('content-type','').split(';')[0].lower()
    if mime not in ('image/png','image/jpeg','image/webp','video/mp4','video/webm'):
        raise HTTPException(415, 'Use foto PNG, JPEG ou WebP, ou vídeo MP4 ou WebM.')
    limite = (40 if mime.startswith('video/') else 10) * 1024 * 1024
    partes, tamanho = [], 0
    async for bloco in request.stream():
        tamanho += len(bloco)
        if tamanho > limite:
            raise HTTPException(413, 'Limite por arquivo: fotos de 10 MB e vídeos de 40 MB.')
        partes.append(bloco)
    raw = b''.join(partes)
    if not identificar(raw, mime):
        raise HTTPException(415, 'O conteúdo do arquivo não corresponde ao formato informado.')
    if mime.startswith('image/'):
        try: raw=await asyncio.to_thread(validar_imagem,raw,mime)
        except ImagemOcupada as exc: raise HTTPException(429,str(exc))
        except ValueError: raise HTTPException(415,'Imagem inválida ou muito grande.')
        tamanho=len(raw)
        if tamanho>limite: raise HTTPException(413,'Imagem processada excede o limite.')
    novo = uuid.uuid4().hex
    with bd.conexao() as con:
        con.execute('BEGIN IMMEDIATE')
        con.execute("DELETE FROM midias WHERE criado_em<? AND NOT EXISTS(SELECT 1 FROM publicacao_midias p WHERE p.midia=midias.id)", ((bd.agora()-timedelta(days=1)).isoformat(timespec='seconds'),))
        usados = con.execute('SELECT COALESCE(SUM(length(arquivo)),0) FROM midias WHERE usuario_id=?',(u['id'],)).fetchone()[0]
        if usados + tamanho > 200 * 1024 * 1024:
            raise HTTPException(413, 'Sua conta atingiu 200 MB de mídias. Exclua publicações antigas para liberar espaço.')
        total=con.execute('SELECT COALESCE(SUM(length(arquivo)),0) FROM midias').fetchone()[0]
        if total+tamanho>1024*1024*1024: raise HTTPException(507,'Armazenamento temporariamente indisponível.')
        con.execute('INSERT INTO midias VALUES (?,?,?,?,?)',(novo,u['id'],mime,raw,data()))
    return {'id':novo, 'url':'/api/midias/'+novo, 'tipo':'video' if mime.startswith('video/') else 'foto'}


@router.api_route('/api/midias/{identificador}', methods=['GET','HEAD'])
def arquivo(identificador: str, request: Request):
    u = exigir(request)
    with bd.conexao() as con:
        r = con.execute("""SELECT mime,length(arquivo) AS tamanho FROM midias m WHERE id=?
          AND (usuario_id=? OR EXISTS(SELECT 1 FROM publicacao_midias p WHERE p.midia=m.id))""",(identificador,u['id'])).fetchone()
        if not r:
            raise HTTPException(404, 'Mídia não encontrada.')
        total = r['tamanho']; inicio, fim, status = 0,total-1,200
        headers = {'Accept-Ranges':'bytes','X-Content-Type-Options':'nosniff','Cache-Control':'no-store'}
        faixa = request.headers.get('range')
        if faixa:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)',faixa) if len(faixa)<=80 else None
            if not match or not any(match.groups()):
                return Response(status_code=416,headers={**headers,'Content-Range':f'bytes */{total}'})
            a,b = match.groups()
            if a: inicio=int(a);fim=min(int(b),total-1) if b else total-1
            else: inicio=max(0,total-int(b));fim=total-1
            if inicio>fim or inicio>=total:
                return Response(status_code=416,headers={**headers,'Content-Range':f'bytes */{total}'})
            status=206;headers['Content-Range']=f'bytes {inicio}-{fim}/{total}'
        headers['Content-Length']=str(fim-inicio+1)
        raw = b'' if request.method=='HEAD' else con.execute('SELECT substr(arquivo,?,?) FROM midias WHERE id=?',(inicio+1,fim-inicio+1,identificador)).fetchone()[0]
    return Response(raw,status_code=status,media_type=r['mime'],headers=headers)


def vincular(con, usuario, publicacao, ids):
    if len(ids) != len(set(ids)):
        raise HTTPException(422, 'Há mídias repetidas na publicação.')
    for posicao, identificador in enumerate(ids):
        r = con.execute('SELECT usuario_id FROM midias WHERE id=?',(identificador,)).fetchone()
        if not r or r['usuario_id']!=usuario or con.execute('SELECT 1 FROM publicacao_midias WHERE midia=?',(identificador,)).fetchone():
            raise HTTPException(403, 'Uma mídia não pertence à sua conta ou já está publicada.')
        con.execute('INSERT INTO publicacao_midias VALUES (?,?,?)',(publicacao,identificador,posicao))


def com_midias(con, rows):
    posts = [dict(r,midias=[]) for r in rows]
    if not posts:return posts
    por_id = {p['id']:p for p in posts}
    placeholders = ','.join('?' for _ in posts)
    for r in con.execute(f'SELECT p.publicacao,m.id,m.mime FROM publicacao_midias p JOIN midias m ON m.id=p.midia WHERE p.publicacao IN ({placeholders}) ORDER BY p.posicao', list(por_id)):
        por_id[r['publicacao']]['midias'].append({'id':r['id'],'url':'/api/midias/'+r['id'],'tipo':'video' if r['mime'].startswith('video/') else 'foto'})
    return posts
