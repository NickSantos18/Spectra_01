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


def test_laudo_so_referencia_elementos_presentes_na_pagina():
    """Uma referência obsoleta não pode interromper a apresentação de uma análise."""
    from spectra_link_guard.web.app import PARCIAIS
    html = _html('laudo.html')
    for parcial in re.findall(r'<!--PARCIAL:([a-z-]+)-->', html):
        html += (PARCIAIS / f'{parcial}.html').read_text(encoding='utf-8')
    ids = set(re.findall(r'id="([^"]+)"', html))
    js = (ESTATICOS / 'laudo.js').read_text(encoding='utf-8')
    referencias = set(re.findall(r'\$\("([^"]+)"\)', js))
    assert referencias <= ids, f'Elementos ausentes: {referencias - ids}'


def test_nenhum_neutro_antigo_fora_dos_tokens():
    for arquivo in ESTATICOS.iterdir():
        if arquivo.suffix not in {".css", ".js", ".html"} or arquivo.name == "tokens.css":
            continue
        texto = arquivo.read_text(encoding="utf-8").lower()
        for cor in NEUTROS_ANTIGOS:
            assert cor not in texto, f"{cor} ainda aparece em {arquivo.name}"


def test_nenhuma_classe_da_antiga_cor_base_do_tailwind():
    # A cor Tailwind "base" virou "fundo"; text-base agora é só tamanho de fonte.
    for arquivo in ESTATICOS.iterdir():
        if arquivo.suffix not in {".html", ".js"}:
            continue
        texto = arquivo.read_text(encoding="utf-8")
        for classe in ("bg-base", "bg-marca text-base"):
            assert classe not in texto, f"{classe} ainda aparece em {arquivo.name}"


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


def test_toda_pagina_carrega_animacoes_no_head_depois_do_movimento():
    for nome in PAGINAS:
        cabeca = _html(nome).split("</head>")[0]
        assert '<link rel="stylesheet" href="/static/animacoes.css">' in cabeca, nome
        assert '<script src="/static/animacoes.js"></script>' in cabeca, nome
        assert cabeca.index("/static/movimento.js") < cabeca.index("/static/animacoes.js"), nome


def test_home_nao_tem_mais_script_proprio_de_revelar():
    assert "IntersectionObserver" not in _html("inicio.html")


def test_historico_tem_apagar_tudo_com_confirmacao():
    html = _html("historico.html")
    assert 'id="hist-apagar-tudo"' in html
    assert '<dialog class="dialogo" id="dialogo-apagar"' in html


EFEITOS_POR_PAGINA = {
    "visao-geral.html": "varredura",
    "historico.html": "varredura",
    "aprender.html": "chuva-hex",
    "inicio.html": ["circuitos", "chuva-hex"],
}


def test_cada_tela_tem_o_efeito_de_fundo_combinado():
    for nome in PAGINAS:
        html = _html(nome)
        if nome == "comunidade.html":
            assert 'data-efeito="__FUNDO_COMUNIDADE__"' in html
            assert "/static/fundo.js" in html
            continue
        efeitos = re.findall(r'data-efeito="([a-z-]+)"', html)
        esperado = EFEITOS_POR_PAGINA.get(nome)
        if esperado:
            assert efeitos == (esperado if isinstance(esperado, list) else [esperado]), f"{nome}: {efeitos}"
            assert "/static/fundo.js" in html, nome
        else:
            assert efeitos == [], f"{nome} não deveria ter efeito de fundo: {efeitos}"
            assert "/static/fundo.js" not in html, nome


def test_toda_pagina_usa_viewport_fit_cover():
    for nome in PAGINAS:
        assert 'content="width=device-width, initial-scale=1, viewport-fit=cover"' in _html(nome), nome


def test_menu_tem_navegacao_de_celular():
    from spectra_link_guard.web.app import PARCIAIS

    menu = (PARCIAIS / "menu.html").read_text(encoding="utf-8")
    assert '<nav class="barra-abas"' in menu
    assert menu.count('class="aba-item"') == 4
    assert '<dialog class="gaveta" id="gaveta-mais"' in menu
    assert menu.count("data-abrir-mais") == 1
    assert 'data-menu="perfil"' not in menu
    assert 'data-conta' not in menu
