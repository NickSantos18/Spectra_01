"""Histórico de análises por usuário (SQLite). Banco isolado pelo conftest."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from spectra_link_guard.auth import bd
from spectra_link_guard.models import Achado, AnaliseLink, NivelRisco, Severidade
from spectra_link_guard.web import analises
from spectra_link_guard.web.rotulos_sinais import ROTULOS_SINAIS, rotulo_do_sinal


def _usuario(email: str = "ana@exemplo.com.br") -> str:
    return bd.criar_usuario(nome="Pessoa Teste", email=email, senha_hash="x")["id"]


def _achado(codigo: str, severidade: Severidade = Severidade.MEDIA) -> Achado:
    return Achado(codigo=codigo, titulo=codigo, severidade=severidade, detalhe="", recomendacao="")


def _relatorio(host="exemplo.com", risco=0, nivel=NivelRisco.SEGURO,
               quando="2026-10-08T12:00:00+00:00", codigos=(), info=()) -> AnaliseLink:
    return AnaliseLink(
        url_original=f"https://{host}/caminho?token=segredo-do-usuario",
        host=host,
        dominio_registravel=host,
        achados=[_achado(c) for c in codigos] + [_achado(c, Severidade.INFO) for c in info],
        risco=risco,
        nivel=nivel,
        analisado_em=quando,
    )


def test_registrar_e_listar_devolvem_so_campos_publicos():
    usuario = _usuario()
    item_id = analises.registrar(usuario, _relatorio(risco=10, nivel=NivelRisco.BAIXO))
    itens = analises.listar(usuario)
    assert len(itens) == 1
    assert itens[0] == {
        "id": item_id, "host": "exemplo.com", "dominio": "exemplo.com",
        "risco": 10, "nivel": "baixo", "quando": "2026-10-08T12:00:00+00:00",
    }


def test_nunca_grava_a_url_completa():
    usuario = _usuario()
    analises.registrar(usuario, _relatorio())
    with bd.conexao() as con:
        linha = dict(con.execute("SELECT * FROM analises").fetchone())
    assert "segredo-do-usuario" not in str(linha)
    assert "url" not in " ".join(linha)


def test_listar_vem_da_mais_recente_para_a_mais_antiga():
    usuario = _usuario()
    analises.registrar(usuario, _relatorio(host="velho.com", quando="2026-10-01T10:00:00+00:00"))
    analises.registrar(usuario, _relatorio(host="novo.com", quando="2026-10-08T10:00:00+00:00"))
    assert [i["host"] for i in analises.listar(usuario)] == ["novo.com", "velho.com"]


def test_um_usuario_nao_ve_as_analises_do_outro():
    ana, bruno = _usuario("ana@exemplo.com.br"), _usuario("bruno@exemplo.com.br")
    analises.registrar(ana, _relatorio())
    assert analises.listar(bruno) == []
    assert analises.estatisticas(bruno)["total"] == 0


def test_remover_so_apaga_do_dono():
    ana, bruno = _usuario("ana@exemplo.com.br"), _usuario("bruno@exemplo.com.br")
    item_id = analises.registrar(ana, _relatorio())
    assert analises.remover(bruno, item_id) is False
    assert len(analises.listar(ana)) == 1
    assert analises.remover(ana, item_id) is True
    assert analises.listar(ana) == []


def test_remover_todas():
    usuario = _usuario()
    analises.registrar(usuario, _relatorio())
    analises.registrar(usuario, _relatorio())
    assert analises.remover_todas(usuario) == 2
    assert analises.listar(usuario) == []


def test_remover_todas_so_apaga_as_do_dono():
    ana, bruno = _usuario("ana@exemplo.com.br"), _usuario("bruno@exemplo.com.br")
    analises.registrar(ana, _relatorio(host="ana.com"))
    analises.registrar(ana, _relatorio(host="ana.com"))
    do_bruno = analises.registrar(bruno, _relatorio(host="bruno.com"))

    assert analises.remover_todas(ana) == 2
    assert analises.listar(ana) == []
    assert [i["id"] for i in analises.listar(bruno)] == [do_bruno]
    assert analises.resumo(bruno)["total"] == 1


def test_banco_ja_aberto_ganha_a_tabela_registrada_depois(monkeypatch):
    """Caminho real de atualização: a primeira conexão do processo já criou
    só usuarios/sessoes quando o esquema de analises chega."""
    monkeypatch.setattr(bd, "_ESQUEMAS", [bd._ESQUEMA])
    usuario = _usuario()
    assert bd._PRONTO is True
    with bd.conexao() as con:
        tabelas = {nome for (nome,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "analises" not in tabelas

    bd.registrar_esquema(analises._ESQUEMA)

    item_id = analises.registrar(usuario, _relatorio())
    assert [i["id"] for i in analises.listar(usuario)] == [item_id]


def test_limite_por_usuario_descarta_as_mais_antigas(monkeypatch):
    monkeypatch.setattr(analises, "LIMITE_POR_USUARIO", 3)
    usuario = _usuario()
    for dia in range(1, 5):
        analises.registrar(usuario, _relatorio(host=f"d{dia}.com", quando=f"2026-10-0{dia}T10:00:00+00:00"))
    assert [i["host"] for i in analises.listar(usuario)] == ["d4.com", "d3.com", "d2.com"]


def test_apagar_o_usuario_apaga_as_analises():
    usuario = _usuario()
    analises.registrar(usuario, _relatorio())
    with bd.conexao() as con:
        con.execute("DELETE FROM usuarios WHERE id = ?", (usuario,))
    with bd.conexao() as con:
        assert con.execute("SELECT COUNT(*) FROM analises").fetchone()[0] == 0


def test_resumo_mantem_o_formato_do_painel():
    usuario = _usuario()
    analises.registrar(usuario, _relatorio(risco=80, nivel=NivelRisco.CRITICO))
    analises.registrar(usuario, _relatorio(risco=0, nivel=NivelRisco.SEGURO))
    resumo = analises.resumo(usuario)
    assert resumo["total"] == 2
    assert resumo["perigosos"] == 1
    assert resumo["por_nivel"] == {"seguro": 1, "baixo": 0, "atencao": 0, "alto": 0, "critico": 1}
    assert len(resumo["recentes"]) == 2


def test_estatisticas_vazias():
    estat = analises.estatisticas(_usuario(), dias=3, hoje=date(2026, 10, 8))
    assert estat["total"] == 0
    assert estat["risco_medio"] == 0
    assert estat["pct_seguras"] == 0
    assert estat["sinais_frequentes"] == []
    assert [d["dia"] for d in estat["por_dia"]] == ["2026-10-06", "2026-10-07", "2026-10-08"]


def test_estatisticas_conferidas_a_mao():
    usuario = _usuario()
    analises.registrar(usuario, _relatorio(risco=80, nivel=NivelRisco.CRITICO, quando="2026-10-08T10:00:00+00:00",
                                           codigos=("tld_de_risco", "typosquatting")))
    analises.registrar(usuario, _relatorio(risco=10, nivel=NivelRisco.BAIXO, quando="2026-10-08T11:00:00+00:00",
                                           codigos=("tld_de_risco",)))
    analises.registrar(usuario, _relatorio(risco=0, nivel=NivelRisco.SEGURO, quando="2026-10-07T09:00:00+00:00"))
    analises.registrar(usuario, _relatorio(risco=55, nivel=NivelRisco.ALTO, quando="2026-10-01T09:00:00+00:00",
                                           codigos=("encurtador",)))

    estat = analises.estatisticas(usuario, dias=3, hoje=date(2026, 10, 8))

    assert estat["total"] == 4
    assert estat["perigosos"] == 2                       # crítico + alto
    assert estat["risco_medio"] == 36                    # 145 / 4 = 36,25
    assert estat["pct_seguras"] == 50                    # seguro + baixo = 2 de 4
    assert estat["por_nivel"] == {"seguro": 1, "baixo": 1, "atencao": 0, "alto": 1, "critico": 1}
    assert estat["por_dia"] == [
        {"dia": "2026-10-06", "total": 0, "risco_medio": 0},
        {"dia": "2026-10-07", "total": 1, "risco_medio": 0},
        {"dia": "2026-10-08", "total": 2, "risco_medio": 45},
    ]
    assert estat["sinais_frequentes"] == [
        {"codigo": "tld_de_risco", "rotulo": ROTULOS_SINAIS["tld_de_risco"], "vezes": 2},
        {"codigo": "encurtador", "rotulo": ROTULOS_SINAIS["encurtador"], "vezes": 1},
        {"codigo": "typosquatting", "rotulo": ROTULOS_SINAIS["typosquatting"], "vezes": 1},
    ]


def test_arredonda_meio_para_cima():
    usuario = _usuario()
    analises.registrar(usuario, _relatorio(risco=1))
    analises.registrar(usuario, _relatorio(risco=2))
    assert analises.estatisticas(usuario, hoje=date(2026, 10, 8))["risco_medio"] == 2  # 1,5 → 2


def test_sinais_informativos_nao_entram_na_contagem():
    usuario = _usuario()
    analises.registrar(usuario, _relatorio(codigos=("encurtador",), info=("sem_spf", "dominio_estabelecido")))
    sinais = analises.estatisticas(usuario, hoje=date(2026, 10, 8))["sinais_frequentes"]
    assert [s["codigo"] for s in sinais] == ["encurtador"]


def test_rotulos_cobrem_todos_os_codigos_de_achado():
    raiz = Path(analises.__file__).resolve().parents[1]
    codigos = {"certificado_invalido"}  # vem de um if/else em tls.py
    for nome in ("sintaxe.py", "tls.py", "reputacao.py", "rede.py"):
        fonte = (raiz / nome).read_text(encoding="utf-8")
        codigos |= set(re.findall(r'Achado\(\s*codigo="([a-z_]+)"', fonte))
    faltando = codigos - set(ROTULOS_SINAIS)
    assert not faltando, f"sem rótulo: {sorted(faltando)}"


def test_codigo_desconhecido_vira_o_proprio_codigo():
    assert rotulo_do_sinal("codigo_que_nao_existe") == "codigo_que_nao_existe"
