"""Perfis, mensagens privadas e comunidade, com persistência no SQLite."""
import base64
import hashlib
import os
import secrets
import struct
import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import bd, usuario_atual

router = APIRouter()
bd.registrar_esquema("""
CREATE TABLE IF NOT EXISTS seguidores (
 seguidor TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 seguido TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 criado_em TEXT NOT NULL, PRIMARY KEY(seguidor, seguido), CHECK(seguidor != seguido));
CREATE INDEX IF NOT EXISTS idx_seguidores_seguido ON seguidores(seguido);
CREATE TABLE IF NOT EXISTS perfis (
 usuario_id TEXT PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
 bio TEXT NOT NULL DEFAULT '', foto TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS mensagens (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 remetente TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 destinatario TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 texto TEXT NOT NULL, criado_em TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_mensagens_conversa ON mensagens(remetente, destinatario, id);
CREATE TABLE IF NOT EXISTS publicacoes (
 id TEXT PRIMARY KEY, tipo TEXT NOT NULL, autor TEXT NOT NULL REFERENCES usuarios(id),
 titulo TEXT NOT NULL, texto TEXT NOT NULL, criado_em TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS respostas (
 id INTEGER PRIMARY KEY AUTOINCREMENT, publicacao TEXT NOT NULL REFERENCES publicacoes(id) ON DELETE CASCADE,
 autor TEXT NOT NULL REFERENCES usuarios(id), texto TEXT NOT NULL, criado_em TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS especialistas (email TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS convites_blog (
 hash TEXT PRIMARY KEY, email TEXT NOT NULL, expira_em TEXT NOT NULL, usado INTEGER NOT NULL DEFAULT 0);
""")


def exigir(request):
    u = usuario_atual(request.cookies.get("spectra_sessao"))
    if not u:
        raise HTTPException(401, "Entre na sua conta para continuar.")
    if request.method != "GET":
        origem = request.headers.get("origin")
        if origem and origem != str(request.base_url).rstrip("/"):
            raise HTTPException(403, "Origem inválida.")
    return u


def editor(u):
    emails = os.getenv("SPECTRA_EDITOR_EMAILS", "").lower().split(",")
    return u["email"] in [e.strip() for e in emails if e.strip()]


def pode_publicar(u):
    with bd.conexao() as con:
        especialista = con.execute("SELECT 1 FROM especialistas WHERE email = ?", (u["email"],)).fetchone()
    return editor(u) or bool(especialista)


def data():
    return bd.agora().isoformat(timespec="seconds")


class Perfil(BaseModel):
    nome: str = Field(min_length=3, max_length=120)
    bio: str = Field(default="", max_length=1000)
    foto: str = Field(default="", max_length=700000)


@router.get("/api/perfil")
def perfil(request: Request):
    u = exigir(request)
    with bd.conexao() as con:
        p = con.execute("SELECT bio, foto FROM perfis WHERE usuario_id = ?", (u["id"],)).fetchone()
    return {**bd.publico(u), **(dict(p) if p else {"bio": "", "foto": ""}),
            "ip": request.client.host if request.client else "Indisponível",
            "editor": editor(u), "pode_publicar": pode_publicar(u)}


@router.get("/api/usuarios/{identificador}/perfil")
def perfil_membro(identificador: str, request: Request):
    visitante = exigir(request)
    with bd.conexao() as con:
        linha = con.execute("""SELECT u.id,u.nome,u.criado_em,COALESCE(p.bio,'') AS bio,
            COALESCE(p.foto,'') AS foto,
            EXISTS(SELECT 1 FROM seguidores s WHERE s.seguidor=? AND s.seguido=u.id) AS seguindo,
            (SELECT COUNT(*) FROM publicacoes pub WHERE pub.autor=u.id) AS total_publicacoes
            FROM usuarios u LEFT JOIN perfis p ON p.usuario_id=u.id WHERE u.id=?""",
            (visitante["id"], identificador)).fetchone()
    if not linha:
        raise HTTPException(404, "Perfil não encontrado.")
    return dict(linha)


@router.put("/api/perfil")
def salvar_perfil(p: Perfil, request: Request):
    u = exigir(request)
    if len(p.nome.strip()) < 3:
        raise HTTPException(422, "Informe um nome com pelo menos 3 caracteres.")
    if p.foto:
        # A interface converte a foto em PNG. SVG e URLs externas não são aceitos.
        try:
            if not p.foto.startswith("data:image/png;base64,"):
                raise ValueError()
            raw = base64.b64decode(p.foto.split(",", 1)[1], validate=True)
            if raw[:8] != b"\x89PNG\r\n\x1a\n" or len(raw) < 24:
                raise ValueError()
            w, h = struct.unpack(">II", raw[16:24])
            if not (0 < w <= 512 and 0 < h <= 512):
                raise ValueError()
        except (ValueError, struct.error):
            raise HTTPException(422, "Use uma imagem PNG de até 512 × 512 pixels.")
    with bd.conexao() as con:
        con.execute("UPDATE usuarios SET nome = ? WHERE id = ?", (p.nome.strip(), u["id"]))
        con.execute("INSERT INTO perfis(usuario_id,bio,foto) VALUES (?,?,?) ON CONFLICT(usuario_id) DO UPDATE SET bio=excluded.bio,foto=excluded.foto", (u["id"], p.bio.strip(), p.foto))
    return {"ok": True}


@router.get("/api/comunidade/usuarios")
def usuarios(request: Request, busca: str = ""):
    u = exigir(request)
    if len(busca) > 120:
        raise HTTPException(422, "Busca muito longa.")
    with bd.conexao() as con:
        rows = con.execute("SELECT u.id,u.nome,COALESCE(p.foto,'') AS foto FROM usuarios u LEFT JOIN perfis p ON p.usuario_id=u.id WHERE u.id != ? AND instr(lower(u.nome),lower(?)) > 0 AND EXISTS (SELECT 1 FROM seguidores s WHERE (s.seguidor=? AND s.seguido=u.id) OR (s.seguidor=u.id AND s.seguido=?)) ORDER BY u.nome LIMIT 50", (u["id"], busca, u["id"], u["id"])).fetchall()
    return [dict(r) for r in rows]


@router.post("/api/usuarios/{contato}/seguir")
def seguir(contato: str, request: Request):
    u = exigir(request)
    if contato == u["id"] or not bd.buscar_por_id(contato):
        raise HTTPException(404, "Usuário não encontrado.")
    with bd.conexao() as con:
        con.execute("INSERT OR IGNORE INTO seguidores VALUES (?,?,?)", (u["id"], contato, data()))
    return {"seguindo": True}


@router.delete("/api/usuarios/{contato}/seguir")
def deixar_seguir(contato: str, request: Request):
    u = exigir(request)
    with bd.conexao() as con:
        con.execute("DELETE FROM seguidores WHERE seguidor=? AND seguido=?", (u["id"], contato))
    return {"seguindo": False}


def exigir_vinculo(con, usuario, contato):
    if not con.execute("SELECT 1 FROM seguidores WHERE (seguidor=? AND seguido=?) OR (seguidor=? AND seguido=?)", (usuario,contato,contato,usuario)).fetchone():
        raise HTTPException(403, "Siga esta pessoa no Explorar para conversar.")


class Mensagem(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


@router.get("/api/chat/{contato}")
def conversa(contato: str, request: Request, depois: int = 0):
    u = exigir(request)
    with bd.conexao() as con:
        exigir_vinculo(con, u["id"], contato)
        rows = con.execute("SELECT id,remetente,destinatario,texto,criado_em FROM mensagens WHERE id > ? AND ((remetente=? AND destinatario=?) OR (remetente=? AND destinatario=?)) ORDER BY id DESC LIMIT 100", (depois, u["id"], contato, contato, u["id"])).fetchall()
    return [dict(r) for r in reversed(rows)]


@router.post("/api/chat/{contato}", status_code=201)
def enviar(contato: str, p: Mensagem, request: Request):
    u = exigir(request)
    if contato == u["id"] or not bd.buscar_por_id(contato):
        raise HTTPException(404, "Usuário não encontrado.")
    if not p.texto.strip():
        raise HTTPException(422, "Escreva uma mensagem.")
    with bd.conexao() as con:
        exigir_vinculo(con, u["id"], contato)
        recentes = con.execute("SELECT COUNT(*) FROM mensagens WHERE remetente=? AND criado_em>?", (u["id"], (bd.agora()-timedelta(minutes=1)).isoformat(timespec="seconds"))).fetchone()[0]
        if recentes >= 30:
            raise HTTPException(429, "Aguarde um momento para enviar mais mensagens.")
        con.execute("INSERT INTO mensagens(remetente,destinatario,texto,criado_em) VALUES (?,?,?,?)", (u["id"], contato, p.texto.strip(), data()))
    return {"ok": True}


class Publicacao(BaseModel):
    titulo: str = Field(min_length=5, max_length=180)
    texto: str = Field(min_length=10, max_length=20000)
    midias: list[str] = Field(default_factory=list, max_length=4)


def tipo_valido(tipo):
    if tipo not in ("blog", "forum"):
        raise HTTPException(404, "Página não encontrada.")


@router.get("/api/comunidade/{tipo}")
def listar(tipo: str, request: Request, autor: str | None = None):
    u = exigir(request)
    if tipo != "explorar":
        tipo_valido(tipo)
    with bd.conexao() as con:
        rows = con.execute("SELECT p.*,u.nome AS autor_nome,COALESCE(f.foto,'') AS autor_foto,EXISTS(SELECT 1 FROM seguidores s WHERE s.seguidor=? AND s.seguido=p.autor) AS seguindo, (SELECT count(*) FROM respostas r WHERE r.publicacao=p.id) AS respostas FROM publicacoes p JOIN usuarios u ON u.id=p.autor LEFT JOIN perfis f ON f.usuario_id=u.id WHERE (?='explorar' OR tipo=?) AND (? IS NULL OR p.autor=?) ORDER BY criado_em DESC,p.id DESC LIMIT 100", (u["id"],tipo,tipo,autor,autor)).fetchall()
        from .explorar import com_midias
        return com_midias(con, rows)


@router.post("/api/comunidade/{tipo}", status_code=201)
def publicar(tipo: str, p: Publicacao, request: Request):
    u = exigir(request)
    tipo_valido(tipo)
    if tipo == "blog" and not pode_publicar(u):
        raise HTTPException(403, "O blog recebe publicações de especialistas convidados.")
    if len(p.titulo.strip()) < 5 or len(p.texto.strip()) < 10:
        raise HTTPException(422, "Preencha o título e o conteúdo.")
    novo = uuid.uuid4().hex
    with bd.conexao() as con:
        recentes = con.execute("SELECT count(*) FROM publicacoes WHERE autor=? AND criado_em>?", (u["id"], (bd.agora()-timedelta(hours=1)).isoformat(timespec="seconds"))).fetchone()[0]
        if recentes >= 10:
            raise HTTPException(429, "Limite de 10 publicações por hora.")
        con.execute("INSERT INTO publicacoes VALUES (?,?,?,?,?,?)", (novo, tipo, u["id"], p.titulo.strip(), p.texto.strip(), data()))
        from .explorar import vincular
        vincular(con,u['id'],novo,p.midias)
    return {"id": novo}


@router.get("/api/publicacoes/{identificador}/respostas")
def respostas(identificador: str, request: Request):
    exigir(request)
    with bd.conexao() as con:
        rows = con.execute("SELECT r.*,u.nome AS autor_nome FROM respostas r JOIN usuarios u ON u.id=r.autor WHERE publicacao=? ORDER BY r.id LIMIT 200", (identificador,)).fetchall()
    return [dict(r) for r in rows]


@router.post("/api/publicacoes/{identificador}/respostas", status_code=201)
def responder(identificador: str, p: Mensagem, request: Request):
    u = exigir(request)
    if not p.texto.strip():
        raise HTTPException(422, "Escreva uma resposta.")
    with bd.conexao() as con:
        if not con.execute("SELECT 1 FROM publicacoes WHERE id=?", (identificador,)).fetchone():
            raise HTTPException(404, "Publicação não encontrada.")
        recentes = con.execute("SELECT count(*) FROM respostas WHERE autor=? AND criado_em>?", (u["id"], (bd.agora()-timedelta(minutes=1)).isoformat(timespec="seconds"))).fetchone()[0]
        if recentes >= 10:
            raise HTTPException(429, "Aguarde um momento antes de responder novamente.")
        con.execute("INSERT INTO respostas(publicacao,autor,texto,criado_em) VALUES (?,?,?,?)", (identificador,u["id"],p.texto.strip(),data()))
    return {"ok": True}


@router.delete("/api/publicacoes/{identificador}")
def excluir(identificador: str, request: Request):
    u = exigir(request)
    with bd.conexao() as con:
        p = con.execute("SELECT autor FROM publicacoes WHERE id=?", (identificador,)).fetchone()
        if not p or (p["autor"] != u["id"] and not editor(u)):
            raise HTTPException(404, "Publicação não encontrada.")
        midias=[r[0] for r in con.execute('SELECT midia FROM publicacao_midias WHERE publicacao=?',(identificador,))]
        con.execute("DELETE FROM publicacoes WHERE id=?", (identificador,))
        for midia in midias:con.execute('DELETE FROM midias WHERE id=?',(midia,))
    return {"ok": True}


class Convite(BaseModel):
    email: str = Field(min_length=3, max_length=254)


@router.post("/api/blog/convites", status_code=201)
def convidar(p: Convite, request: Request):
    u = exigir(request)
    if not editor(u):
        raise HTTPException(403, "Apenas editores podem convidar especialistas.")
    from pydantic import TypeAdapter, EmailStr, ValidationError
    try:
        email = str(TypeAdapter(EmailStr).validate_python(p.email)).lower()
    except ValidationError:
        raise HTTPException(422, "Informe um e-mail válido.")
    token = secrets.token_urlsafe(32)
    with bd.conexao() as con:
        con.execute("INSERT INTO convites_blog(hash,email,expira_em) VALUES (?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), email, (bd.agora()+timedelta(days=7)).isoformat(timespec="seconds")))
    return {"link": str(request.base_url).rstrip("/")+"/painel/blog?convite="+token}


class Aceite(BaseModel):
    token: str = Field(min_length=20, max_length=100)


@router.post("/api/blog/aceitar")
def aceitar(p: Aceite, request: Request):
    u = exigir(request)
    chave = hashlib.sha256(p.token.encode()).hexdigest()
    with bd.conexao() as con:
        convite = con.execute("SELECT * FROM convites_blog WHERE hash=? AND usado=0 AND expira_em>?", (chave,data())).fetchone()
        if not convite or convite["email"] != u["email"]:
            raise HTTPException(403, "Convite inválido, expirado ou destinado a outro e-mail.")
        con.execute("INSERT OR IGNORE INTO especialistas VALUES (?)", (u["email"],))
        con.execute("UPDATE convites_blog SET usado=1 WHERE hash=?", (chave,))
    return {"ok": True}
