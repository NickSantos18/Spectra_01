"""Regras de estrutura do front-end que dá para checar sem navegador."""

from __future__ import annotations

import re

from spectra_link_guard.web.app import ESTATICOS

PAGINAS = sorted(p.name for p in ESTATICOS.glob("*.html"))

NEUTROS_ANTIGOS = (
    "#0f171a", "#131e22", "#18262b", "#1e3037",
    "#22353b", "#2e474f", "#9fb3b8", "#85999f",
)

TOKENS_OBRIGATORIOS = (
    "base", "base-2", "base-3", "base-4", "linha", "linha-forte",
    "texto", "texto-2", "texto-3",
)


def _blocos(css: str) -> dict[str, str]:
    sem_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return {
        seletor.strip(): corpo
        for seletor, corpo in re.findall(r"([^{}]+)\{([^{}]*)\}", sem_comentarios)
    }


def _html(nome: str) -> str:
    return (ESTATICOS / nome).read_text(encoding="utf-8")


def test_paginas_existem():
    esperadas = {"inicio.html", "laudo.html", "historico.html", "aprender.html",
                 "privacidade.html", "termos.html"}
    assert esperadas <= set(PAGINAS)


def test_nenhum_neutro_antigo_fora_dos_tokens():
    for arquivo in ESTATICOS.iterdir():
        if arquivo.suffix not in {".css", ".js", ".html"} or arquivo.name == "tokens.css":
            continue
        texto = arquivo.read_text(encoding="utf-8").lower()
        for cor in NEUTROS_ANTIGOS:
            assert cor not in texto, f"{cor} ainda aparece em {arquivo.name}"


def test_tokens_definem_tema_escuro_e_claro_com_triplets():
    blocos = _blocos((ESTATICOS / "tokens.css").read_text(encoding="utf-8"))
    escuro = blocos[":root"]
    claro = blocos[':root[data-tema="claro"]']
    for nome in TOKENS_OBRIGATORIOS:
        for bloco in (escuro, claro):
            assert f"--{nome}:" in bloco
            assert f"--{nome}-rgb:" in bloco
    assert "--base: #070B14;" in escuro


def test_toda_pagina_carrega_tokens_antes_dos_outros_estilos():
    for nome in PAGINAS:
        folhas = re.findall(r'<link rel="stylesheet" href="/static/([^"]+)"', _html(nome))
        assert folhas and folhas[0] == "tokens.css", f"{nome}: {folhas}"
