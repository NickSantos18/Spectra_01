"""Histórico de análises por usuário, guardado no SQLite.

Substitui o histórico em memória que vivia em app.py: ele era global (todo
usuário via as análises de todos) e sumia ao reiniciar o servidor.

PRIVACIDADE: guarda host, domínio registrável, nota, nível, horário e os
códigos dos sinais de risco — nunca a URL completa, porque caminho e query
podem carregar token de sessão ou dado pessoal.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ..auth import bd
from ..models import AnaliseLink, NivelRisco, Severidade
from .rotulos_sinais import rotulo_do_sinal

#: Análises guardadas por usuário; ao passar disso, as mais antigas saem.
LIMITE_POR_USUARIO = 500

#: Quantos sinais entram no gráfico de "mais frequentes".
TOP_SINAIS = 8

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS analises (
    id          TEXT PRIMARY KEY,
    usuario_id  TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    host        TEXT,
    dominio     TEXT,
    risco       INTEGER NOT NULL,
    nivel       TEXT NOT NULL,
    codigos     TEXT NOT NULL DEFAULT '[]',
    quando      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_analises_usuario_quando ON analises(usuario_id, quando);
"""
bd.registrar_esquema(_ESQUEMA)

_NIVEIS = [n.value for n in NivelRisco]
_PERIGOSOS = (NivelRisco.ALTO.value, NivelRisco.CRITICO.value)
_SEGUROS = (NivelRisco.SEGURO.value, NivelRisco.BAIXO.value)


def _arredondar(valor: float) -> int:
    """Meio para cima: o round() do Python leva 2,5 a 2 (arredondamento bancário)."""
    return int(valor + 0.5)


def registrar(usuario_id: str, relatorio: AnaliseLink) -> str:
    """Guarda a análise do usuário e devolve o id dela."""
    item_id = uuid.uuid4().hex[:12]
    codigos = sorted(
        {a.codigo for a in relatorio.achados if a.severidade is not Severidade.INFO}
    )
    with bd.conexao() as con:
        con.execute(
            """INSERT INTO analises
               (id, usuario_id, host, dominio, risco, nivel, codigos, quando)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item_id, usuario_id, relatorio.host, relatorio.dominio_registravel,
                relatorio.risco, relatorio.nivel.value, json.dumps(codigos),
                relatorio.analisado_em,
            ),
        )
        con.execute(
            """DELETE FROM analises WHERE usuario_id = ? AND id NOT IN (
                   SELECT id FROM analises WHERE usuario_id = ?
                   ORDER BY quando DESC, rowid DESC LIMIT ?)""",
            (usuario_id, usuario_id, LIMITE_POR_USUARIO),
        )
    return item_id


def listar(usuario_id: str, limite: int | None = None) -> list[dict[str, Any]]:
    """Análises do usuário, da mais recente para a mais antiga."""
    with bd.conexao() as con:
        if limite is None:
            linhas = con.execute(
                """SELECT id, host, dominio, risco, nivel, quando FROM analises
                   WHERE usuario_id = ? ORDER BY quando DESC, rowid DESC""",
                (usuario_id,),
            ).fetchall()
        else:
            linhas = con.execute(
                """SELECT id, host, dominio, risco, nivel, quando FROM analises
                   WHERE usuario_id = ? ORDER BY quando DESC, rowid DESC LIMIT ?""",
                (usuario_id, limite),
            ).fetchall()
    return [dict(linha) for linha in linhas]


def remover(usuario_id: str, item_id: str) -> bool:
    """Apaga uma análise do usuário. ``False`` se não existe ou é de outro."""
    with bd.conexao() as con:
        cursor = con.execute(
            "DELETE FROM analises WHERE id = ? AND usuario_id = ?", (item_id, usuario_id)
        )
        return cursor.rowcount > 0


def remover_todas(usuario_id: str) -> int:
    """Apaga todo o histórico do usuário e devolve quantas análises saíram."""
    with bd.conexao() as con:
        return con.execute("DELETE FROM analises WHERE usuario_id = ?", (usuario_id,)).rowcount


def _contagem_por_nivel(con, usuario_id: str) -> dict[str, int]:
    contagem = {nivel: 0 for nivel in _NIVEIS}
    for linha in con.execute(
        "SELECT nivel, COUNT(*) AS n FROM analises WHERE usuario_id = ? GROUP BY nivel",
        (usuario_id,),
    ):
        contagem[linha["nivel"]] = linha["n"]
    return contagem


def resumo(usuario_id: str) -> dict[str, Any]:
    """Indicadores rápidos — mesmo formato do antigo histórico em memória."""
    with bd.conexao() as con:
        contagem = _contagem_por_nivel(con, usuario_id)
    return {
        "total": sum(contagem.values()),
        "por_nivel": contagem,
        "perigosos": sum(contagem[n] for n in _PERIGOSOS),
        "recentes": listar(usuario_id, limite=12),
    }


def estatisticas(usuario_id: str, dias: int = 30, hoje: date | None = None) -> dict[str, Any]:
    """Números do dashboard, já agregados. Datas em UTC."""
    hoje = hoje or datetime.now(timezone.utc).date()
    inicio = hoje - timedelta(days=dias - 1)
    with bd.conexao() as con:
        contagem = _contagem_por_nivel(con, usuario_id)
        media = con.execute(
            "SELECT AVG(risco) AS m FROM analises WHERE usuario_id = ?", (usuario_id,)
        ).fetchone()["m"]
        diarios = {
            linha["dia"]: linha
            for linha in con.execute(
                """SELECT substr(quando, 1, 10) AS dia, COUNT(*) AS total, AVG(risco) AS media
                   FROM analises WHERE usuario_id = ? AND substr(quando, 1, 10) >= ?
                   GROUP BY dia""",
                (usuario_id, inicio.isoformat()),
            )
        }
        sinais: Counter[str] = Counter()
        for linha in con.execute(
            "SELECT codigos FROM analises WHERE usuario_id = ?", (usuario_id,)
        ):
            sinais.update(json.loads(linha["codigos"]))

    total = sum(contagem.values())
    por_dia = []
    for deslocamento in range(dias):
        dia = (inicio + timedelta(days=deslocamento)).isoformat()
        linha = diarios.get(dia)
        por_dia.append({
            "dia": dia,
            "total": linha["total"] if linha else 0,
            "risco_medio": _arredondar(linha["media"]) if linha else 0,
        })
    frequentes = sorted(sinais.items(), key=lambda par: (-par[1], par[0]))[:TOP_SINAIS]
    seguras = sum(contagem[n] for n in _SEGUROS)
    return {
        "total": total,
        "perigosos": sum(contagem[n] for n in _PERIGOSOS),
        "risco_medio": _arredondar(media) if media is not None else 0,
        "pct_seguras": _arredondar(100 * seguras / total) if total else 0,
        "por_nivel": contagem,
        "por_dia": por_dia,
        "sinais_frequentes": [
            {"codigo": codigo, "rotulo": rotulo_do_sinal(codigo), "vezes": vezes}
            for codigo, vezes in frequentes
        ],
    }
