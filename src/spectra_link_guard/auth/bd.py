"""Banco de usuários e sessões (SQLite).

Escolha deliberada: SQLite em arquivo, sem ORM. São três tabelas pequenas e
consultas diretas — trazer SQLAlchemy aqui custaria mais do que resolve. Se o
produto crescer para Postgres, o contrato deste módulo (as funções abaixo) é o
que muda de implementação; o resto do código não vê SQL.

TODAS as consultas usam parâmetros ligados (`?`). Nenhuma string de SQL é
montada por concatenação — a aplicação inteira lida com entrada de terceiros.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

#: Caminho do arquivo. Em produção, aponte para um volume persistente.
CAMINHO_BD = Path(os.getenv("SPECTRA_BD", "dados/spectra.db"))

#: Quanto tempo uma sessão vale sem novo login.
DIAS_DE_SESSAO = 14

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id                TEXT PRIMARY KEY,
    nome              TEXT NOT NULL,
    email             TEXT NOT NULL UNIQUE,   -- sempre em minúsculas
    senha_hash        TEXT,                   -- NULL em conta criada pelo Google
    google_sub        TEXT UNIQUE,            -- id estável do Google
    email_verificado  INTEGER NOT NULL DEFAULT 0,
    criado_em         TEXT NOT NULL,
    ultimo_acesso     TEXT
);

CREATE TABLE IF NOT EXISTS sessoes (
    id          TEXT PRIMARY KEY,
    usuario_id  TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    criado_em   TEXT NOT NULL,
    expira_em   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessoes_usuario ON sessoes(usuario_id);
CREATE INDEX IF NOT EXISTS idx_sessoes_expira  ON sessoes(expira_em);
"""

#: Esquemas criados na primeira conexão do processo. Outros módulos (ex.:
#: web/analises.py) acrescentam suas tabelas por registrar_esquema().
_ESQUEMAS: list[str] = [_ESQUEMA]


def agora() -> datetime:
    return datetime.now(timezone.utc)


#: Garante que o esquema existe antes da primeira consulta do processo, sem
#: depender de alguém lembrar de chamar preparar() na subida do servidor.
_PRONTO = False


@contextmanager
def conexao() -> Iterator[sqlite3.Connection]:
    """Abre uma conexão por operação — simples e sem estado compartilhado."""
    global _PRONTO
    CAMINHO_BD.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(CAMINHO_BD, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    if not _PRONTO:
        for esquema in _ESQUEMAS:
            con.executescript(esquema)
        con.commit()
        _PRONTO = True
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def preparar() -> None:
    """Cria o esquema se ainda não existir. Idempotente."""
    with conexao():
        pass


def registrar_esquema(sql: str) -> None:
    """Acrescenta tabelas de outro módulo ao esquema criado na primeira conexão."""
    global _PRONTO
    if sql not in _ESQUEMAS:
        _ESQUEMAS.append(sql)
        _PRONTO = False


# --------------------------------------------------------------------------- #
# Usuários
# --------------------------------------------------------------------------- #


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def buscar_por_email(email: str) -> dict[str, Any] | None:
    with conexao() as con:
        linha = con.execute(
            "SELECT * FROM usuarios WHERE email = ?", (normalizar_email(email),)
        ).fetchone()
    return dict(linha) if linha else None


def buscar_por_google(sub: str) -> dict[str, Any] | None:
    with conexao() as con:
        linha = con.execute("SELECT * FROM usuarios WHERE google_sub = ?", (sub,)).fetchone()
    return dict(linha) if linha else None


def buscar_por_id(usuario_id: str) -> dict[str, Any] | None:
    with conexao() as con:
        linha = con.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return dict(linha) if linha else None


def criar_usuario(
    *,
    nome: str,
    email: str,
    senha_hash: str | None = None,
    google_sub: str | None = None,
    email_verificado: bool = False,
) -> dict[str, Any]:
    """Insere o usuário. Levanta ``sqlite3.IntegrityError`` se o e-mail repetir."""
    novo = {
        "id": uuid.uuid4().hex,
        "nome": nome.strip(),
        "email": normalizar_email(email),
        "senha_hash": senha_hash,
        "google_sub": google_sub,
        "email_verificado": int(email_verificado),
        "criado_em": agora().isoformat(timespec="seconds"),
        "ultimo_acesso": None,
    }
    with conexao() as con:
        con.execute(
            """INSERT INTO usuarios
               (id, nome, email, senha_hash, google_sub, email_verificado, criado_em, ultimo_acesso)
               VALUES (:id, :nome, :email, :senha_hash, :google_sub, :email_verificado,
                       :criado_em, :ultimo_acesso)""",
            novo,
        )
    return novo


def vincular_google(usuario_id: str, sub: str, *, email_verificado: bool) -> None:
    """Liga uma conta existente (criada por senha) ao login do Google.

    Só promove o e-mail a verificado quando o próprio Google o atestou — nunca
    rebaixa um e-mail que já estava verificado.
    """
    with conexao() as con:
        con.execute(
            "UPDATE usuarios SET google_sub = ?, email_verificado = MAX(email_verificado, ?) "
            "WHERE id = ?",
            (sub, int(email_verificado), usuario_id),
        )


def marcar_acesso(usuario_id: str) -> None:
    with conexao() as con:
        con.execute(
            "UPDATE usuarios SET ultimo_acesso = ? WHERE id = ?",
            (agora().isoformat(timespec="seconds"), usuario_id),
        )


# --------------------------------------------------------------------------- #
# Sessões
# --------------------------------------------------------------------------- #


def abrir_sessao(usuario_id: str, dias: int = DIAS_DE_SESSAO) -> str:
    """Cria a sessão no banco e devolve o id que vai assinado no cookie.

    A sessão vive no servidor de propósito: sem isso, "sair" não revoga nada —
    um cookie assinado continuaria válido até expirar.
    """
    sessao_id = uuid.uuid4().hex
    inicio = agora()
    with conexao() as con:
        con.execute(
            "INSERT INTO sessoes (id, usuario_id, criado_em, expira_em) VALUES (?, ?, ?, ?)",
            (
                sessao_id,
                usuario_id,
                inicio.isoformat(timespec="seconds"),
                (inicio + timedelta(days=dias)).isoformat(timespec="seconds"),
            ),
        )
    return sessao_id


def usuario_da_sessao(sessao_id: str) -> dict[str, Any] | None:
    """Devolve o dono da sessão, ou ``None`` se ela não existe ou venceu."""
    with conexao() as con:
        linha = con.execute(
            """SELECT u.* FROM sessoes s
               JOIN usuarios u ON u.id = s.usuario_id
               WHERE s.id = ? AND s.expira_em > ?""",
            (sessao_id, agora().isoformat(timespec="seconds")),
        ).fetchone()
    return dict(linha) if linha else None


def renovar_sessao(sessao_id: str, dias: int = DIAS_DE_SESSAO) -> bool:
    """Empurra o vencimento de uma sessão ainda válida para ``dias`` a partir de agora.

    Quem usa o painel não é deslogado no meio do caminho: só "Sair" encerra.
    Devolve ``False`` se a sessão já não existe ou venceu (não ressuscita).
    """
    inicio = agora()
    with conexao() as con:
        cur = con.execute(
            "UPDATE sessoes SET expira_em = ? WHERE id = ? AND expira_em > ?",
            (
                (inicio + timedelta(days=dias)).isoformat(timespec="seconds"),
                sessao_id,
                inicio.isoformat(timespec="seconds"),
            ),
        )
        return cur.rowcount == 1


def fechar_sessao(sessao_id: str) -> None:
    with conexao() as con:
        con.execute("DELETE FROM sessoes WHERE id = ?", (sessao_id,))


def limpar_sessoes_vencidas() -> int:
    with conexao() as con:
        cur = con.execute(
            "DELETE FROM sessoes WHERE expira_em <= ?",
            (agora().isoformat(timespec="seconds"),),
        )
        return cur.rowcount


def publico(usuario: dict[str, Any]) -> dict[str, Any]:
    """Recorte seguro para mandar ao navegador — nunca inclui hash nem sub."""
    return {
        "id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
        "email_verificado": bool(usuario["email_verificado"]),
        "tem_senha": usuario["senha_hash"] is not None,
        "tem_google": usuario["google_sub"] is not None,
        "criado_em": usuario["criado_em"],
    }
