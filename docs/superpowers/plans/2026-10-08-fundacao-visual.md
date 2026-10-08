# Fundação visual — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fundo azul quase preto via tokens únicos, histórico por usuário no SQLite com dashboard "Visão geral", partes compartilhadas (menu/rodapé/acessibilidade), micro-interações, efeitos de fundo e responsividade de 320px a 1920px.

**Architecture:** FastAPI serve HTML estático por `_pagina()`, que passa a encaixar parciais (`web/parciais/*.html`) e marcar o item ativo do menu. Cores saem só de `static/tokens.css` (hex + triplet RGB). Histórico vira o módulo `web/analises.py` sobre o SQLite de `auth/bd.py`. JS sem build: arquivos compartilhados (`menu.js`, `animacoes.js`, `fundo.js`) + um por tela.

**Tech Stack:** Python ≥3.11, FastAPI, SQLite (sem ORM), pytest; HTML/CSS/JS sem build; Tailwind via CDN só na home; Lucide 0.462.0 e Chart.js 4.4.4 via CDN com SRI (já usados).

**Spec:** `docs/superpowers/specs/2026-10-08-fundacao-visual-design.md`

## Global Constraints

- Nenhuma dependência nova de Python; nenhuma etapa de build/Node; nenhuma biblioteca de CDN nova (só Lucide 0.462.0 e Chart.js 4.4.4, sempre com `integrity` e `crossorigin`).
- Cor só em `src/spectra_link_guard/web/static/tokens.css`. Os neutros antigos `#0f171a #131e22 #18262b #1e3037 #22353b #2e474f #9fb3b8 #85999f` não podem aparecer em nenhum outro arquivo de `static/` (teste de regressão).
- Fundo do tema escuro: `#070B14`.
- Texto vindo do servidor ou do usuário entra no DOM só por `textContent` — nunca `innerHTML` com dados.
- SQL só com parâmetros ligados (`?`); nada de montar SQL por concatenação ou f-string.
- A URL completa analisada **nunca** é gravada (só host, domínio, nota, nível, horário e códigos de sinais).
- Toda animação obedece `data-movimento` (movimento.js): com `"off"`, nada se mexe e nada fica invisível. Animações CSS só em `transform`, `translate` e `opacity`.
- Sem rolagem horizontal a partir de 320px; alvos de toque ≥ 44px em ≤ 599px.
- Textos de interface novos não usam "—" como valor vazio (pedido do usuário sobre travessões ainda em aberto).
- Código e comentários em português, no estilo do projeto; comentário só quando o porquê não é óbvio.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Comandos rodam na raiz `C:\Users\Dev_2o_Ano\spectra 01` (Git Bash). Servidor de dev: preview `spectra-web` do `.claude/launch.json`, ou `python -m uvicorn spectra_link_guard.web.app:app --reload --port 8000`.

## Refinamentos do plano sobre o spec (para o usuário revisar)

1. **Hover:** cards pequenos (`.cartao-vivo`: indicadores, amostras, cards da home) sobem 2px; os quadros grandes do painel só ganham borda teal — levantar um painel da largura da tela parece tremedeira.
2. **`cubos.js`** mantém sua paleta: ele só usa cores de marca (teal/sálvia/amarelo), nenhum neutro.
3. **Tema claro:** além do teal, sálvia (`#3D6E5F`), amarelo (`#806500`) e vermelho (`#C62E24`) escurecem — os tons do escuro ficam abaixo de 4.5:1 sobre fundo claro.
4. **"Nesta análise"** (âncoras do laudo) sai do menu lateral, que agora é compartilhado, e vira uma fileira de atalhos fixa logo abaixo da barra de busca, que também funciona no celular.
5. **Tailwind:** a cor `base` vira `fundo`. O nome `base` colide com o utilitário de tamanho `text-base` — é por isso que o título do modal de login está hoje quase invisível (cor do fundo).
6. Scripts das telas novas carregam com `defer`, depois do Chart.js, evitando a corrida em que o gráfico tenta desenhar antes de a biblioteca existir.

## Mapa de arquivos

| Arquivo | Responsabilidade | Tarefa |
|---|---|---|
| `web/static/tokens.css` (novo) | todas as cores, temas e alto contraste | 1 |
| `web/analises.py` (novo) | histórico por usuário no SQLite + estatísticas | 2 |
| `web/rotulos_sinais.py` (novo) | nome legível de cada código de achado | 2 |
| `auth/bd.py` | `registrar_esquema()` para outros módulos criarem tabelas | 2 |
| `web/app.py` | `_pagina()` com parciais, rotas, API do histórico | 1, 2, 3, 4, 5, 6 |
| `web/parciais/menu.html` (novo) | menu lateral, conta, barra de abas e gaveta | 3, 5, 7 |
| `web/parciais/rodape.html` (novo) | rodapé único | 3 |
| `web/parciais/acessibilidade.html` (novo) | painel de acessibilidade único | 3 |
| `web/static/menu.js` (novo) | conta, sair e gaveta "Mais" | 3, 7 |
| `web/static/animacoes.css` / `animacoes.js` (novos) | revelar, hover, skeleton, contador, toast, transições | 4 |
| `web/static/visao-geral.html` / `visao-geral.js` (novos) | dashboard | 5 |
| `web/static/fundo.js` (novo) | efeitos varredura e chuva hexadecimal | 6 |
| `web/static/laudo.css` | layout do painel, componentes, responsividade | 1, 3, 4, 5, 7 |
| `web/static/rodape.css` | rodapé, documento, acessibilidade, brilho de fundo | 1, 6, 7 |
| `web/static/*.html` | telas | todas |
| `tests/test_analises.py` (novo), `tests/test_frontend.py` (novo), `tests/test_web.py` | testes | 1–7 |

---

### Task 1: Tokens de cor e fundo #070B14

**Files:**
- Create: `src/spectra_link_guard/web/static/tokens.css`
- Create: `tests/test_frontend.py`
- Modify: `src/spectra_link_guard/web/static/laudo.css` (bloco `:root` no topo e cores fixas)
- Modify: `src/spectra_link_guard/web/static/rodape.css` (fallbacks de cor, seções 4 e 5)
- Modify: `src/spectra_link_guard/web/static/inicio.html` (Tailwind, `<style>`, classes `*-base`)
- Modify: `src/spectra_link_guard/web/static/laudo.js`, `historico.js`, `acessibilidade.js`
- Modify: `laudo.html`, `historico.html`, `aprender.html`, `privacidade.html`, `termos.html` (link do `tokens.css`)
- Modify: `src/spectra_link_guard/web/app.py` (`_ATIVOS_BASE`)

**Interfaces:**
- Produces: variáveis CSS `--base`, `--base-2`, `--base-3`, `--base-4`, `--linha`, `--linha-forte`, `--texto`, `--texto-2`, `--texto-3`, `--primaria`, `--primaria-clara`, `--secundaria`, `--terciaria`, `--perigo`, `--sobre-primaria`, `--brilho-1`, `--brilho-2`, e cada cor também como `--<nome>-rgb` ("R G B"). Evento `window` `spectra:tema` (`detail`: `"claro"`/`"escuro"`) disparado pelo acessibilidade.js ao trocar o tema. Constante `_ATIVOS_BASE` em `app.py`. Cores Tailwind na home: `fundo`, `sup`, `sup-2`, `sup-3`, `linha`, `linha-forte`, `txt`, `txt-2`, `txt-3`, `marca`, `marca-claro`, `sage`, `amarelo`, `perigo`, `sobre-marca`.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_frontend.py`:

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_frontend.py -q`
Expected: FAIL — `tokens.css` não existe (`KeyError`/`FileNotFoundError`) e os neutros antigos ainda aparecem em `laudo.css`, `rodape.css` e `inicio.html`.

- [ ] **Step 3: Criar `tokens.css`**

Criar `src/spectra_link_guard/web/static/tokens.css`:

```css
/* Spectra — tokens de cor.
 *
 * Fonte única de cor do site. laudo.css, rodape.css, animacoes.css, o
 * Tailwind da home (inicio.html) e os canvas/gráficos (via getComputedStyle)
 * leem estas variáveis; nenhum outro arquivo define cor neutra.
 *
 * Cada cor existe duas vezes: em hex e como triplet RGB (`--x-rgb`), que o
 * Tailwind usa nos modificadores de opacidade (`bg-fundo/95`) e o JS usa em
 * `rgb(… / alfa)`. Ao mudar uma, mude a outra.
 *
 * Contrastes (WCAG) medidos contra o fundo de cada tema; texto precisa de
 * pelo menos 4.5:1.
 */

:root {
  --base: #070B14;            --base-rgb: 7 11 20;
  --base-2: #0C1220;          --base-2-rgb: 12 18 32;
  --base-3: #121A2B;          --base-3-rgb: 18 26 43;
  --base-4: #18223A;          --base-4-rgb: 24 34 58;
  --linha: #1C2638;           --linha-rgb: 28 38 56;
  --linha-forte: #2A3852;     --linha-forte-rgb: 42 56 82;

  --texto: #E7EEF0;           --texto-rgb: 231 238 240;         /* 16.7:1 */
  --texto-2: #9FB0C8;         --texto-2-rgb: 159 176 200;       /*  8.9:1 */
  --texto-3: #7E8DA6;         --texto-3-rgb: 126 141 166;       /*  5.9:1 */

  --primaria: #118E94;        --primaria-rgb: 17 142 148;
  --primaria-clara: #3FB6BB;  --primaria-clara-rgb: 63 182 187; /*  8.1:1 */
  --secundaria: #5B9986;      --secundaria-rgb: 91 153 134;
  --terciaria: #FFFC0E;       --terciaria-rgb: 255 252 14;
  --perigo: #FF4438;          --perigo-rgb: 255 68 56;
  --sobre-primaria: #04191A;  --sobre-primaria-rgb: 4 25 26;    /* sobre o teal: 4.6:1 */

  /* brilho estático dos cantos da página (rodape.css) */
  --brilho-1: rgb(17 142 148 / .09);
  --brilho-2: rgb(37 72 160 / .10);

  color-scheme: dark;
}

/* Tema claro. Teal, sálvia, amarelo e vermelho escurecem: como texto sobre
   fundo claro, os tons do tema escuro ficam abaixo de 4.5:1. */
:root[data-tema="claro"] {
  --base: #F3F6FA;            --base-rgb: 243 246 250;
  --base-2: #FFFFFF;          --base-2-rgb: 255 255 255;
  --base-3: #EAF0F6;          --base-3-rgb: 234 240 246;
  --base-4: #DFE7F0;          --base-4-rgb: 223 231 240;
  --linha: #D5DEE8;           --linha-rgb: 213 222 232;
  --linha-forte: #BCC9D8;     --linha-forte-rgb: 188 201 216;

  --texto: #0D1626;           --texto-rgb: 13 22 38;
  --texto-2: #3A4A63;         --texto-2-rgb: 58 74 99;
  --texto-3: #56657E;         --texto-3-rgb: 86 101 126;        /* 5.5:1 */

  --primaria-clara: #0B6E73;  --primaria-clara-rgb: 11 110 115; /* 6.0:1 */
  --secundaria: #3D6E5F;      --secundaria-rgb: 61 110 95;      /* 5.4:1 */
  --terciaria: #806500;       --terciaria-rgb: 128 101 0;       /* 5.1:1 */
  --perigo: #C62E24;          --perigo-rgb: 198 46 36;          /* 5.1:1 */

  --brilho-1: rgb(17 142 148 / .07);
  --brilho-2: rgb(37 72 160 / .06);

  color-scheme: light;
}

/* Alto contraste: bordas e textos secundários vão ao máximo do tema. */
:root[data-alto-contraste="on"] {
  --linha: var(--linha-forte);  --linha-rgb: var(--linha-forte-rgb);
  --texto-2: var(--texto);      --texto-2-rgb: var(--texto-rgb);
  --texto-3: var(--texto);      --texto-3-rgb: var(--texto-rgb);
}
:root[data-alto-contraste="on"] .quadro,
:root[data-alto-contraste="on"] .veredito,
:root[data-alto-contraste="on"] .trilho,
:root[data-alto-contraste="on"] .barra {
  border-width: 2px;
}
:root[data-alto-contraste="on"] :focus-visible {
  outline-width: 3px !important;
  outline-offset: 2px !important;
}
```

- [ ] **Step 4: `laudo.css` passa a ler os tokens**

Em `src/spectra_link_guard/web/static/laudo.css`:

(a) No comentário do topo, trocar as linhas

```
 * Tokens do design system da Spectra: teal #118E94, sage #5B9986,
 * amarelo #FFFC0E, neutro #0F171A. Tipos Hanken Grotesk (títulos),
 * Inter (corpo) e JetBrains Mono (dados).
```

por

```
 * Cores: todas vêm de tokens.css (carregado antes deste arquivo). Tipos
 * Hanken Grotesk (títulos), Inter (corpo) e JetBrains Mono (dados).
```

(b) Trocar o bloco `:root { … }` inteiro (do `:root {` até o `}` que fecha depois de `--vao: 14px;`) por:

```css
:root {
  --sinal: var(--texto-3);

  --fonte-titulo: "Hanken Grotesk", system-ui, sans-serif;
  --fonte-corpo: "Inter", system-ui, -apple-system, sans-serif;
  --fonte-mono: "JetBrains Mono", ui-monospace, "Cascadia Code", monospace;

  --trilho-l: 236px;
  --barra-h: 64px;
  --vao: 14px;
}
```

(c) Substituições no arquivo inteiro (todas as ocorrências):
- `color: #04191a;` → `color: var(--sobre-primaria);`
- `rgba(17, 142, 148, .18)` → `rgb(var(--primaria-rgb) / .18)`
- `rgba(17, 142, 148, .4)` → `rgb(var(--primaria-rgb) / .4)`
- `rgba(255, 68, 56, .12)` → `rgb(var(--perigo-rgb) / .12)`

(d) Corrigir o hover do "Sair" (usava uma variável que não existe): `.conta-sair:hover { color: var(--error-strong); }` → `.conta-sair:hover { color: var(--perigo); }`

- [ ] **Step 5: `rodape.css` sem fallbacks de cor e sem os blocos movidos**

(a) Remover os fallbacks de cor (`var(--x, #hex)` → `var(--x)`). Os fallbacks de fonte ficam, porque a home não carrega `laudo.css`. Rodar uma vez:

```bash
python - <<'EOF'
import re
from pathlib import Path
p = Path("src/spectra_link_guard/web/static/rodape.css")
texto = p.read_text(encoding="utf-8")
novo = re.sub(r"var\((--[a-z0-9-]+), #[0-9a-fA-F]{3,6}\)", r"var(\1)", texto)
novo = novo.replace("color: #04191a;", "color: var(--sobre-primaria);")
p.write_text(novo, encoding="utf-8")
print(len(re.findall(r"var\(--[a-z0-9-]+, #", texto)), "fallbacks removidos")
EOF
```

Expected: imprime um número > 20.

(b) Apagar as seções inteiras `/* ─── 4) tema claro */` e `/* ─── 5) alto contraste */` (do comentário da seção 4 até o fim do arquivo). Elas agora estão em `tokens.css`.

(c) No comentário do topo, trocar os itens 4 e 5 da lista por:

```
 *   4) tema claro e alto contraste moram em tokens.css.
```

- [ ] **Step 6: Tailwind da home lê os tokens; `base` vira `fundo`**

Em `src/spectra_link_guard/web/static/inicio.html`:

(a) Antes de `<link rel="stylesheet" href="/static/rodape.css">`, inserir:

```html
<link rel="stylesheet" href="/static/tokens.css">
```

(b) Trocar o `<script>` do `tailwind.config` (de `<script>` com `// Tokens do design system…` até o `</script>` correspondente) por:

```html
<script>
  // Cores do Tailwind apontam para os tokens (tokens.css), em triplet RGB para
  // os modificadores de opacidade funcionarem (bg-fundo/95). "fundo" e não
  // "base": uma cor chamada base colide com o utilitário de tamanho text-base.
  const token = (nome) => `rgb(var(--${nome}-rgb) / <alpha-value>)`;
  tailwind.config = {
    theme: {
      extend: {
        colors: {
          fundo:         token("base"),
          sup:           token("base-2"),
          "sup-2":       token("base-3"),
          "sup-3":       token("base-4"),
          linha:         token("linha"),
          "linha-forte": token("linha-forte"),
          txt:           token("texto"),
          "txt-2":       token("texto-2"),
          "txt-3":       token("texto-3"),
          marca:         token("primaria"),
          "marca-claro": token("primaria-clara"),
          sage:          token("secundaria"),
          amarelo:       token("terciaria"),
          perigo:        token("perigo"),
          "sobre-marca": token("sobre-primaria"),
        },
        fontFamily: {
          display: ['"Hanken Grotesk"', "system-ui", "sans-serif"],
          corpo:   ['"Inter"', "system-ui", "sans-serif"],
          mono:    ['"JetBrains Mono"', "ui-monospace", "monospace"],
        },
        boxShadow: {
          suave: "0 18px 40px -24px rgba(0,0,0,.9)",
          alta:  "0 30px 60px -30px rgba(0,0,0,1)",
        },
      },
    },
  };
</script>
```

(c) No `<style>` da home:
- `body { background: #0f171a; }` → `body { background: var(--base); }`
- `background-image: linear-gradient(180deg, #e7eef0, #9fb3b8);` → `background-image: linear-gradient(180deg, var(--texto), var(--texto-2));`
- no bloco do autofill: `-webkit-text-fill-color: #e7eef0;` → `-webkit-text-fill-color: var(--texto);`, `-webkit-box-shadow: 0 0 0 1000px #18262b inset;` → `-webkit-box-shadow: 0 0 0 1000px var(--base-3) inset;`, `caret-color: #e7eef0;` → `caret-color: var(--texto);`
- `border-color: #118e94;` → `border-color: var(--primaria);`

(d) Classes (rodar uma vez; renomeia `bg-base`→`bg-fundo` e troca `text-base` usado como **cor** sobre o teal por `text-sobre-marca`; os dois `text-base` que são tamanho de fonte — o parágrafo do hero e o título do modal — ficam):

```bash
python - <<'EOF'
from pathlib import Path
p = Path("src/spectra_link_guard/web/static/inicio.html")
t = p.read_text(encoding="utf-8")
antes = t
t = t.replace("bg-base/95", "bg-fundo/95").replace("bg-base/85", "bg-fundo/85")
t = t.replace('class="bg-base p-7', 'class="bg-fundo p-7')
t = t.replace("focus:text-base", "focus:text-sobre-marca")
t = t.replace("bg-marca text-base", "bg-marca text-sobre-marca")
t = t.replace("font-semibold text-base transition", "font-semibold text-sobre-marca transition")
t = t.replace("font-bold text-base", "font-bold text-sobre-marca")
p.write_text(t, encoding="utf-8")
print("text-sobre-marca:", t.count("text-sobre-marca"), "| bg-fundo:", t.count("bg-fundo"))
EOF
grep -n "text-base\|bg-base" src/spectra_link_guard/web/static/inicio.html
```

Expected: `text-sobre-marca: 9 | bg-fundo: 5`. O `grep` mostra só duas linhas com `text-base`: o `<p class="subir mt-6 max-w-xl text-base font-light …">` do hero e o `<h2 id="modal-titulo" class="font-display text-base font-bold">`. Nenhum `bg-base`.

- [ ] **Step 7: Demais páginas linkam `tokens.css` primeiro**

Em `laudo.html`, `historico.html`, `aprender.html`, `privacidade.html` e `termos.html`, inserir antes de `<link rel="stylesheet" href="/static/laudo.css">`:

```html
<link rel="stylesheet" href="/static/tokens.css">
```

- [ ] **Step 8: `app.py` versiona `tokens.css` em todas as páginas**

Em `src/spectra_link_guard/web/app.py`, logo depois de `ESTATICOS = Path(__file__).parent / "static"`, inserir:

```python

#: Ativos que toda página carrega; entram no cache-busting de _pagina().
_ATIVOS_BASE = ("tokens.css", "rodape.css", "movimento.js", "acessibilidade.js")
```

E trocar as chamadas `_pagina(...)` das rotas por:

```python
# /inicio
    return _pagina("inicio.html", *_ATIVOS_BASE, "caminhos.js", "inicio.js", "cubos.js")
# /painel
    return _pagina(
        "laudo.html", *_ATIVOS_BASE, "laudo.css",
        "glossario.js", "caminhos.js", "melhorias.js", "laudo.js",
    )
# /painel/historico
    return _pagina("historico.html", *_ATIVOS_BASE, "laudo.css", "historico.js")
# /painel/aprender
    return _pagina("aprender.html", *_ATIVOS_BASE, "laudo.css", "glossario.js")
# /privacidade
    return _pagina("privacidade.html", *_ATIVOS_BASE, "laudo.css")
# /termos
    return _pagina("termos.html", *_ATIVOS_BASE, "laudo.css")
```

- [ ] **Step 9: JS lê cores dos tokens e redesenha ao trocar o tema**

(a) `acessibilidade.js`: no handler do botão de tema, depois de `aplicarTema(tema);`, acrescentar:

```js
      window.dispatchEvent(new CustomEvent("spectra:tema", { detail: tema }));
```

(b) `laudo.js`: logo abaixo de `const $ = (id) => document.getElementById(id);`, acrescentar:

```js

/** Valor atual de um token de tokens.css (muda com o tema). */
function token(nome) {
  return getComputedStyle(document.documentElement).getPropertyValue(`--${nome}`).trim();
}
```

No construtor do `Poligrafo`, trocar `this.cor = "#85999f";` por:

```js
    this.cor = token("texto-3");
    this.corMarcas = `rgb(${token("texto-rgb")} / .07)`;
```

Em `configurar({ url, tensao, cor })`, depois de `this.cor = cor;`, acrescentar:

```js
    this.corMarcas = `rgb(${token("texto-rgb")} / .07)`;
```

Em `marcasDeFundo`, trocar `ctx.strokeStyle = "rgba(231, 238, 240, .07)";` por `ctx.strokeStyle = this.corMarcas;`.

Em `corDoSinal`, trocar `|| "#85999f"` por `|| token("texto-3")`.

Em `renderGrafico`, trocar `backgroundColor: [cor, "rgba(159, 179, 184, .16)"],` por `backgroundColor: [cor, token("linha")],`.

No fim da seção `fluxo` (logo depois do `for (const amostra of document.querySelectorAll(".amostra")) { … }`), acrescentar:

```js

// Trocar o tema muda as cores dos tokens: o medidor e o polígrafo redesenham.
window.addEventListener("spectra:tema", () => {
  if (!laudoAtual) return;
  poligrafo.configurar({ tensao: TENSAO[laudoAtual.nivel] ?? 0.5, cor: corDoSinal() });
  renderGrafico(laudoAtual);
});
```

(c) `historico.js`: trocar o bloco `const COR_NIVEL = { … };` por:

```js
const TOKEN_NIVEL = {
  seguro: "secundaria", baixo: "secundaria", atencao: "terciaria", alto: "perigo", critico: "perigo",
};

function corNivel(nivel) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(`--${TOKEN_NIVEL[nivel]}`).trim();
}
```

Trocar `ponto.style.background = COR_NIVEL[nivel];` por `ponto.style.background = corNivel(nivel);` e `backgroundColor: Object.keys(contagem).map((n) => COR_NIVEL[n])` por `backgroundColor: Object.keys(contagem).map(corNivel)`. Antes da linha `carregar();`, acrescentar:

```js
window.addEventListener("spectra:tema", renderizarResumo);
```

- [ ] **Step 10: Rodar os testes**

Run: `python -m pytest -q`
Expected: PASS (todos; os 4 de `test_frontend.py` incluídos).

- [ ] **Step 11: Conferir no navegador**

Subir o servidor, entrar (criar conta em `/inicio`) e, no console de `/painel`, `/painel/historico` e `/inicio`:

```js
({ fundo: getComputedStyle(document.body).backgroundColor,
   texto: getComputedStyle(document.body).color })
```

Expected: `fundo: "rgb(7, 11, 20)"`, `texto: "rgb(231, 238, 240)"`. Abrir o painel de acessibilidade, clicar em "Tema": o fundo vira `rgb(243, 246, 250)` em todas as telas, **inclusive a home**. Em `/inicio`, abrir "Entrar": o título "Acessar o Spectra" aparece claro (antes saía quase invisível). Nenhum erro no console.

- [ ] **Step 12: Commit**

```bash
git add src/spectra_link_guard/web/static/tokens.css tests/test_frontend.py \
  src/spectra_link_guard/web/static/laudo.css src/spectra_link_guard/web/static/rodape.css \
  src/spectra_link_guard/web/static/inicio.html src/spectra_link_guard/web/static/laudo.html \
  src/spectra_link_guard/web/static/historico.html src/spectra_link_guard/web/static/aprender.html \
  src/spectra_link_guard/web/static/privacidade.html src/spectra_link_guard/web/static/termos.html \
  src/spectra_link_guard/web/static/laudo.js src/spectra_link_guard/web/static/historico.js \
  src/spectra_link_guard/web/static/acessibilidade.js src/spectra_link_guard/web/app.py
git commit -m "$(cat <<'EOF'
Tokens de cor únicos e fundo #070B14

tokens.css passa a ser a fonte única de cor (hex + triplet RGB), com tema
claro e alto contraste. laudo.css, rodape.css, o Tailwind da home e os
gráficos leem os tokens; o remendo !important do tema claro sai. A cor
Tailwind "base" vira "fundo" para não colidir com o utilitário text-base,
o que deixava o título do modal de login quase invisível.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Histórico por usuário no SQLite

**Files:**
- Modify: `src/spectra_link_guard/auth/bd.py` (`registrar_esquema`, `conexao`)
- Create: `src/spectra_link_guard/web/rotulos_sinais.py`
- Create: `src/spectra_link_guard/web/analises.py`
- Modify: `src/spectra_link_guard/web/app.py` (remove `_Historico`; API nova)
- Modify: `src/spectra_link_guard/web/static/historico.js` (401)
- Create: `tests/test_analises.py`
- Modify: `tests/test_web.py` (reescrito)

**Interfaces:**
- Consumes: `bd.conexao()`, `bd.criar_usuario()`, `usuario_atual(cookie)`, `AnaliseLink`, `Achado`, `Severidade`, `NivelRisco`.
- Produces:
  - `bd.registrar_esquema(sql: str) -> None`
  - `analises.LIMITE_POR_USUARIO: int = 500`
  - `analises.registrar(usuario_id: str, relatorio: AnaliseLink) -> str`
  - `analises.listar(usuario_id: str, limite: int | None = None) -> list[dict]` — itens `{id, host, dominio, risco, nivel, quando}`
  - `analises.remover(usuario_id: str, item_id: str) -> bool`
  - `analises.remover_todas(usuario_id: str) -> int`
  - `analises.resumo(usuario_id: str) -> dict` — `{total, por_nivel, perigosos, recentes}`
  - `analises.estatisticas(usuario_id: str, dias: int = 30, hoje: date | None = None) -> dict` — `{total, perigosos, risco_medio, pct_seguras, por_nivel, por_dia, sinais_frequentes}`
  - `rotulos_sinais.ROTULOS_SINAIS: dict[str, str]`, `rotulos_sinais.rotulo_do_sinal(codigo: str) -> str`
  - API: `GET /api/painel`, `GET /api/painel/historico`, `GET /api/painel/estatisticas`, `DELETE /api/painel/{id}`, `DELETE /api/painel` — 401 sem sessão.

- [ ] **Step 1: Escrever os testes do módulo**

Criar `tests/test_analises.py`:

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_analises.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'spectra_link_guard.web.analises'`.

- [ ] **Step 3: `bd.registrar_esquema`**

Em `src/spectra_link_guard/auth/bd.py`, logo depois do fechamento de `_ESQUEMA = """…"""`, inserir:

```python

#: Esquemas criados na primeira conexão do processo. Outros módulos (ex.:
#: web/analises.py) acrescentam suas tabelas por registrar_esquema().
_ESQUEMAS: list[str] = [_ESQUEMA]
```

Dentro de `conexao()`, trocar

```python
    if not _PRONTO:
        con.executescript(_ESQUEMA)
        con.commit()
        _PRONTO = True
```

por

```python
    if not _PRONTO:
        for esquema in _ESQUEMAS:
            con.executescript(esquema)
        con.commit()
        _PRONTO = True
```

E logo depois da função `preparar()`, acrescentar:

```python


def registrar_esquema(sql: str) -> None:
    """Acrescenta tabelas de outro módulo ao esquema criado na primeira conexão."""
    global _PRONTO
    if sql not in _ESQUEMAS:
        _ESQUEMAS.append(sql)
        _PRONTO = False
```

- [ ] **Step 4: `rotulos_sinais.py`**

Criar `src/spectra_link_guard/web/rotulos_sinais.py`:

```python
"""Nome legível de cada código de achado, para os gráficos da Visão geral.

O título do próprio achado não serve: varia com a análise ("Domínio quase
igual ao de 'itau'"). Aqui é um nome fixo por código. Um teste confere que
todo código de achado do analisador tem nome.
"""

from __future__ import annotations

ROTULOS_SINAIS: dict[str, str] = {
    # sintaxe
    "url_invalida": "URL inválida",
    "esquema_perigoso": "Esquema perigoso",
    "esquema_ausente": "Sem protocolo",
    "userinfo_no_host": "'@' escondendo o destino",
    "host_ip_literal": "IP no lugar do domínio",
    "porta_incomum": "Porta incomum",
    "encurtador": "Link encurtado",
    "url_embutida": "URL escondida nos parâmetros",
    "subdominios_excessivos": "Subdomínios em excesso",
    "tld_de_risco": "Extensão de domínio de risco",
    "hifens_em_excesso": "Hífens em excesso",
    "url_muito_longa": "URL muito longa",
    "alfabetos_misturados": "Alfabetos misturados",
    "dominio_punycode": "Domínio em punycode",
    "dominio_sosia": "Domínio sósia de marca",
    "typosquatting": "Typosquatting",
    "marca_em_subdominio": "Marca em domínio de terceiro",
    "palavras_isca": "Palavras típicas de golpe",
    "download_executavel": "Download de executável",
    # TLS
    "sem_https": "Sem HTTPS",
    "tls_indisponivel": "Sem conexão segura",
    "certificado_invalido": "Certificado não confiável",
    "certificado_autoassinado": "Certificado autoassinado",
    "certificado_host_divergente": "Certificado de outro endereço",
    "certificado_expirado": "Certificado vencido",
    "certificado_perto_do_vencimento": "Certificado perto de vencer",
    "certificado_recem_emitido": "Certificado recém-emitido",
    "tls_obsoleto": "TLS obsoleto",
    # reputação
    "listado_como_malicioso": "Listado como malicioso",
    "reputacao_indisponivel": "Listas de ameaça indisponíveis",
    # registro e DNS
    "dominio_recem_registrado": "Domínio registrado há poucos dias",
    "dominio_novo": "Domínio novo",
    "dominio_estabelecido": "Domínio estabelecido",
    "dominio_suspenso": "Domínio suspenso",
    "dominio_expirado": "Domínio expirado",
    "sem_spf": "Sem SPF",
    "sem_dmarc": "Sem DMARC",
    "dmarc_permissivo": "DMARC permissivo",
    "sem_caa": "Sem CAA",
}


def rotulo_do_sinal(codigo: str) -> str:
    """Nome legível; um código sem nome aparece como o próprio código."""
    return ROTULOS_SINAIS.get(codigo, codigo)
```

- [ ] **Step 5: `analises.py`**

Criar `src/spectra_link_guard/web/analises.py`:

```python
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
```

- [ ] **Step 6: Rodar os testes do módulo**

Run: `python -m pytest tests/test_analises.py -q`
Expected: PASS (15 testes).

- [ ] **Step 7: Reescrever `tests/test_web.py` para o contrato com login**

Substituir o conteúdo de `tests/test_web.py` por:

```python
"""Testes da camada web.

Todos rodam em modo offline (``offline: true`` no corpo), então a suíte
continua sem abrir conexão de rede nem consumir cota de API de terceiro.
O banco é isolado por teste (conftest.py).
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi", reason="extra 'web' não instalado")
from fastapi.testclient import TestClient  # noqa: E402

from spectra_link_guard.web.app import app, limitador  # noqa: E402


@pytest.fixture
def cliente() -> TestClient:
    # Estado do processo é compartilhado entre testes: zeramos antes de cada um.
    limitador._por_ip.clear()
    return TestClient(app)


def entrar(cliente: TestClient, email: str = "ana@exemplo.com.br") -> None:
    """Cria a conta e deixa a sessão no cookie deste cliente."""
    resp = cliente.post(
        "/api/auth/cadastrar",
        json={"nome": "Pessoa de Teste", "email": email, "senha": "senha-forte-123"},
    )
    assert resp.status_code == 201


def analisar(cliente: TestClient, url: str):
    return cliente.post("/api/analisar", json={"url": url, "offline": True})


# --------------------------------------------------------------------------- #
# Páginas
# --------------------------------------------------------------------------- #


def test_raiz_redireciona_para_a_entrada(cliente):
    """A raiz não serve mais painel próprio — o produto é um só."""
    resp = cliente.get("/", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"] == "/inicio"


def test_v2_antigo_aponta_para_o_painel(cliente):
    resp = cliente.get("/v2", follow_redirects=False)
    assert resp.status_code == 308
    assert resp.headers["location"] == "/painel"


@pytest.mark.parametrize("rota", ["/painel", "/painel/historico", "/painel/aprender"])
def test_telas_do_painel_exigem_sessao(cliente, rota):
    resp = cliente.get(rota, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/inicio?erro=entre_primeiro"


@pytest.mark.parametrize("rota", ["/privacidade", "/termos"])
def test_paginas_legais_sao_publicas(cliente, rota):
    resp = cliente.get(rota)
    assert resp.status_code == 200
    assert "Spectra" in resp.text


def test_tela_de_entrada_responde(cliente):
    resp = cliente.get("/inicio")
    assert resp.status_code == 200
    assert "inicio.js?v=" in resp.text  # ativo versionado contra cache
    for marco in ("Cadastrar-se", "Esqueci minha senha", "Aceito os", "Assistente Spectra"):
        assert marco in resp.text


# --------------------------------------------------------------------------- #
# Análise
# --------------------------------------------------------------------------- #


def test_analise_devolve_relatorio_completo(cliente):
    resp = analisar(cliente, "https://itau.seguranca-cliente.top/atualizar/senha")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["nivel"] in ("alto", "critico")
    assert corpo["dominio_registravel"] == "seguranca-cliente.top"
    assert any(a["codigo"] == "marca_em_subdominio" for a in corpo["achados"])


def test_modo_offline_nao_traz_tls_nem_reputacao(cliente):
    corpo = analisar(cliente, "https://exemplo.com").json()
    assert corpo["tls"] is None
    assert corpo["reputacao"] == []


def test_analise_traz_checklist_heuristico(cliente):
    corpo = analisar(cliente, "https://exemplo.com").json()
    assert len(corpo["checklist"]) == 11
    assert all({"codigo", "rotulo", "passou", "motivo"} == set(c) for c in corpo["checklist"])


def test_url_vazia_e_rejeitada(cliente):
    assert cliente.post("/api/analisar", json={"url": ""}).status_code == 422


def test_url_absurdamente_longa_e_rejeitada(cliente):
    resp = cliente.post("/api/analisar", json={"url": "https://x.com/" + "a" * 4000})
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# Histórico por usuário
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "metodo,rota",
    [
        ("get", "/api/painel"),
        ("get", "/api/painel/historico"),
        ("get", "/api/painel/estatisticas"),
        ("delete", "/api/painel"),
        ("delete", "/api/painel/abcdef123456"),
    ],
)
def test_rotas_do_historico_exigem_sessao(cliente, metodo, rota):
    resp = getattr(cliente, metodo)(rota)
    assert resp.status_code == 401
    assert "erro" in resp.json()


def test_analise_sem_sessao_nao_entra_no_historico(cliente):
    analisar(cliente, "https://exemplo.com")
    entrar(cliente)
    assert cliente.get("/api/painel/historico").json() == {"itens": []}


def test_painel_acumula_historico(cliente):
    entrar(cliente)
    analisar(cliente, "https://itau.seguranca-cliente.top/senha/login")
    analisar(cliente, "https://exemplo.com")
    painel = cliente.get("/api/painel").json()
    assert painel["total"] == 2
    assert painel["perigosos"] >= 1


def test_historico_nao_guarda_a_url_completa(cliente):
    """A query pode carregar token de sessão — só host e nota são retidos."""
    entrar(cliente)
    analisar(cliente, "https://exemplo.com/pagina?token=segredo-do-usuario")
    recente = cliente.get("/api/painel").json()["recentes"][0]
    assert recente["host"] == "exemplo.com"
    assert "segredo-do-usuario" not in str(recente)
    assert set(recente) == {"id", "host", "dominio", "risco", "nivel", "quando"}


def test_api_historico_completo_tem_mesmo_formato_do_resumo(cliente):
    entrar(cliente)
    analisar(cliente, "https://exemplo.com/pagina?token=segredo-do-usuario")
    itens = cliente.get("/api/painel/historico").json()["itens"]
    assert len(itens) == 1
    assert set(itens[0]) == {"id", "host", "dominio", "risco", "nivel", "quando"}
    assert "segredo-do-usuario" not in str(itens[0])


def test_excluir_entrada_do_historico(cliente):
    entrar(cliente)
    analisar(cliente, "https://exemplo.com")
    analisar(cliente, "https://outro-exemplo.com")
    recentes = cliente.get("/api/painel").json()["recentes"]
    assert len(recentes) == 2

    alvo = recentes[0]["id"]
    assert cliente.delete(f"/api/painel/{alvo}").status_code == 204

    restantes = cliente.get("/api/painel").json()
    assert restantes["total"] == 1
    assert alvo not in [r["id"] for r in restantes["recentes"]]


def test_excluir_id_inexistente_devolve_404(cliente):
    entrar(cliente)
    resp = cliente.delete("/api/painel/abcdef123456")
    assert resp.status_code == 404
    assert "erro" in resp.json()


def test_excluir_id_malformado_e_rejeitado(cliente):
    # Só hexadecimal: fecha a porta para path traversal e lixo na rota.
    entrar(cliente)
    assert cliente.delete("/api/painel/..%2Fetc").status_code in (404, 422)
    assert cliente.delete("/api/painel/ZZZZ").status_code == 422


def test_cada_analise_recebe_id_proprio(cliente):
    entrar(cliente)
    analisar(cliente, "https://exemplo.com")
    analisar(cliente, "https://exemplo.com")
    ids = [r["id"] for r in cliente.get("/api/painel").json()["recentes"]]
    assert len(set(ids)) == 2


def test_um_usuario_nao_ve_nem_apaga_o_historico_do_outro(cliente):
    entrar(cliente, "ana@exemplo.com.br")
    analisar(cliente, "https://exemplo.com")
    item_da_ana = cliente.get("/api/painel/historico").json()["itens"][0]["id"]

    bruno = TestClient(app)
    entrar(bruno, "bruno@exemplo.com.br")
    assert bruno.get("/api/painel/historico").json() == {"itens": []}
    assert bruno.get("/api/painel/estatisticas").json()["total"] == 0
    assert bruno.delete(f"/api/painel/{item_da_ana}").status_code == 404

    itens_da_ana = cliente.get("/api/painel/historico").json()["itens"]
    assert [i["id"] for i in itens_da_ana] == [item_da_ana]


def test_apagar_todo_o_historico(cliente):
    entrar(cliente)
    analisar(cliente, "https://exemplo.com")
    analisar(cliente, "https://outro-exemplo.com")
    assert cliente.delete("/api/painel").status_code == 204
    assert cliente.get("/api/painel/historico").json() == {"itens": []}


def test_estatisticas_tem_o_formato_do_dashboard(cliente):
    entrar(cliente)
    analisar(cliente, "https://itau.seguranca-cliente.top/atualizar/senha")
    analisar(cliente, "https://exemplo.com")
    estat = cliente.get("/api/painel/estatisticas").json()
    assert set(estat) == {
        "total", "perigosos", "risco_medio", "pct_seguras",
        "por_nivel", "por_dia", "sinais_frequentes",
    }
    assert estat["total"] == 2
    assert len(estat["por_dia"]) == 30
    assert estat["por_dia"][-1]["total"] == 2
    assert any(s["codigo"] == "marca_em_subdominio" for s in estat["sinais_frequentes"])


# --------------------------------------------------------------------------- #
# Saúde e limite
# --------------------------------------------------------------------------- #


def test_saude_nao_vaza_chaves(cliente):
    corpo = cliente.get("/api/saude").json()
    assert set(corpo["provedores"]) == {"google_safe_browsing", "virustotal", "phishtank"}
    # Só booleanos: nunca o valor da chave.
    assert all(isinstance(v, bool) for v in corpo["provedores"].values())


def test_limite_de_requisicoes(cliente):
    limitador._por_ip.clear()
    for _ in range(limitador.maximo):
        assert analisar(cliente, "https://exemplo.com").status_code == 200
    excedente = analisar(cliente, "https://exemplo.com")
    assert excedente.status_code == 429
    assert "erro" in excedente.json()
```

- [ ] **Step 8: Rodar e ver falhar**

Run: `python -m pytest tests/test_web.py -q`
Expected: FAIL — `test_rotas_do_historico_exigem_sessao` (hoje responde 200/404), `test_um_usuario_nao_ve…` (vê o histórico global), `test_apagar_todo_o_historico` e `test_estatisticas…` (rotas não existem).

- [ ] **Step 9: API por usuário em `app.py`**

Em `src/spectra_link_guard/web/app.py`:

(a) Imports: trocar `import time` / `import uuid` por

```python
import asyncio
import time
```

e acrescentar, depois de `from ..models import NivelRisco`:

```python
from . import analises
```

(remover `from ..models import NivelRisco` se ficar sem uso).

(b) Apagar a classe `_Historico` inteira (do `@dataclass` acima de `class _Historico:` até o fim do método `todos`) e a linha `historico = _Historico()`.

(c) Logo depois de `guard = LinkGuard()`, inserir:

```python


def _usuario_ou_401(request: Request) -> dict[str, Any]:
    """Dono da sessão, ou 401: o histórico é sempre de alguém."""
    usuario = usuario_atual(request.cookies.get("spectra_sessao"))
    if usuario is None:
        raise HTTPException(status_code=401, detail="Entre na sua conta para ver o histórico.")
    return usuario
```

(d) Em `analisar`, trocar `historico.registrar(relatorio)` por:

```python
    # Sem sessão (CLI, testes, integração) a análise funciona, mas não é salva.
    usuario = usuario_atual(request.cookies.get("spectra_sessao"))
    if usuario is not None:
        await asyncio.to_thread(analises.registrar, usuario["id"], relatorio)
```

(e) Trocar as rotas `painel`, `historico_completo` e `remover_do_historico` por:

```python
@app.get("/api/painel", summary="Indicadores do usuário")
async def painel(request: Request) -> dict[str, Any]:
    usuario = _usuario_ou_401(request)
    return await asyncio.to_thread(analises.resumo, usuario["id"])


@app.get("/api/painel/historico", summary="Histórico completo do usuário")
async def historico_completo(request: Request) -> dict[str, Any]:
    """Todas as análises guardadas (até 500), para busca e filtro na tela de Histórico."""
    usuario = _usuario_ou_401(request)
    return {"itens": await asyncio.to_thread(analises.listar, usuario["id"])}


@app.get("/api/painel/estatisticas", summary="Números da Visão geral")
async def estatisticas(request: Request) -> dict[str, Any]:
    usuario = _usuario_ou_401(request)
    return await asyncio.to_thread(analises.estatisticas, usuario["id"])


@app.delete("/api/painel", status_code=204, summary="Apaga todo o histórico do usuário")
async def apagar_historico(request: Request) -> Response:
    usuario = _usuario_ou_401(request)
    await asyncio.to_thread(analises.remover_todas, usuario["id"])
    return Response(status_code=204)


@app.delete(
    "/api/painel/{item_id}",
    status_code=204,
    summary="Remove uma análise do histórico do usuário",
)
async def remover_do_historico(
    request: Request,
    item_id: str = ParamPath(min_length=1, max_length=32, pattern=r"^[0-9a-f]+$"),
) -> Response:
    usuario = _usuario_ou_401(request)
    # 404 também quando o item é de outra pessoa: não revela que ele existe.
    if not await asyncio.to_thread(analises.remover, usuario["id"], item_id):
        raise HTTPException(status_code=404, detail="Entrada não encontrada.")
    return Response(status_code=204)
```

(f) Na docstring da rota `/painel/historico`, trocar "Histórico das análises feitas nesta sessão." por "Histórico das análises do usuário.".

- [ ] **Step 10: `historico.js` trata 401**

Em `carregar()` de `src/spectra_link_guard/web/static/historico.js`, logo depois de `const resp = await fetch("/api/painel/historico");`, inserir:

```js
    if (resp.status === 401) {
      window.location.href = "/inicio?erro=entre_primeiro";
      return;
    }
```

- [ ] **Step 11: Rodar tudo**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 12: Conferir no navegador**

Com duas contas (janela normal e anônima): analisar um link com a conta A em `/painel`; abrir `/painel/historico` com a conta B — lista vazia. Reiniciar o servidor: o histórico de A continua lá.

- [ ] **Step 13: Commit**

```bash
git add src/spectra_link_guard/auth/bd.py src/spectra_link_guard/web/analises.py \
  src/spectra_link_guard/web/rotulos_sinais.py src/spectra_link_guard/web/app.py \
  src/spectra_link_guard/web/static/historico.js tests/test_analises.py tests/test_web.py
git commit -m "$(cat <<'EOF'
Histórico de análises por usuário no SQLite

O histórico ficava num objeto global em memória: todo usuário via e apagava
as análises dos outros, e tudo sumia ao reiniciar. Agora vive na tabela
analises, presa ao usuário (até 500 por conta, sem a URL completa), e as
rotas do painel exigem sessão. Novas rotas: estatísticas agregadas para o
dashboard e apagar todo o histórico.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Partes compartilhadas (menu, rodapé, acessibilidade)

**Files:**
- Create: `src/spectra_link_guard/web/parciais/menu.html`, `rodape.html`, `acessibilidade.html`
- Create: `src/spectra_link_guard/web/static/menu.js`
- Modify: `src/spectra_link_guard/web/app.py` (`_pagina`, `_ATIVOS_PAINEL`, rotas)
- Modify: `laudo.html`, `inicio.html`, `privacidade.html`, `termos.html`; reescrever `historico.html` e `aprender.html`
- Modify: `laudo.js`, `historico.js` (sai o bloco de conta/sair)
- Modify: `laudo.css` (item ativo, conta, fontes, atalhos "Nesta análise")
- Modify: `pyproject.toml`
- Modify: `tests/test_web.py`

**Interfaces:**
- Consumes: `_ATIVOS_BASE` (Task 1).
- Produces:
  - `_pagina(arquivo: str, *ativos: str, menu: str | None = None) -> HTMLResponse` — troca `<!--PARCIAL:nome-->` por `web/parciais/nome.html` e acrescenta `aria-current="page"` a todo `data-menu="<menu>"`.
  - `_ATIVOS_PAINEL = _ATIVOS_BASE + ("laudo.css", "menu.js")`.
  - Valores de `data-menu`: `verificar`, `historico`, `aprender` (Task 5 acrescenta `visao-geral`).
  - Marcação da conta por atributos (vários lugares podem existir): `[data-conta]`, `[data-conta-inicial]`, `[data-conta-nome]`, `[data-sair]`.
  - Atalhos do laudo: `<nav class="subnav-analise" id="subnav-analise">` (mesmo id de antes).

- [ ] **Step 1: Escrever os testes**

Acrescentar ao fim de `tests/test_web.py`:

```python


# --------------------------------------------------------------------------- #
# Partes compartilhadas
# --------------------------------------------------------------------------- #

ITENS_DO_MENU = ["verificar", "historico", "aprender"]
TELAS_DO_PAINEL = [("/painel", "verificar"), ("/painel/historico", "historico"),
                   ("/painel/aprender", "aprender")]


def test_telas_do_painel_trazem_parciais_e_marcam_o_item_ativo(cliente):
    entrar(cliente)
    for rota, ativo in TELAS_DO_PAINEL:
        html = cliente.get(rota).text
        assert "<!--PARCIAL" not in html, rota
        assert 'class="trilho"' in html, rota
        assert 'class="rodape-spectra"' in html, rota
        assert 'id="a11y-painel"' in html, rota
        assert f'data-menu="{ativo}" aria-current="page"' in html, rota
        for outro in ITENS_DO_MENU:
            if outro != ativo:
                assert f'data-menu="{outro}" aria-current' not in html, (rota, outro)


@pytest.mark.parametrize("rota", ["/inicio", "/privacidade", "/termos"])
def test_paginas_publicas_trazem_rodape_e_acessibilidade_sem_menu(cliente, rota):
    html = cliente.get(rota).text
    assert "<!--PARCIAL" not in html
    assert 'class="rodape-spectra"' in html
    assert 'id="a11y-painel"' in html
    assert 'class="trilho"' not in html


def test_rodape_e_acessibilidade_moram_so_nos_parciais():
    from spectra_link_guard.web.app import ESTATICOS

    for pagina in ESTATICOS.glob("*.html"):
        html = pagina.read_text(encoding="utf-8")
        assert 'class="rodape-spectra"' not in html, pagina.name
        assert 'id="a11y-painel"' not in html, pagina.name
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_web.py -q -k "parciais or rodape or menu"`
Expected: FAIL — `data-menu` não existe e o rodapé ainda está copiado nas páginas.

- [ ] **Step 3: Criar os parciais**

Criar `src/spectra_link_guard/web/parciais/rodape.html`:

```html
<footer class="rodape-spectra">
  <div class="rodape-fundo" aria-hidden="true"></div>
  <div class="rodape-conteudo">
    <div>
      <div class="rodape-marca" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        SPECTRA
      </div>
      <p class="rodape-tagline">Análise passiva de risco de links, para proteção ao consumidor.</p>
    </div>
    <nav aria-label="Links legais">
      <p class="rodape-titulo-coluna">Legal</p>
      <ul class="rodape-links">
        <li><a href="/privacidade">Política de Privacidade</a></li>
        <li><a href="/termos">Termos de Uso</a></li>
      </ul>
    </nav>
    <div>
      <p class="rodape-titulo-coluna">Contato</p>
      <ul class="rodape-contato">
        <li><a href="https://wa.me/5511999999999" target="_blank" rel="noopener"><i data-lucide="message-circle" aria-hidden="true"></i>(11) 99999-9999</a></li>
        <li><a href="https://instagram.com/spectra.seguranca" target="_blank" rel="noopener"><i data-lucide="instagram" aria-hidden="true"></i>@spectra.seguranca</a></li>
        <li><a href="mailto:contato@spectra.app"><i data-lucide="mail" aria-hidden="true"></i>contato@spectra.app</a></li>
      </ul>
    </div>
  </div>
  <div class="rodape-base">
    <span>© <span data-ano-atual>2026</span> Spectra. Todos os direitos reservados.</span>
    <span>Varredura passiva · proteção ao consumidor</span>
  </div>
</footer>
```

Criar `src/spectra_link_guard/web/parciais/acessibilidade.html`:

```html
<div class="a11y-caixa">
  <div id="a11y-painel" class="a11y-painel" hidden role="region" aria-label="Acessibilidade">
    <p class="a11y-titulo">Acessibilidade</p>
    <div class="a11y-linha">
      <span class="a11y-rotulo">Tema</span>
      <button type="button" data-a11y-tema>
        <i data-lucide="sun-moon" aria-hidden="true"></i><span data-a11y-tema-rotulo>Tema</span>
      </button>
    </div>
    <div class="a11y-linha">
      <span class="a11y-rotulo">Fonte</span>
      <div class="a11y-grupo">
        <button type="button" data-a11y-fonte-menos aria-label="Diminuir fonte">A−</button>
        <button type="button" data-a11y-fonte-reset aria-label="Fonte padrão"><span data-a11y-fonte-valor>100%</span></button>
        <button type="button" data-a11y-fonte-mais aria-label="Aumentar fonte">A+</button>
      </div>
    </div>
    <div class="a11y-linha">
      <span class="a11y-rotulo">Alto contraste</span>
      <button type="button" data-a11y-contraste aria-pressed="false">
        <i data-lucide="contrast" aria-hidden="true"></i>Ativar
      </button>
    </div>
    <div class="a11y-linha">
      <span class="a11y-rotulo">Movimento</span>
      <button type="button" data-interruptor-movimento aria-pressed="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M3 12h4l3-8 4 16 3-8h4"/></svg>
        <span data-rotulo-movimento>Movimento ligado</span>
      </button>
    </div>
  </div>
  <button type="button" id="a11y-abrir" class="a11y-botao" aria-expanded="false" aria-controls="a11y-painel" aria-label="Abrir opções de acessibilidade">
    <i data-lucide="accessibility" aria-hidden="true"></i>
  </button>
</div>
```

(É o mesmo bloco que hoje está copiado nas páginas; privacidade e termos ganham a linha "Movimento", que antes não tinham.)

Criar `src/spectra_link_guard/web/parciais/menu.html`:

```html
<aside class="trilho">
  <a class="chancela" href="/inicio">
    <span class="chancela-marca" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
    </span>
    <span class="chancela-texto">
      <span class="chancela-nome">SPECTRA</span>
      <span class="chancela-tipo">laudo de link</span>
    </span>
  </a>

  <nav class="menu" aria-label="Navegação principal">
    <a class="menu-item" href="/painel" data-menu="verificar">
      <i data-lucide="search-check" class="menu-icone" aria-hidden="true"></i><span class="menu-rotulo">Verificar</span>
    </a>
    <a class="menu-item" href="/painel/historico" data-menu="historico">
      <i data-lucide="history" class="menu-icone" aria-hidden="true"></i><span class="menu-rotulo">Histórico</span>
    </a>
    <a class="menu-item" href="/painel/aprender" data-menu="aprender">
      <i data-lucide="book-open" class="menu-icone" aria-hidden="true"></i><span class="menu-rotulo">Aprender</span>
    </a>
  </nav>

  <div class="trilho-base">
    <div class="conta" data-conta hidden>
      <span class="conta-inicial" data-conta-inicial aria-hidden="true"></span>
      <span class="conta-texto"><span class="conta-nome" data-conta-nome></span></span>
      <button type="button" class="conta-sair" data-sair>
        <i data-lucide="log-out" aria-hidden="true"></i><span class="conta-sair-rotulo">Sair</span>
      </button>
    </div>
  </div>
</aside>
```

- [ ] **Step 4: `menu.js`**

Criar `src/spectra_link_guard/web/static/menu.js`:

```js
/* Menu compartilhado do painel (web/parciais/menu.html): bloco da conta e
 * botões de sair. A conta pode aparecer em mais de um lugar (menu lateral,
 * barra do celular, gaveta), por isso os alvos são atributos data-*, não ids.
 * Todo texto vindo do servidor entra por textContent.
 */

(function () {
  function preencherConta(usuario) {
    const inicial = usuario.nome.trim().charAt(0).toUpperCase();
    document.querySelectorAll("[data-conta-inicial]").forEach((el) => { el.textContent = inicial; });
    document.querySelectorAll("[data-conta-nome]").forEach((el) => { el.textContent = usuario.nome; });
    document.querySelectorAll("[data-conta]").forEach((el) => { el.hidden = false; });
  }

  async function sair() {
    try {
      await fetch("/api/auth/sair", { method: "POST" });
    } finally {
      window.location.href = "/inicio";
    }
  }

  fetch("/api/auth/eu")
    .then((resposta) => resposta.json())
    .then(({ usuario }) => { if (usuario) preencherConta(usuario); })
    .catch(() => {});

  document.querySelectorAll("[data-sair]").forEach((botao) => botao.addEventListener("click", sair));
})();
```

- [ ] **Step 5: `_pagina` com parciais**

Em `src/spectra_link_guard/web/app.py`:

(a) Imports: acrescentar `import re`.

(b) Depois de `_ATIVOS_BASE = (…)`, acrescentar:

```python

#: Ativos das telas com menu lateral (painel).
_ATIVOS_PAINEL = _ATIVOS_BASE + ("laudo.css", "menu.js")

#: Partes de HTML compartilhadas, encaixadas por _pagina() no lugar de
#: <!--PARCIAL:nome-->. Ficam fora de static/: não são servidas sozinhas.
PARCIAIS = Path(__file__).parent / "parciais"
_MARCADOR_PARCIAL = re.compile(r"<!--PARCIAL:([a-z-]+)-->")
```

(c) Trocar a função `_pagina` por:

```python
def _pagina(arquivo: str, *ativos: str, menu: str | None = None) -> HTMLResponse:
    """Serve uma página: encaixa os parciais, marca o item ativo do menu e
    injeta ?v=<mtime> nos ativos que ela referencia (cache-busting)."""
    html = (ESTATICOS / arquivo).read_text(encoding="utf-8")
    html = _MARCADOR_PARCIAL.sub(
        lambda marcador: (PARCIAIS / f"{marcador.group(1)}.html").read_text(encoding="utf-8"),
        html,
    )
    if menu is not None:
        html = html.replace(f'data-menu="{menu}"', f'data-menu="{menu}" aria-current="page"')
    for ativo in ativos:
        html = html.replace(f"/static/{ativo}", f"/static/{ativo}?v={_carimbo(ativo)}")
    return HTMLResponse(html)
```

(d) Rotas do painel:

```python
# /painel
    return _pagina(
        "laudo.html", *_ATIVOS_PAINEL,
        "glossario.js", "caminhos.js", "melhorias.js", "laudo.js", menu="verificar",
    )
# /painel/historico
    return _pagina("historico.html", *_ATIVOS_PAINEL, "historico.js", menu="historico")
# /painel/aprender
    return _pagina("aprender.html", *_ATIVOS_PAINEL, "glossario.js", menu="aprender")
```

- [ ] **Step 6: `pyproject.toml` empacota os parciais**

Trocar `"spectra_link_guard.web" = ["static/*"]` por:

```toml
"spectra_link_guard.web" = ["static/*", "parciais/*"]
```

- [ ] **Step 7: `laudo.html` usa os parciais**

Em `src/spectra_link_guard/web/static/laudo.html`:

(a) No `<head>`, depois do `<link rel="icon" …>`, inserir (scripts que precisam rodar antes da primeira pintura):

```html
<script src="/static/movimento.js"></script>
<script src="/static/acessibilidade.js"></script>
```

(b) Trocar o bloco `<!-- ═══ trilho -->` + `<aside class="trilho">…</aside>` inteiro por:

```html
<!--PARCIAL:menu-->
```

(c) Logo depois do `</header>` da `<header class="barra">`, inserir:

```html

<div class="fontes-linha">
  <p class="legenda">Fontes consultadas</p>
  <ul class="fontes" id="fontes">
    <li class="fonte" data-fonte="sintaxe"><span class="led" aria-hidden="true"></span>Estrutura da URL</li>
    <li class="fonte" data-fonte="tls"><span class="led" aria-hidden="true"></span>Certificado TLS</li>
    <li class="fonte" data-fonte="rede"><span class="led" aria-hidden="true"></span>RDAP / DNS</li>
  </ul>
</div>

<nav class="subnav-analise" id="subnav-analise" aria-label="Nesta análise" hidden>
  <span class="legenda subnav-legenda">Nesta análise</span>
  <a class="subnav-item" href="#q-veredito">Veredito</a>
  <a class="subnav-item" href="#q-checklist">Pontuação</a>
  <a class="subnav-item" href="#q-cadeia">Destino real</a>
  <a class="subnav-item" href="#q-evidencias">Evidências</a>
  <a class="subnav-item" href="#q-sinais">Sinais</a>
</nav>
```

(d) Trocar o bloco `<footer class="rodape-spectra">…</footer>` por `<!--PARCIAL:rodape-->`.

(e) Trocar o comentário `<!-- ═══ acessibilidade -->` + `<div class="a11y-caixa">…</div>` por `<!--PARCIAL:acessibilidade-->`.

(f) No fim do `<body>`, trocar

```html
<script src="/static/movimento.js"></script>
<script src="/static/acessibilidade.js"></script>
<script src="/static/glossario.js"></script>
```

por

```html
<script src="/static/menu.js"></script>
<script src="/static/glossario.js"></script>
```

- [ ] **Step 8: `laudo.js` sem o bloco da conta**

Apagar de `src/spectra_link_guard/web/static/laudo.js` o trecho `/* ═══ conta e sessão */` inteiro: o `fetch("/api/auth/eu")…` e o `$("sair").addEventListener(…)`.

- [ ] **Step 9: Reescrever `historico.html`**

Substituir `src/spectra_link_guard/web/static/historico.html` por:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spectra</title>
<meta name="description" content="Histórico dos links já verificados.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&family=Inter:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/tokens.css">
<link rel="stylesheet" href="/static/laudo.css">
<link rel="stylesheet" href="/static/rodape.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛡️</text></svg>">
<script src="/static/movimento.js"></script>
<script src="/static/acessibilidade.js"></script>
<script src="https://unpkg.com/lucide@0.462.0/dist/umd/lucide.js" defer
        integrity="sha384-WBRt9V/J/erVtkEuP91HUFRv9MvHzFiFOp4/zTDp4xkcMG7aOeIv2asTV4yxFLWa" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js" defer
        integrity="sha384-NrKB+u6Ts6AtkIhwPixiKTzgSKNblyhlk0Sohlgar9UHUBzai/sgnNNWWd291xqt" crossorigin="anonymous"></script>
</head>
<body data-estado="seguro">

<div class="app">

<!--PARCIAL:menu-->

<div class="corpo">

<header class="barra hist-barra">
  <h1 class="hist-titulo">Histórico</h1>
  <div class="hist-controles">
    <label class="oculto" for="hist-busca">Buscar por host ou domínio</label>
    <input id="hist-busca" type="search" placeholder="buscar por host ou domínio…" class="hist-busca">
    <label class="oculto" for="hist-filtro">Filtrar por veredito</label>
    <select id="hist-filtro" class="hist-filtro">
      <option value="">todos os vereditos</option>
      <option value="seguro">seguro</option>
      <option value="baixo">baixo</option>
      <option value="atencao">atenção</option>
      <option value="alto">alto</option>
      <option value="critico">crítico</option>
    </select>
  </div>
</header>

<main class="grade">

  <section class="quadro q-hist-resumo">
    <header class="quadro-topo">
      <h2 class="quadro-titulo">Resumo</h2>
      <span class="quadro-marca mono" id="hist-total">0 análises</span>
    </header>
    <div class="quadro-corpo hist-resumo-corpo">
      <div class="hist-grafico">
        <canvas id="hist-grafico" width="160" height="160" role="img" aria-label="Gráfico com a distribuição de vereditos no histórico"></canvas>
      </div>
      <ul class="hist-legenda" id="hist-legenda"></ul>
      <p class="hist-nota">Guardamos só host, domínio, nota e horário, nunca a URL completa (ela pode ter dados pessoais na query).</p>
    </div>
  </section>

  <section class="quadro q-hist-lista">
    <header class="quadro-topo">
      <h2 class="quadro-titulo">Análises</h2>
      <span class="quadro-marca mono" id="hist-contagem"></span>
    </header>
    <div class="quadro-corpo">
      <table class="tabela-hist">
        <caption class="oculto">Links já verificados: data, host, domínio, veredito e nota</caption>
        <thead>
          <tr>
            <th scope="col">Quando</th>
            <th scope="col">Host</th>
            <th scope="col">Domínio</th>
            <th scope="col">Veredito</th>
            <th scope="col">Nota</th>
            <th scope="col"><span class="oculto">Ações</span></th>
          </tr>
        </thead>
        <tbody id="hist-corpo"></tbody>
      </table>
      <p class="hist-vazio" id="hist-vazio" hidden>Nenhuma análise encontrada.</p>
    </div>
  </section>

</main>

<!--PARCIAL:rodape-->

</div>
</div>

<!--PARCIAL:acessibilidade-->

<script src="/static/menu.js" defer></script>
<script src="/static/historico.js" defer></script>
</body>
</html>
```

E em `historico.js`, apagar o bloco final `fetch("/api/auth/eu")…` e o `$("sair").addEventListener(…)`.

- [ ] **Step 10: `aprender.html` usa os parciais**

Em `src/spectra_link_guard/web/static/aprender.html` (o `<main class="grade aprender-grade">…</main>` com os cinco artigos não muda):

(a) No `<head>`, depois do `<link rel="icon" …>`, inserir:

```html
<script src="/static/movimento.js"></script>
<script src="/static/acessibilidade.js"></script>
```

(b) Trocar o `<aside class="trilho">…</aside>` inteiro por `<!--PARCIAL:menu-->`.

(c) Trocar o `<footer class="rodape-spectra">…</footer>` por `<!--PARCIAL:rodape-->` e o `<div class="a11y-caixa">…</div>` por `<!--PARCIAL:acessibilidade-->`.

(d) Trocar tudo do `<script src="/static/movimento.js"></script>` do fim do `<body>` até o `</script>` do script inline (que hoje preenche o glossário **e** cuida da conta/sair) por:

```html
<script src="/static/menu.js" defer></script>
<script src="/static/glossario.js"></script>
<script>
  // Preenche o glossário completo nesta tela (nos outros lugares, só os
  // botões "?" pontuais usam o mesmo GLOSSARIO de glossario.js).
  (function () {
    const lista = document.getElementById("glossario-lista");
    for (const termo of Object.values(window.GLOSSARIO || {})) {
      const dt = document.createElement("dt");
      dt.textContent = termo.titulo;
      const dd = document.createElement("dd");
      dd.textContent = termo.texto;
      lista.append(dt, dd);
    }
  })();
</script>
```

- [ ] **Step 11: Home e páginas legais usam os parciais**

`inicio.html`:
- trocar o bloco `<footer class="rodape-spectra">…</footer>` por `<!--PARCIAL:rodape-->`;
- trocar o comentário `<!-- ═══ acessibilidade -->` + `<div class="a11y-caixa">…</div>` por `<!--PARCIAL:acessibilidade-->`;
- mover a linha `<script src="/static/acessibilidade.js"></script>` do fim do `<body>` para o `<head>`, logo depois de `<script src="/static/movimento.js"></script>`.

`privacidade.html` e `termos.html`:
- trocar o `<footer class="rodape-spectra">…</footer>` por `<!--PARCIAL:rodape-->`;
- trocar o `<div class="a11y-caixa">…</div>` por `<!--PARCIAL:acessibilidade-->`;
- mover `<script src="/static/movimento.js"></script>` e `<script src="/static/acessibilidade.js"></script>` do fim do `<body>` para o fim do `<head>`.

- [ ] **Step 12: CSS do menu, conta, fontes e atalhos**

Em `src/spectra_link_guard/web/static/laudo.css`:

(a) Trocar

```css
.menu-item.ativo { background: var(--base-3); border-color: var(--linha-forte); color: var(--texto); }
.menu-marca { width: 5px; height: 5px; flex: none; background: var(--texto-3); }
.menu-item.ativo .menu-marca { background: var(--primaria); }
```

por

```css
.menu-item[aria-current="page"] { background: var(--base-3); border-color: var(--linha-forte); color: var(--texto); }
```

e `.menu-item.ativo .menu-icone, .menu-item:hover .menu-icone` por `.menu-item[aria-current="page"] .menu-icone, .menu-item:hover .menu-icone`.

(b) Trocar o bloco do comentário `/* Sub-navegação secundária… */` + as regras `.submenu`, `.submenu-item`, `.submenu-item:hover`, `.submenu-item:focus-visible` por:

```css
/* "Nesta análise": atalhos para as seções do laudo, fixos abaixo da barra de
   busca. Rolam na horizontal quando não cabem (celular). */
.subnav-analise {
  position: sticky; top: var(--barra-h); z-index: 15;
  display: flex; align-items: center; gap: 6px;
  overflow-x: auto; scrollbar-width: none;
  padding: 8px var(--vao);
  background: color-mix(in srgb, var(--base) 82%, transparent);
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--linha);
}
.subnav-analise::-webkit-scrollbar { display: none; }
.subnav-legenda { margin: 0 6px 0 0; flex: none; }
.subnav-item {
  flex: none;
  padding: 6px 12px;
  border: 1px solid var(--linha); border-radius: 999px;
  color: var(--texto-2); text-decoration: none; font-size: .76rem; white-space: nowrap;
  transition: border-color .16s, color .16s;
}
.subnav-item:hover { border-color: var(--primaria); color: var(--texto); }
.subnav-item:focus-visible { outline: 2px solid var(--primaria); outline-offset: 2px; }

.quadro, .faixa, .faixa-checklist { scroll-margin-top: calc(var(--barra-h) + 56px); }

.fontes-linha {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px 18px;
  padding: 10px var(--vao);
  border-bottom: 1px solid var(--linha);
}
.fontes-linha .legenda { margin: 0; }
.fontes-linha .fontes { display: flex; flex-wrap: wrap; gap: 8px 18px; }
```

(c) Trocar as regras `.conta-sair { … }`, `.conta-sair:hover { … }` e `.conta-sair:focus-visible { … }` por:

```css
.conta-sair {
  display: flex; align-items: center; gap: 6px;
  margin-left: auto; padding: 6px;
  border: none; background: none;
  font-family: var(--fonte-mono); font-size: .6rem;
  letter-spacing: .1em; text-transform: uppercase;
  color: var(--texto-3); cursor: pointer;
  transition: color .16s;
}
.conta-sair svg { width: 14px; height: 14px; }
.conta-sair:hover { color: var(--perigo); }
.conta-sair:focus-visible { outline: 2px solid var(--primaria); outline-offset: 2px; }
```

(d) No bloco `@media (max-width: 860px)`, apagar as linhas que mencionam `.submenu`, `.submenu-item` e `.fontes`, e acrescentar `.subnav-analise { top: 0; }`.

- [ ] **Step 13: Rodar tudo**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 14: Conferir no navegador**

Logado, visitar `/painel`, `/painel/historico` e `/painel/aprender`: menu lateral idêntico nas três, item da tela atual destacado, nome e inicial da conta preenchidos, "Sair" funciona. Em `/painel`, analisar um link: a fileira "Nesta análise" aparece abaixo das fontes; clicar em "Sinais" rola até a seção sem escondê-la atrás da barra. Rodapé e botão de acessibilidade presentes em todas as telas, incluindo `/inicio`, `/privacidade` e `/termos`. Nenhum erro no console.

- [ ] **Step 15: Commit**

```bash
git add src/spectra_link_guard/web/parciais src/spectra_link_guard/web/static/menu.js \
  src/spectra_link_guard/web/app.py pyproject.toml tests/test_web.py \
  src/spectra_link_guard/web/static/laudo.html src/spectra_link_guard/web/static/laudo.js \
  src/spectra_link_guard/web/static/laudo.css src/spectra_link_guard/web/static/historico.html \
  src/spectra_link_guard/web/static/historico.js src/spectra_link_guard/web/static/aprender.html \
  src/spectra_link_guard/web/static/inicio.html src/spectra_link_guard/web/static/privacidade.html \
  src/spectra_link_guard/web/static/termos.html
git commit -m "$(cat <<'EOF'
Menu, rodapé e acessibilidade como partes compartilhadas

O rodapé e o painel de acessibilidade estavam copiados em 6 arquivos e o
menu em 3. Agora _pagina() encaixa web/parciais/*.html e marca o item
ativo do menu; menu.js cuida da conta e do sair. "Nesta análise" vira uma
fileira de atalhos abaixo da busca, e movimento/acessibilidade carregam no
<head> em todas as telas (sem piscar o tema errado).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Micro-interações e transições

**Files:**
- Create: `src/spectra_link_guard/web/static/animacoes.css`, `animacoes.js`
- Modify: todas as páginas HTML (link + script no `<head>`)
- Modify: `inicio.html` (sai o script inline de revelar e o CSS `.motivo-card`; cards ganham `cartao-vivo`)
- Modify: `laudo.html` (amostras com `cartao-vivo`), `laudo.js` (feixe, LEDs, contador)
- Modify: `historico.html`, `historico.js` (Apagar tudo, toasts, skeleton)
- Modify: `laudo.css` (botões e diálogo)
- Modify: `app.py` (`_ATIVOS_BASE`)
- Modify: `tests/test_frontend.py`

**Interfaces:**
- Consumes: tokens (Task 1), `menu.js`/parciais (Task 3).
- Produces:
  - `window.animarNumero(el: Element, valor: number, opcoes?: { sufixo?: string, duracaoMs?: number })`
  - `window.avisarToast(texto: string, tipo?: "info" | "ok" | "erro")`
  - Classes CSS: `[data-revelar]` / `.revelado`, `.cartao-vivo`, `.esqueleto`, `.esqueleto-linha`, `.fonte.pulsando`, `.q-veredito.varrendo` (lê `--altura-varredura`), `.botao-perigo`, `.botao-secundario`, `.dialogo`.
  - Variável CSS `--ease-saida`.

- [ ] **Step 1: Escrever os testes**

Acrescentar a `tests/test_frontend.py`:

```python


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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_frontend.py -q`
Expected: FAIL nos três testes novos.

- [ ] **Step 3: `animacoes.css`**

Criar `src/spectra_link_guard/web/static/animacoes.css`:

```css
/* Spectra — micro-interações e transições, compartilhadas por todas as telas.
 *
 * Com movimento parado (`data-movimento="off"`, resolvido por movimento.js a
 * partir do interruptor e do prefers-reduced-motion), nada se mexe e nada
 * fica invisível esperando animação. Só transform, translate e opacity são
 * animados.
 */

:root { --ease-saida: cubic-bezier(.16, 1, .3, 1); }

/* Entrada ao rolar. animacoes.js marca .revelado. Usa `translate` (não
   `transform`) para não brigar com o hover dos cards, que usa transform. */
[data-revelar] {
  transition: opacity .55s var(--ease-saida), translate .55s var(--ease-saida);
}
:root.revelar-pronto[data-movimento="on"] [data-revelar]:not(.revelado) {
  opacity: 0;
  translate: 0 18px;
}

/* Hover: quadros grandes só ganham borda; cards pequenos também sobem. */
.quadro { transition: border-color .2s ease; }
.quadro:hover { border-color: color-mix(in srgb, var(--primaria) 35%, var(--linha)); }

.cartao-vivo { transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease; }
.cartao-vivo[data-revelar] {
  transition: opacity .55s var(--ease-saida), translate .55s var(--ease-saida),
              transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}
.cartao-vivo:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--primaria) 60%, var(--linha));
  box-shadow: 0 14px 30px -20px rgb(var(--primaria-rgb) / .55);
}

/* Botões afundam ao clicar (o de acessibilidade não: ele é arrastável). */
button:not(.a11y-botao):not(:disabled):active,
.botao-primario:active { transform: scale(.97); }

/* Skeleton enquanto carrega. */
.esqueleto {
  position: relative; overflow: hidden;
  color: transparent !important;
  background: var(--base-3);
  border-radius: 6px;
}
.esqueleto::after {
  content: ""; position: absolute; inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, rgb(var(--texto-rgb) / .07), transparent);
  animation: esqueleto-brilho 1.3s ease-in-out infinite;
}
.esqueleto-linha { display: block; height: 12px; min-width: 48px; }
@keyframes esqueleto-brilho { to { transform: translateX(100%); } }
:root[data-movimento="off"] .esqueleto::after { display: none; }

/* LEDs de "fontes consultadas" pulsam enquanto a análise roda. */
.fonte.pulsando .led {
  border-color: var(--primaria-clara);
  animation: led-pulso 1s ease-in-out infinite;
}
@keyframes led-pulso {
  0%, 100% { opacity: .35; }
  50%      { opacity: 1; background: var(--primaria-clara); }
}

/* Feixe de varredura sobre o veredito enquanto a análise roda. A altura do
   quadro vem de --altura-varredura (laudo.js mede antes de começar). */
.q-veredito { position: relative; }
.q-veredito.varrendo { overflow: hidden; }
.q-veredito.varrendo::after {
  content: ""; position: absolute; left: 0; right: 0; top: 0; z-index: 3;
  height: 72px; pointer-events: none;
  background: linear-gradient(180deg, transparent, rgb(var(--primaria-rgb) / .26));
  border-bottom: 2px solid var(--primaria-clara);
  animation: varrer 1.6s linear infinite;
}
@keyframes varrer {
  from { transform: translateY(-72px); }
  to   { transform: translateY(var(--altura-varredura, 360px)); }
}
:root[data-movimento="off"] .q-veredito.varrendo::after { display: none; }

/* Avisos curtos (toast). */
.toasts {
  position: fixed; top: 16px; left: 50%; z-index: 90;
  transform: translateX(-50%);
  display: grid; gap: 8px;
  width: min(420px, calc(100vw - 32px));
  pointer-events: none;
}
.toast {
  margin: 0;
  pointer-events: auto;
  padding: 11px 14px;
  background: var(--base-3); color: var(--texto);
  border: 1px solid var(--linha-forte); border-left-width: 3px;
  font-size: .84rem; line-height: 1.45;
  box-shadow: 0 18px 40px -24px rgb(0 0 0 / .9);
  animation: toast-entrar .28s var(--ease-saida) both;
}
.toast[data-tipo="ok"] { border-left-color: var(--secundaria); }
.toast[data-tipo="erro"] { border-left-color: var(--perigo); }
.toast.saindo { animation: toast-sair .2s ease both; }
@keyframes toast-entrar { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: none; } }
@keyframes toast-sair { to { opacity: 0; transform: translateY(-8px); } }

/* Transição entre páginas (View Transitions entre documentos da mesma
   origem). Navegador sem suporte navega normalmente. O menu tem nome
   próprio para ficar parado enquanto o conteúdo faz o fade. */
@view-transition { navigation: auto; }
.trilho { view-transition-name: trilho; }
::view-transition-old(root),
::view-transition-new(root) { animation-duration: .22s; }
:root[data-movimento="off"]::view-transition-group(*),
:root[data-movimento="off"]::view-transition-old(*),
:root[data-movimento="off"]::view-transition-new(*) { animation: none !important; }
@media (prefers-reduced-motion: reduce) {
  ::view-transition-group(*),
  ::view-transition-old(*),
  ::view-transition-new(*) { animation: none !important; }
}
```

- [ ] **Step 4: `animacoes.js`**

Criar `src/spectra_link_guard/web/static/animacoes.js`:

```js
/* Spectra — micro-interações compartilhadas.
 *
 * Carregado no <head>, depois de movimento.js: marca <html> com
 * `revelar-pronto` antes da primeira pintura — sem isso os elementos
 * [data-revelar] apareceriam e sumiriam num piscar. Expõe:
 *   window.animarNumero(el, valor, { sufixo, duracaoMs })
 *   window.avisarToast(texto, tipo)   // "info" | "ok" | "erro"
 */

(function () {
  const raiz = document.documentElement;
  raiz.classList.add("revelar-pronto");

  const movimentoLigado = () => raiz.dataset.movimento !== "off";

  function revelarAoRolar() {
    const alvos = [...document.querySelectorAll("[data-revelar]")];
    if (!alvos.length) return;
    if (!movimentoLigado() || !("IntersectionObserver" in window)) {
      alvos.forEach((el) => el.classList.add("revelado"));
      return;
    }
    const observador = new IntersectionObserver(
      (entradas) => {
        entradas
          .filter((entrada) => entrada.isIntersecting)
          .forEach((entrada, i) => {
            setTimeout(() => entrada.target.classList.add("revelado"), i * 70);
            observador.unobserve(entrada.target);
          });
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" },
    );
    alvos.forEach((el) => observador.observe(el));
  }

  function formatar(valor, sufixo) {
    return `${Math.round(valor).toLocaleString("pt-BR")}${sufixo}`;
  }

  function animarNumero(el, valor, { sufixo = "", duracaoMs = 1100 } = {}) {
    if (!el) return;
    if (!movimentoLigado() || valor === 0) {
      el.textContent = formatar(valor, sufixo);
      return;
    }
    const inicio = performance.now();
    function quadro(agora) {
      const t = Math.min(1, (agora - inicio) / duracaoMs);
      el.textContent = formatar(valor * (1 - Math.pow(1 - t, 3)), sufixo);
      if (t < 1) requestAnimationFrame(quadro);
    }
    requestAnimationFrame(quadro);
  }

  // A região aria-live precisa existir antes do primeiro aviso, senão o
  // leitor de tela não anuncia a primeira mensagem.
  function caixaDeAvisos() {
    let caixa = document.querySelector(".toasts");
    if (!caixa) {
      caixa = document.createElement("div");
      caixa.className = "toasts";
      caixa.setAttribute("role", "status");
      caixa.setAttribute("aria-live", "polite");
      document.body.append(caixa);
    }
    return caixa;
  }

  function avisarToast(texto, tipo = "info") {
    const toast = document.createElement("p");
    toast.className = "toast";
    toast.dataset.tipo = tipo;
    toast.textContent = texto;
    caixaDeAvisos().append(toast);
    setTimeout(() => {
      toast.classList.add("saindo");
      setTimeout(() => toast.remove(), 220);
    }, 3500);
  }

  window.animarNumero = animarNumero;
  window.avisarToast = avisarToast;

  function iniciar() {
    caixaDeAvisos();
    revelarAoRolar();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
```

- [ ] **Step 5: Todas as páginas carregam animações**

Em `inicio.html`, `laudo.html`, `historico.html`, `aprender.html`, `privacidade.html` e `termos.html`:
- depois de `<link rel="stylesheet" href="/static/rodape.css">`, inserir `<link rel="stylesheet" href="/static/animacoes.css">`;
- logo depois de `<script src="/static/acessibilidade.js"></script>` (que está no `<head>` desde a Task 3), inserir `<script src="/static/animacoes.js"></script>`.

Em `app.py`, trocar `_ATIVOS_BASE` por:

```python
_ATIVOS_BASE = (
    "tokens.css", "rodape.css", "animacoes.css",
    "movimento.js", "acessibilidade.js", "animacoes.js",
)
```

- [ ] **Step 6: Home usa o revelar compartilhado**

Em `inicio.html`:
- apagar do `<style>` o comentário `/* Seção "Por que usar nossos serviços?": entrada ao rolar + hover. */` e as regras `.motivo-card { … }`, `.motivo-card.revelado { … }`, `.motivo-card:hover { … }` e `:root[data-movimento="off"] .motivo-card { … }`;
- apagar o `<script>` inline que começa com `// Entrada ao rolar dos cards "por que usar"` (o bloco `<script>…</script>` inteiro);
- nos seis `<article class="motivo-card rounded-xl border border-linha bg-sup p-6" data-revelar>`, trocar `motivo-card` por `motivo-card cartao-vivo`.

- [ ] **Step 7: Feedback da análise no laudo**

Em `laudo.html`, nos quatro `<button class="amostra" …>`, trocar `class="amostra"` por `class="amostra cartao-vivo"`.

Em `laudo.js`:

(a) Em `periciar(url)`, logo depois de `avisar("");`, inserir:

```js
  const quadroVeredito = $("q-veredito");
  quadroVeredito.style.setProperty("--altura-varredura", `${quadroVeredito.offsetHeight}px`);
  quadroVeredito.classList.add("varrendo");
  document.querySelectorAll(".fonte").forEach((fonte) => fonte.classList.add("pulsando"));
```

(b) No `finally` de `periciar`, antes de `botao.disabled = false;`, inserir:

```js
    $("q-veredito").classList.remove("varrendo");
    document.querySelectorAll(".fonte").forEach((fonte) => fonte.classList.remove("pulsando"));
```

(c) Trocar a assinatura e a primeira linha de `renderGrafico`:

```js
function renderGrafico(r, { animar = true } = {}) {
  if (animar) animarNumero($("pontuacao-numero"), r.risco);
  else $("pontuacao-numero").textContent = r.risco;
```

(d) No listener `spectra:tema` (Task 1), trocar `renderGrafico(laudoAtual);` por `renderGrafico(laudoAtual, { animar: false });`.

- [ ] **Step 8: Histórico com "Apagar tudo", avisos e skeleton**

Em `historico.html`:

(a) Dentro de `<div class="hist-controles">`, depois do `</select>`, inserir:

```html
    <button type="button" class="botao-perigo" id="hist-apagar-tudo" disabled>
      <i data-lucide="trash-2" aria-hidden="true"></i>Apagar tudo
    </button>
```

(b) Antes de `<!--PARCIAL:acessibilidade-->`, inserir:

```html
<dialog class="dialogo" id="dialogo-apagar" aria-labelledby="dialogo-apagar-titulo">
  <form method="dialog" class="dialogo-corpo">
    <h2 id="dialogo-apagar-titulo" class="dialogo-titulo">Apagar todo o histórico?</h2>
    <p class="dialogo-texto">Todas as suas análises salvas serão apagadas. Isso não pode ser desfeito.</p>
    <div class="dialogo-acoes">
      <button value="cancelar" class="botao-secundario">Cancelar</button>
      <button value="apagar" class="botao-perigo">Apagar tudo</button>
    </div>
  </form>
</dialog>
```

Substituir `src/spectra_link_guard/web/static/historico.js` por:

```js
/* Spectra — Histórico.
 *
 * Consome a API por usuário: GET /api/painel/historico, DELETE
 * /api/painel/{id} e DELETE /api/painel (apagar tudo). Busca e filtro rodam
 * no cliente: a lista tem no máximo 500 itens. Sem sessão a API responde 401
 * e a tela volta para a entrada.
 */

const $ = (id) => document.getElementById(id);

const NOME_NIVEL = { seguro: "seguro", baixo: "baixo", atencao: "atenção", alto: "alto", critico: "crítico" };
const TOKEN_NIVEL = {
  seguro: "secundaria", baixo: "secundaria", atencao: "terciaria", alto: "perigo", critico: "perigo",
};

let itensTodos = [];
let graficoHist = null;

function corNivel(nivel) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(`--${TOKEN_NIVEL[nivel]}`).trim();
}

function elemento(tag, classe, texto) {
  const el = document.createElement(tag);
  if (classe) el.className = classe;
  if (texto !== undefined && texto !== null) el.textContent = String(texto);
  return el;
}

function celula(rotulo, classe, texto) {
  const td = elemento("td", classe, texto);
  td.dataset.rotulo = rotulo;
  return td;
}

function formatarQuando(iso) {
  const data = new Date(iso);
  return Number.isNaN(data.getTime())
    ? iso
    : data.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function voltarParaEntrada() {
  window.location.href = "/inicio?erro=entre_primeiro";
}

function itensFiltrados() {
  const busca = $("hist-busca").value.trim().toLowerCase();
  const filtro = $("hist-filtro").value;
  return itensTodos.filter((item) => {
    if (filtro && item.nivel !== filtro) return false;
    if (!busca) return true;
    return (item.host || "").toLowerCase().includes(busca)
      || (item.dominio || "").toLowerCase().includes(busca);
  });
}

async function apagar(item) {
  let resp;
  try {
    resp = await fetch(`/api/painel/${item.id}`, { method: "DELETE" });
  } catch {
    avisarToast("Sem resposta do servidor. Tente de novo.", "erro");
    return;
  }
  if (resp.status === 401) return voltarParaEntrada();
  if (!resp.ok && resp.status !== 404) {
    avisarToast("Não foi possível apagar esta análise.", "erro");
    return;
  }
  itensTodos = itensTodos.filter((i) => i.id !== item.id);
  renderizarTudo();
  avisarToast(`Análise de ${item.host || "link"} apagada.`, "ok");
}

async function apagarTudo() {
  let resp;
  try {
    resp = await fetch("/api/painel", { method: "DELETE" });
  } catch {
    avisarToast("Sem resposta do servidor. Tente de novo.", "erro");
    return;
  }
  if (resp.status === 401) return voltarParaEntrada();
  if (!resp.ok) {
    avisarToast("Não foi possível apagar o histórico.", "erro");
    return;
  }
  itensTodos = [];
  renderizarTudo();
  avisarToast("Histórico apagado.", "ok");
}

function linhaHist(item) {
  const tr = elemento("tr");
  tr.append(celula("Quando", "mono", formatarQuando(item.quando)));
  tr.append(celula("Host", "mono copiavel", item.host || "(sem host)"));
  tr.append(celula("Domínio", "mono copiavel", item.dominio || "(sem domínio)"));

  const tdVeredito = celula("Veredito");
  const selo = elemento("span", "hist-veredito", NOME_NIVEL[item.nivel] || item.nivel);
  selo.dataset.nivel = item.nivel;
  tdVeredito.append(selo);
  tr.append(tdVeredito);

  tr.append(celula("Nota", "mono", `${item.risco}/100`));

  const tdAcao = celula("Ações");
  const botao = elemento("button", "hist-apagar");
  botao.type = "button";
  botao.setAttribute("aria-label", `Apagar análise de ${item.host || "link"} do histórico`);
  const icone = document.createElement("i");
  icone.setAttribute("data-lucide", "trash-2");
  icone.setAttribute("aria-hidden", "true");
  botao.append(icone);
  botao.addEventListener("click", () => apagar(item));
  tdAcao.append(botao);
  tr.append(tdAcao);

  return tr;
}

function renderizarTabela() {
  const filtrados = itensFiltrados();
  $("hist-corpo").replaceChildren(...filtrados.map(linhaHist));
  $("hist-vazio").hidden = filtrados.length > 0;
  $("hist-contagem").textContent = `${filtrados.length} de ${itensTodos.length}`;
  $("hist-apagar-tudo").disabled = itensTodos.length === 0;
  if (window.lucide) window.lucide.createIcons();
}

function renderizarResumo() {
  $("hist-total").textContent = `${itensTodos.length} análise${itensTodos.length === 1 ? "" : "s"}`;

  const contagem = { seguro: 0, baixo: 0, atencao: 0, alto: 0, critico: 0 };
  for (const item of itensTodos) contagem[item.nivel] = (contagem[item.nivel] || 0) + 1;

  const legenda = $("hist-legenda");
  legenda.replaceChildren();
  for (const nivel of Object.keys(contagem)) {
    const li = elemento("li");
    const ponto = elemento("span", "ponto");
    ponto.style.background = corNivel(nivel);
    li.append(ponto, elemento("span", "", NOME_NIVEL[nivel]), elemento("span", "qtd", contagem[nivel]));
    legenda.append(li);
  }

  if (!window.Chart) return;
  const semMovimento = window.spectraMovimentoLigado && !window.spectraMovimentoLigado();
  if (graficoHist) graficoHist.destroy();
  graficoHist = new Chart($("hist-grafico"), {
    type: "doughnut",
    data: {
      labels: Object.keys(contagem).map((n) => NOME_NIVEL[n]),
      datasets: [{
        data: Object.values(contagem),
        backgroundColor: Object.keys(contagem).map(corNivel),
        borderWidth: 0,
      }],
    },
    options: {
      cutout: "62%",
      animation: semMovimento ? false : { duration: 500 },
      plugins: { legend: { display: false } },
    },
  });
}

function renderizarTudo() {
  renderizarResumo();
  renderizarTabela();
}

function esqueletoTabela(linhas = 4) {
  const corpo = $("hist-corpo");
  corpo.replaceChildren();
  for (let i = 0; i < linhas; i += 1) {
    const tr = elemento("tr");
    for (let j = 0; j < 6; j += 1) {
      const td = elemento("td");
      td.append(elemento("span", "esqueleto esqueleto-linha", "carregando"));
      tr.append(td);
    }
    corpo.append(tr);
  }
}

async function carregar() {
  esqueletoTabela();
  let resp;
  try {
    resp = await fetch("/api/painel/historico");
  } catch {
    avisarToast("Não foi possível carregar o histórico.", "erro");
    itensTodos = [];
    renderizarTudo();
    return;
  }
  if (resp.status === 401) return voltarParaEntrada();
  itensTodos = (await resp.json()).itens || [];
  renderizarTudo();
}

const dialogo = $("dialogo-apagar");
$("hist-busca").addEventListener("input", renderizarTabela);
$("hist-filtro").addEventListener("change", renderizarTabela);
$("hist-apagar-tudo").addEventListener("click", () => dialogo.showModal());
dialogo.addEventListener("close", () => {
  if (dialogo.returnValue === "apagar") apagarTudo();
});
window.addEventListener("spectra:tema", renderizarResumo);

carregar();
```

- [ ] **Step 9: Estilo dos botões e do diálogo**

Acrescentar a `laudo.css`, logo antes do comentário `/* ─── amostras */`:

```css
/* ───────────────────────────────────────────────────── botões e diálogo */

.botao-perigo, .botao-secundario {
  display: inline-flex; align-items: center; justify-content: center; gap: 7px;
  min-height: 40px; padding: 8px 14px;
  background: transparent;
  font-family: var(--fonte-corpo); font-size: .8rem;
  cursor: pointer;
  transition: border-color .16s, color .16s, background .16s;
}
.botao-perigo svg, .botao-secundario svg { width: 15px; height: 15px; }
.botao-perigo { border: 1px solid rgb(var(--perigo-rgb) / .6); color: var(--perigo); }
.botao-perigo:hover:not(:disabled) { background: rgb(var(--perigo-rgb) / .12); border-color: var(--perigo); }
.botao-perigo:disabled { opacity: .45; cursor: not-allowed; }
.botao-secundario { border: 1px solid var(--linha-forte); color: var(--texto); }
.botao-secundario:hover { border-color: var(--primaria); }
.botao-perigo:focus-visible, .botao-secundario:focus-visible {
  outline: 2px solid var(--primaria); outline-offset: 2px;
}

.dialogo {
  width: min(440px, calc(100vw - 32px));
  padding: 0;
  border: 1px solid var(--linha-forte);
  background: var(--base-2); color: var(--texto);
}
.dialogo::backdrop {
  background: rgb(var(--base-rgb) / .75);
  -webkit-backdrop-filter: blur(4px);
  backdrop-filter: blur(4px);
}
.dialogo-corpo { margin: 0; padding: 22px; display: grid; gap: 12px; }
.dialogo-titulo { font-size: 1.05rem; }
.dialogo-texto { margin: 0; color: var(--texto-2); font-size: .88rem; line-height: 1.6; }
.dialogo-acoes { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 10px; margin-top: 6px; }
```

- [ ] **Step 10: Rodar tudo**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 11: Conferir no navegador**

- `/inicio`: rolar até "Por que usar"; os cards entram em sequência e sobem no hover. Com "Movimento parado", aparecem direto.
- `/painel`: analisar um link; durante a espera os LEDs pulsam e o feixe percorre o quadro do veredito; o número do medidor conta até a nota.
- `/painel/historico`: enquanto carrega, aparecem blocos pulsando; apagar um item mostra o aviso "Análise de … apagada."; "Apagar tudo" abre o diálogo (Esc ou Cancelar não apagam; Apagar tudo esvazia a lista e o botão fica desabilitado).
- Navegar entre Verificar, Histórico e Aprender no Chrome/Edge: conteúdo faz fade e o menu fica parado.
- Nenhum erro no console.

- [ ] **Step 12: Commit**

```bash
git add src/spectra_link_guard/web/static/animacoes.css src/spectra_link_guard/web/static/animacoes.js \
  src/spectra_link_guard/web/static/*.html src/spectra_link_guard/web/static/laudo.js \
  src/spectra_link_guard/web/static/historico.js src/spectra_link_guard/web/static/laudo.css \
  src/spectra_link_guard/web/app.py tests/test_frontend.py
git commit -m "$(cat <<'EOF'
Micro-interações e transição entre páginas

animacoes.css/js compartilhados: entrada ao rolar, hover nos cards,
skeleton, contador animado, avisos e View Transitions. Durante a análise,
os LEDs das fontes pulsam e um feixe de varredura passa pelo veredito. O
histórico ganha "Apagar tudo" com confirmação. Tudo para com movimento
desligado.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Tela "Visão geral"

**Files:**
- Create: `src/spectra_link_guard/web/static/visao-geral.html`, `visao-geral.js`
- Modify: `src/spectra_link_guard/web/parciais/menu.html` (item novo)
- Modify: `src/spectra_link_guard/web/static/historico.html` (link para a Visão geral)
- Modify: `src/spectra_link_guard/web/app.py` (rota)
- Modify: `src/spectra_link_guard/web/static/laudo.css` (estilos `vg-*`, `kpi`, `botao-primario`, `botao-link`)
- Modify: `tests/test_web.py`

**Interfaces:**
- Consumes: `GET /api/painel/estatisticas` (Task 2), `animarNumero`, `avisarToast`, `.esqueleto`, `.cartao-vivo` (Task 4), `_ATIVOS_PAINEL`/`menu=` (Task 3), evento `spectra:tema` (Task 1), evento `spectra:movimento` (movimento.js).
- Produces: rota `GET /painel/visao-geral`; `data-menu="visao-geral"`; classes `.botao-primario`, `.botao-link`.

- [ ] **Step 1: Escrever os testes**

Em `tests/test_web.py`:
- trocar o parametrize de `test_telas_do_painel_exigem_sessao` por `["/painel", "/painel/visao-geral", "/painel/historico", "/painel/aprender"]`;
- trocar `ITENS_DO_MENU` por `["verificar", "visao-geral", "historico", "aprender"]` e acrescentar `("/painel/visao-geral", "visao-geral")` a `TELAS_DO_PAINEL`;
- acrescentar:

```python


def test_visao_geral_traz_indicadores_e_graficos(cliente):
    entrar(cliente)
    html = cliente.get("/painel/visao-geral").text
    for alvo in ("kpi-total", "kpi-perigosos", "kpi-risco", "kpi-seguras",
                 "g-tempo", "g-niveis", "g-sinais", "vg-vazio"):
        assert f'id="{alvo}"' in html
    assert "visao-geral.js?v=" in html
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_web.py -q`
Expected: FAIL — `/painel/visao-geral` responde 404.

- [ ] **Step 3: Item no menu**

Em `src/spectra_link_guard/web/parciais/menu.html`, entre o item de Verificar e o de Histórico, inserir:

```html
    <a class="menu-item" href="/painel/visao-geral" data-menu="visao-geral">
      <i data-lucide="layout-dashboard" class="menu-icone" aria-hidden="true"></i><span class="menu-rotulo">Visão geral</span>
    </a>
```

- [ ] **Step 4: Rota**

Em `app.py`, depois da rota `/painel`, inserir:

```python


@app.get("/painel/visao-geral", include_in_schema=False)
async def painel_visao_geral(request: Request) -> Response:
    """Dashboard com os números e gráficos das análises do usuário."""
    if usuario_atual(request.cookies.get("spectra_sessao")) is None:
        return RedirectResponse("/inicio?erro=entre_primeiro", status_code=303)
    return _pagina("visao-geral.html", *_ATIVOS_PAINEL, "visao-geral.js", menu="visao-geral")
```

- [ ] **Step 5: `visao-geral.html`**

Criar `src/spectra_link_guard/web/static/visao-geral.html`:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Spectra</title>
<meta name="description" content="Números e gráficos das suas análises de links.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&family=Inter:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/tokens.css">
<link rel="stylesheet" href="/static/laudo.css">
<link rel="stylesheet" href="/static/rodape.css">
<link rel="stylesheet" href="/static/animacoes.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛡️</text></svg>">
<script src="/static/movimento.js"></script>
<script src="/static/acessibilidade.js"></script>
<script src="/static/animacoes.js"></script>
<script src="https://unpkg.com/lucide@0.462.0/dist/umd/lucide.js" defer
        integrity="sha384-WBRt9V/J/erVtkEuP91HUFRv9MvHzFiFOp4/zTDp4xkcMG7aOeIv2asTV4yxFLWa" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js" defer
        integrity="sha384-NrKB+u6Ts6AtkIhwPixiKTzgSKNblyhlk0Sohlgar9UHUBzai/sgnNNWWd291xqt" crossorigin="anonymous"></script>
</head>
<body data-estado="seguro">

<div class="app">

<!--PARCIAL:menu-->

<div class="corpo">

<header class="barra hist-barra">
  <h1 class="hist-titulo">Visão geral</h1>
  <a class="botao-link" href="/painel/historico">Ver histórico</a>
</header>

<main class="grade" id="visao" aria-busy="true">

  <section class="vg-kpis" aria-label="Indicadores">
    <article class="quadro kpi cartao-vivo">
      <p class="kpi-rotulo">Análises</p>
      <p class="kpi-valor esqueleto" id="kpi-total">0</p>
    </article>
    <article class="quadro kpi cartao-vivo">
      <p class="kpi-rotulo">Perigosas</p>
      <p class="kpi-valor kpi-perigo esqueleto" id="kpi-perigosos">0</p>
    </article>
    <article class="quadro kpi cartao-vivo">
      <p class="kpi-rotulo">Risco médio</p>
      <p class="kpi-valor esqueleto" id="kpi-risco">0</p>
    </article>
    <article class="quadro kpi cartao-vivo">
      <p class="kpi-rotulo">Seguras</p>
      <p class="kpi-valor esqueleto" id="kpi-seguras">0%</p>
    </article>
  </section>

  <section class="quadro vg-vazio" id="vg-vazio" hidden>
    <div class="quadro-corpo vg-vazio-corpo">
      <i data-lucide="radar" class="vg-vazio-icone" aria-hidden="true"></i>
      <h2 class="vg-vazio-titulo">Nenhuma análise ainda</h2>
      <p class="vg-vazio-texto">Os gráficos aparecem aqui depois que você verificar o primeiro link.</p>
      <a class="botao-primario" href="/painel">Verificar meu primeiro link</a>
    </div>
  </section>

  <section class="quadro vg-tempo" data-com-dados>
    <header class="quadro-topo">
      <h2 class="quadro-titulo">Últimos 30 dias</h2>
      <span class="quadro-marca mono">análises e risco médio</span>
    </header>
    <div class="quadro-corpo">
      <div class="grafico-caixa grafico-alto">
        <canvas id="g-tempo" role="img" aria-label="Gráfico de análises por dia nos últimos 30 dias"></canvas>
      </div>
    </div>
  </section>

  <section class="quadro vg-niveis" data-com-dados>
    <header class="quadro-topo"><h2 class="quadro-titulo">Vereditos</h2></header>
    <div class="quadro-corpo">
      <div class="grafico-caixa">
        <canvas id="g-niveis" role="img" aria-label="Distribuição de vereditos"></canvas>
      </div>
    </div>
  </section>

  <section class="quadro vg-sinais" data-com-dados>
    <header class="quadro-topo"><h2 class="quadro-titulo">Sinais mais frequentes</h2></header>
    <div class="quadro-corpo">
      <div class="grafico-caixa">
        <canvas id="g-sinais" role="img" aria-label="Sinais de risco mais frequentes"></canvas>
      </div>
      <p class="vg-sinais-vazio" id="vg-sinais-vazio" hidden>Nenhum sinal de risco nas suas análises até agora.</p>
    </div>
  </section>

</main>

<!--PARCIAL:rodape-->

</div>
</div>

<!--PARCIAL:acessibilidade-->

<script src="/static/menu.js" defer></script>
<script src="/static/visao-geral.js" defer></script>
</body>
</html>
```

- [ ] **Step 6: `visao-geral.js`**

Criar `src/spectra_link_guard/web/static/visao-geral.js`:

```js
/* Spectra — Visão geral.
 *
 * Lê GET /api/painel/estatisticas (já agregado no servidor) e desenha os
 * indicadores e três gráficos. Cores vêm dos tokens; os gráficos se
 * redesenham quando o tema ou o movimento mudam. Carregado com defer, depois
 * do Chart.js.
 */

const $ = (id) => document.getElementById(id);

const NIVEIS = ["seguro", "baixo", "atencao", "alto", "critico"];
const NOME_NIVEL = { seguro: "Seguro", baixo: "Baixo", atencao: "Atenção", alto: "Alto", critico: "Crítico" };
const COR_NIVEL = {
  seguro: ["secundaria", 1],
  baixo: ["primaria-clara", 1],
  atencao: ["terciaria", 1],
  alto: ["perigo", 0.6],
  critico: ["perigo", 1],
};

let dados = null;
let graficos = [];

function cor(token, alfa = 1) {
  const canais = getComputedStyle(document.documentElement).getPropertyValue(`--${token}-rgb`).trim();
  return `rgb(${canais} / ${alfa})`;
}

function semMovimento() {
  return window.spectraMovimentoLigado && !window.spectraMovimentoLigado();
}

function diaCurto(iso) {
  const [, mes, dia] = iso.split("-");
  return `${dia}/${mes}`;
}

function graficoTempo(animacao) {
  return new Chart($("g-tempo"), {
    data: {
      labels: dados.por_dia.map((d) => diaCurto(d.dia)),
      datasets: [
        {
          type: "bar", label: "Análises", order: 2, yAxisID: "y",
          data: dados.por_dia.map((d) => d.total),
          backgroundColor: cor("primaria", 0.55), borderRadius: 3,
        },
        {
          type: "line", label: "Risco médio", order: 1, yAxisID: "y1",
          data: dados.por_dia.map((d) => (d.total ? d.risco_medio : null)),
          borderColor: cor("terciaria"), backgroundColor: cor("terciaria"),
          pointRadius: 2, tension: 0.3, spanGaps: true,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      animation: animacao,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 8 } },
        y: { beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: "análises" } },
        y1: {
          position: "right", min: 0, max: 100,
          grid: { drawOnChartArea: false }, title: { display: true, text: "risco" },
        },
      },
      plugins: { legend: { labels: { boxWidth: 12 } } },
    },
  });
}

function graficoNiveis(animacao) {
  return new Chart($("g-niveis"), {
    type: "doughnut",
    data: {
      labels: NIVEIS.map((n) => NOME_NIVEL[n]),
      datasets: [{
        data: NIVEIS.map((n) => dados.por_nivel[n] || 0),
        backgroundColor: NIVEIS.map((n) => cor(...COR_NIVEL[n])),
        borderWidth: 0,
      }],
    },
    options: {
      maintainAspectRatio: false,
      cutout: "62%",
      animation: animacao,
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12 } } },
    },
  });
}

function graficoSinais(animacao) {
  return new Chart($("g-sinais"), {
    type: "bar",
    data: {
      labels: dados.sinais_frequentes.map((s) => s.rotulo),
      datasets: [{
        label: "Vezes",
        data: dados.sinais_frequentes.map((s) => s.vezes),
        backgroundColor: cor("perigo", 0.55), borderRadius: 3,
      }],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      animation: animacao,
      scales: { x: { beginAtZero: true, ticks: { precision: 0 } }, y: { grid: { display: false } } },
      plugins: { legend: { display: false } },
    },
  });
}

/** Os canvas são imagens para o leitor de tela: o rótulo carrega os números. */
function descreverGraficos() {
  const niveis = NIVEIS.map((n) => `${dados.por_nivel[n] || 0} ${NOME_NIVEL[n].toLowerCase()}`).join(", ");
  $("g-niveis").setAttribute("aria-label", `Distribuição de vereditos: ${niveis}.`);

  const sinais = dados.sinais_frequentes.map((s) => `${s.rotulo}: ${s.vezes}`).join("; ");
  $("g-sinais").setAttribute("aria-label", sinais
    ? `Sinais mais frequentes: ${sinais}.`
    : "Nenhum sinal de risco registrado ainda.");

  const dias = dados.por_dia.filter((d) => d.total);
  const totalPeriodo = dias.reduce((soma, d) => soma + d.total, 0);
  $("g-tempo").setAttribute("aria-label",
    `Últimos ${dados.por_dia.length} dias: ${totalPeriodo} análises em ${dias.length} dias.`);
}

function desenhar() {
  graficos.forEach((grafico) => grafico.destroy());
  graficos = [];
  if (!window.Chart || !dados || !dados.total) return;

  Chart.defaults.color = cor("texto-3");
  Chart.defaults.borderColor = cor("linha");
  Chart.defaults.font.family = '"Inter", system-ui, sans-serif';
  const animacao = semMovimento() ? false : { duration: 700 };

  graficos.push(graficoTempo(animacao), graficoNiveis(animacao));
  const temSinais = dados.sinais_frequentes.length > 0;
  if (temSinais) graficos.push(graficoSinais(animacao));
  $("vg-sinais-vazio").hidden = temSinais;
  descreverGraficos();
}

async function carregar() {
  try {
    const resp = await fetch("/api/painel/estatisticas");
    if (resp.status === 401) {
      window.location.href = "/inicio?erro=entre_primeiro";
      return;
    }
    dados = await resp.json();
  } catch {
    avisarToast("Não foi possível carregar a visão geral.", "erro");
    return;
  } finally {
    $("visao").setAttribute("aria-busy", "false");
    document.querySelectorAll(".kpi-valor.esqueleto").forEach((el) => el.classList.remove("esqueleto"));
  }

  animarNumero($("kpi-total"), dados.total);
  animarNumero($("kpi-perigosos"), dados.perigosos);
  animarNumero($("kpi-risco"), dados.risco_medio);
  animarNumero($("kpi-seguras"), dados.pct_seguras, { sufixo: "%" });

  const vazio = !dados.total;
  $("vg-vazio").hidden = !vazio;
  document.querySelectorAll("[data-com-dados]").forEach((el) => { el.hidden = vazio; });
  desenhar();
}

window.addEventListener("spectra:tema", desenhar);
window.addEventListener("spectra:movimento", desenhar);
carregar();
```

- [ ] **Step 7: Estilos da Visão geral**

Acrescentar a `laudo.css`, logo antes do comentário `/* ─── botões e diálogo */` (Task 4):

```css
/* ───────────────────────────────────────────────────── visão geral */

.vg-kpis {
  grid-column: span 12;
  display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--vao);
}
.kpi { padding: 16px; }
.kpi-rotulo {
  margin: 0;
  font-family: var(--fonte-mono); font-size: .6rem;
  letter-spacing: .12em; text-transform: uppercase; color: var(--texto-3);
}
.kpi-valor {
  margin: 10px 0 0; min-width: 3ch;
  font-family: var(--fonte-titulo); font-weight: 800;
  font-size: clamp(1.6rem, 3vw, 2.3rem); line-height: 1.1; color: var(--texto);
}
.kpi-perigo { color: var(--perigo); }

.vg-tempo { grid-column: span 12; }
.vg-niveis { grid-column: span 5; }
.vg-sinais { grid-column: span 7; }
.grafico-caixa { position: relative; height: 240px; }
.grafico-alto { height: 280px; }
.vg-sinais-vazio { margin: 0; color: var(--texto-3); font-size: .84rem; }

.vg-vazio { grid-column: span 12; }
.vg-vazio-corpo { display: grid; justify-items: center; gap: 10px; padding: 40px 16px; text-align: center; }
.vg-vazio-icone { width: 36px; height: 36px; color: var(--primaria-clara); }
.vg-vazio-titulo { font-size: 1.15rem; }
.vg-vazio-texto { margin: 0 0 6px; color: var(--texto-2); max-width: 46ch; }

.botao-primario {
  display: inline-flex; align-items: center; gap: 8px;
  min-height: 44px; padding: 10px 18px;
  border: 1px solid var(--primaria);
  background: var(--primaria); color: var(--sobre-primaria);
  font-family: var(--fonte-titulo); font-weight: 700; font-size: .84rem;
  text-decoration: none;
  transition: filter .16s;
}
.botao-primario:hover { filter: brightness(1.12); }
.botao-primario:focus-visible { outline: 2px solid var(--primaria-clara); outline-offset: 3px; }

.botao-link {
  margin-left: auto;
  display: inline-flex; align-items: center; min-height: 44px;
  color: var(--primaria-clara); font-size: .84rem; text-decoration: none;
}
.botao-link:hover { text-decoration: underline; text-underline-offset: 4px; }
.botao-link:focus-visible { outline: 2px solid var(--primaria); outline-offset: 2px; }

@media (max-width: 1023px) {
  .vg-kpis { grid-template-columns: repeat(2, 1fr); }
  .vg-niveis, .vg-sinais { grid-column: span 12; }
}

.hist-resumo-corpo .botao-link { margin-left: 0; }
```

Em `historico.html`, dentro de `<div class="quadro-corpo hist-resumo-corpo">`, logo depois do `<p class="hist-nota">…</p>`, inserir:

```html
      <a class="botao-link" href="/painel/visao-geral">Ver gráficos na Visão geral</a>
```

- [ ] **Step 8: Rodar tudo**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 9: Conferir no navegador**

- Conta nova em `/painel/visao-geral`: indicadores em 0, estado vazio com "Verificar meu primeiro link"; gráficos escondidos.
- Analisar 3 links (um perigoso, um seguro, um encurtado) e voltar: os contadores sobem, os três gráficos aparecem, a barra de hoje tem 3 análises, a rosca tem as cores dos níveis, "Sinais mais frequentes" lista nomes legíveis (ex.: "Link encurtado").
- Trocar o tema: os gráficos se redesenham com as cores do tema claro. Ligar "Movimento parado": sem animação ao redesenhar.
- O item "Visão geral" do menu fica destacado. Nenhum erro no console.

- [ ] **Step 10: Commit**

```bash
git add src/spectra_link_guard/web/static/visao-geral.html src/spectra_link_guard/web/static/visao-geral.js \
  src/spectra_link_guard/web/parciais/menu.html src/spectra_link_guard/web/app.py \
  src/spectra_link_guard/web/static/laudo.css src/spectra_link_guard/web/static/historico.html \
  tests/test_web.py
git commit -m "$(cat <<'EOF'
Tela Visão geral com indicadores e gráficos

Dashboard em /painel/visao-geral: total, perigosas, risco médio e % seguras
com contador animado; análises e risco médio dos últimos 30 dias; rosca de
vereditos e os sinais mais frequentes. Cores dos tokens, redesenho ao
trocar o tema e estado vazio com atalho para a primeira análise.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Efeitos de fundo (varredura e chuva hexadecimal)

**Files:**
- Create: `src/spectra_link_guard/web/static/fundo.js`
- Modify: `visao-geral.html`, `historico.html`, `aprender.html`, `inicio.html` (canvas + script)
- Modify: `rodape.css` (brilho estático, `.fundo-fixo`, `.fundo-animado`)
- Modify: `app.py` (ativo `fundo.js`)
- Modify: `tests/test_frontend.py`

**Interfaces:**
- Consumes: tokens `--*-rgb`, `--brilho-1`, `--brilho-2` (Task 1); eventos `spectra:movimento` (movimento.js) e `spectra:tema` (Task 1).
- Produces: `<canvas class="fundo-animado" data-efeito="varredura|chuva-hex">`, inicializado automaticamente por `fundo.js`; wrapper `.fundo-fixo`.

- [ ] **Step 1: Escrever os testes**

Acrescentar a `tests/test_frontend.py`:

```python


EFEITOS_POR_PAGINA = {
    "visao-geral.html": "varredura",
    "historico.html": "varredura",
    "aprender.html": "chuva-hex",
    "inicio.html": "chuva-hex",
}


def test_cada_tela_tem_o_efeito_de_fundo_combinado():
    for nome in PAGINAS:
        html = _html(nome)
        efeitos = re.findall(r'data-efeito="([a-z-]+)"', html)
        esperado = EFEITOS_POR_PAGINA.get(nome)
        if esperado:
            assert efeitos == [esperado], f"{nome}: {efeitos}"
            assert "/static/fundo.js" in html, nome
        else:
            assert efeitos == [], f"{nome} não deveria ter efeito de fundo: {efeitos}"
            assert "/static/fundo.js" not in html, nome
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_frontend.py -q`
Expected: FAIL — nenhuma página tem `data-efeito`.

- [ ] **Step 3: `fundo.js`**

Criar `src/spectra_link_guard/web/static/fundo.js`:

```js
/* Spectra — efeitos de fundo em canvas.
 *
 * Inicializa todo <canvas class="fundo-animado" data-efeito="..."> da página:
 *   - "varredura": grade com um feixe de scanner que acende pontos ao passar;
 *   - "chuva-hex": colunas de caracteres hexadecimais caindo.
 * O canvas ocupa o elemento pai. As cores vêm dos tokens a cada quadro, então
 * trocar o tema não exige reiniciar nada.
 *
 * Desempenho: resolução limitada a 1,5x; pausa com a aba em segundo plano e
 * com o canvas fora da tela; no celular, menos quadros e feixe mais lento.
 * Movimento parado: a varredura desenha só a grade, uma vez; a chuva some.
 */

(function () {
  const raiz = document.documentElement;
  const DPR = Math.min(window.devicePixelRatio || 1, 1.5);
  const HEX = "0123456789ABCDEF";

  const movimentoLigado = () => raiz.dataset.movimento !== "off";
  const celular = () => window.matchMedia("(max-width: 599px)").matches;

  /** Uma leitura de estilo por quadro; devolve cor(token, alfa). */
  function paleta() {
    const estilo = getComputedStyle(raiz);
    return (token, alfa) => `rgb(${estilo.getPropertyValue(`--${token}-rgb`).trim()} / ${alfa})`;
  }

  const varredura = {
    iniciar: () => ({ y: -60, pontos: [], ultimo: 0 }),
    redimensionar(estado, largura, altura) {
      const quantidade = Math.max(6, Math.min(40, Math.round((largura * altura) / 26000)));
      estado.pontos = Array.from({ length: quantidade }, () => ({
        x: Math.random() * largura,
        y: Math.random() * altura,
        aceso: -Infinity,
        perigo: Math.random() < 0.3,
      }));
    },
    intervaloMs: () => (celular() ? 33 : 16),
    grade(ctx, largura, altura, cor) {
      ctx.strokeStyle = cor("linha-forte", 0.35);
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = 0.5; x < largura; x += 22) { ctx.moveTo(x, 0); ctx.lineTo(x, altura); }
      for (let y = 0.5; y < altura; y += 22) { ctx.moveTo(0, y); ctx.lineTo(largura, y); }
      ctx.stroke();
    },
    estatico(ctx, estado, largura, altura, cor) {
      ctx.clearRect(0, 0, largura, altura);
      this.grade(ctx, largura, altura, cor);
    },
    quadro(ctx, estado, largura, altura, agora, cor) {
      const passo = estado.ultimo ? Math.min(agora - estado.ultimo, 100) : 16;
      estado.ultimo = agora;
      estado.y += (celular() ? 0.036 : 0.06) * passo; // px por ms
      if (estado.y > altura + 60) estado.y = -60;

      ctx.clearRect(0, 0, largura, altura);
      this.grade(ctx, largura, altura, cor);

      const rastro = ctx.createLinearGradient(0, estado.y - 56, 0, estado.y);
      rastro.addColorStop(0, cor("primaria", 0));
      rastro.addColorStop(1, cor("primaria", 0.22));
      ctx.fillStyle = rastro;
      ctx.fillRect(0, estado.y - 56, largura, 56);
      ctx.fillStyle = cor("primaria-clara", 0.8);
      ctx.fillRect(0, estado.y, largura, 1.5);

      for (const ponto of estado.pontos) {
        if (Math.abs(ponto.y - estado.y) < 3) ponto.aceso = agora;
        const forca = 1 - (agora - ponto.aceso) / 1500;
        if (forca <= 0) continue;
        ctx.fillStyle = cor(ponto.perigo ? "perigo" : "terciaria", forca * 0.85);
        ctx.beginPath();
        ctx.arc(ponto.x, ponto.y, 2.5 + 4 * (1 - forca), 0, Math.PI * 2);
        ctx.fill();
      }
    },
  };

  const chuvaHex = {
    iniciar: () => ({ colunas: [], tamanho: 14 }),
    redimensionar(estado, largura) {
      estado.tamanho = celular() ? 16 : 14;
      estado.colunas = Array.from(
        { length: Math.ceil(largura / estado.tamanho) },
        () => Math.floor(Math.random() * -40),
      );
    },
    intervaloMs: () => (celular() ? 90 : 70),
    estatico(ctx, estado, largura, altura) {
      ctx.clearRect(0, 0, largura, altura);
    },
    quadro(ctx, estado, largura, altura, agora, cor) {
      // Rastro: apaga um pouco do quadro anterior em vez de pintar o fundo
      // por cima, para o canvas continuar transparente em qualquer tema.
      ctx.globalCompositeOperation = "destination-out";
      ctx.fillStyle = "rgb(0 0 0 / .16)";
      ctx.fillRect(0, 0, largura, altura);
      ctx.globalCompositeOperation = "source-over";

      ctx.font = `${estado.tamanho}px "JetBrains Mono", ui-monospace, monospace`;
      estado.colunas.forEach((linha, i) => {
        const y = linha * estado.tamanho;
        if (y > 0) {
          ctx.fillStyle = Math.random() < 0.04 ? cor("texto", 0.5) : cor("primaria-clara", 0.35);
          ctx.fillText(HEX[(Math.random() * 16) | 0], i * estado.tamanho, y);
        }
        estado.colunas[i] = y > altura && Math.random() > 0.975 ? 0 : linha + 1;
      });
    },
  };

  const EFEITOS = { varredura, "chuva-hex": chuvaHex };

  function montar(canvas) {
    const efeito = EFEITOS[canvas.dataset.efeito];
    const pai = canvas.parentElement;
    if (!efeito || !pai) return;

    const ctx = canvas.getContext("2d");
    const estado = efeito.iniciar();
    let largura = 0;
    let altura = 0;
    let visivel = true;
    let pedido = 0;
    let ultimoQuadro = 0;

    function laco(agora) {
      pedido = requestAnimationFrame(laco);
      if (agora - ultimoQuadro < efeito.intervaloMs()) return;
      ultimoQuadro = agora;
      efeito.quadro(ctx, estado, largura, altura, agora, paleta());
    }

    function atualizar() {
      cancelAnimationFrame(pedido);
      pedido = 0;
      if (!largura) return;
      if (!movimentoLigado()) {
        efeito.estatico(ctx, estado, largura, altura, paleta());
        return;
      }
      if (visivel && !document.hidden) pedido = requestAnimationFrame(laco);
    }

    function medir() {
      const caixa = pai.getBoundingClientRect();
      largura = Math.max(1, Math.round(caixa.width));
      altura = Math.max(1, Math.round(caixa.height));
      canvas.width = Math.round(largura * DPR);
      canvas.height = Math.round(altura * DPR);
      canvas.style.width = `${largura}px`;
      canvas.style.height = `${altura}px`;
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
      efeito.redimensionar(estado, largura, altura);
      atualizar();
    }

    new ResizeObserver(medir).observe(pai);
    new IntersectionObserver(([entrada]) => {
      visivel = entrada.isIntersecting;
      atualizar();
    }).observe(canvas);
    document.addEventListener("visibilitychange", atualizar);
    window.addEventListener("spectra:movimento", atualizar);
    window.addEventListener("spectra:tema", () => { if (!movimentoLigado()) atualizar(); });
  }

  function iniciar() {
    document.querySelectorAll("canvas.fundo-animado[data-efeito]").forEach(montar);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
```

- [ ] **Step 4: Estilos do fundo**

Acrescentar a `rodape.css`, logo depois da seção `/* ─── 1) cursor / seleção */`:

```css
/* ─────────────────────────────────────────────── 1b) fundo da página */

/* Brilho estático nos cantos, num pseudo-elemento fixo (background-attachment
   fixed é ignorado ou pesa no Safari do celular). Custo zero de animação. */
body::before {
  content: "";
  position: fixed; inset: 0; z-index: -1;
  pointer-events: none;
  background:
    radial-gradient(1100px 620px at 0% 0%, var(--brilho-1), transparent 62%),
    radial-gradient(900px 560px at 100% 100%, var(--brilho-2), transparent 60%);
}

/* Efeitos animados (fundo.js). O canvas assume o tamanho do pai. */
.fundo-fixo {
  position: fixed; inset: 0; z-index: 0;
  pointer-events: none; overflow: hidden;
}
.fundo-animado { display: block; pointer-events: none; }
```

O `body { background: var(--base); }` de cada página continua como está: o fundo do `body` é propagado para a tela inteira (o `html` não tem fundo próprio), e o `body::before` com `z-index: -1` é pintado por cima dele e por baixo do conteúdo.

- [ ] **Step 5: Canvas nas telas**

`visao-geral.html` e `historico.html`: logo depois de `<body data-estado="seguro">`, inserir

```html

<div class="fundo-fixo" aria-hidden="true"><canvas class="fundo-animado" data-efeito="varredura"></canvas></div>
```

e, antes de `<script src="/static/menu.js" defer></script>`, inserir `<script src="/static/fundo.js" defer></script>`.

`aprender.html`: o mesmo, com `data-efeito="chuva-hex"`.

`inicio.html`: na seção "Por que usar" — trocar `<section class="border-b border-linha">` (a que contém "Por que usar nossos serviços?") por `<section class="relative overflow-hidden border-b border-linha">`; logo depois dela inserir

```html
    <div class="pointer-events-none absolute inset-0 opacity-70" aria-hidden="true">
      <canvas class="fundo-animado" data-efeito="chuva-hex"></canvas>
    </div>
```

e trocar a `<div class="mx-auto max-w-6xl px-5 py-16 sm:px-8 sm:py-20">` imediatamente seguinte por `<div class="relative mx-auto max-w-6xl px-5 py-16 sm:px-8 sm:py-20">`. Antes de `<script src="/static/caminhos.js"></script>`, inserir `<script src="/static/fundo.js" defer></script>`.

- [ ] **Step 6: Ativo no `app.py`**

Acrescentar `"fundo.js"` à lista de ativos das rotas `/inicio`, `/painel/visao-geral`, `/painel/historico` e `/painel/aprender` (ex.: `_pagina("historico.html", *_ATIVOS_PAINEL, "fundo.js", "historico.js", menu="historico")`).

- [ ] **Step 7: Rodar tudo**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 8: Conferir no navegador**

- `/painel/visao-geral` e `/painel/historico`: grade sutil com o feixe descendo e pontos acendendo, atrás dos quadros (visível pelas bordas translúcidas, sem atrapalhar a leitura).
- `/painel/aprender` e `/inicio` (rolar até "Por que usar"): chuva hexadecimal em baixa opacidade; no hero da home continuam só os cubos; `/painel` continua só com os caminhos.
- "Movimento parado": a varredura vira uma grade parada e a chuva some. Tema claro: as cores acompanham.
- Trocar de aba e voltar: no painel de desempenho do DevTools, não há quadros desenhados com a aba oculta.
- Nenhum erro no console.

- [ ] **Step 9: Commit**

```bash
git add src/spectra_link_guard/web/static/fundo.js src/spectra_link_guard/web/static/rodape.css \
  src/spectra_link_guard/web/static/visao-geral.html src/spectra_link_guard/web/static/historico.html \
  src/spectra_link_guard/web/static/aprender.html src/spectra_link_guard/web/static/inicio.html \
  src/spectra_link_guard/web/app.py tests/test_frontend.py
git commit -m "$(cat <<'EOF'
Efeitos de fundo: varredura e chuva hexadecimal

fundo.js desenha a varredura (Visão geral e Histórico) e a chuva
hexadecimal (Aprender e parte de baixo da home), com cores dos tokens,
pausa fora da tela e versão estática com movimento parado. Brilho
estático nos cantos da página em todas as telas.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Responsividade (celular, tablet, notebook)

**Files:**
- Modify: `src/spectra_link_guard/web/parciais/menu.html` (barra superior, barra de abas, gaveta)
- Modify: `src/spectra_link_guard/web/static/menu.js` (gaveta)
- Modify: `src/spectra_link_guard/web/static/laudo.css` (bloco responsivo)
- Modify: `src/spectra_link_guard/web/static/rodape.css` (acessibilidade acima da barra de abas)
- Modify: `src/spectra_link_guard/web/static/animacoes.css` (nomes de view transition do celular)
- Modify: `src/spectra_link_guard/web/static/laudo.js` (`data-rotulo` na checklist)
- Modify: todas as páginas (`viewport-fit=cover`)
- Modify: `tests/test_frontend.py`, `tests/test_web.py`

**Interfaces:**
- Consumes: `data-menu`/`aria-current` (Task 3), `[data-conta*]`/`[data-sair]` (Task 3), `--ease-saida` (Task 4), `data-rotulo` nas células do histórico (Task 4).
- Produces: `.topo-movel`, `.barra-abas`, `.aba-item`, `<dialog class="gaveta" id="gaveta-mais">`, `[data-abrir-mais]`, `[data-fechar-gaveta]`; variável `--abas-h`.

- [ ] **Step 1: Escrever os testes**

Acrescentar a `tests/test_frontend.py`:

```python


def test_toda_pagina_usa_viewport_fit_cover():
    for nome in PAGINAS:
        assert 'content="width=device-width, initial-scale=1, viewport-fit=cover"' in _html(nome), nome


def test_menu_tem_navegacao_de_celular():
    from spectra_link_guard.web.app import PARCIAIS

    menu = (PARCIAIS / "menu.html").read_text(encoding="utf-8")
    assert '<nav class="barra-abas"' in menu
    assert menu.count('class="aba-item"') == 4
    assert '<dialog class="gaveta" id="gaveta-mais"' in menu
    assert menu.count("data-abrir-mais") == 2
```

Acrescentar a `tests/test_web.py`:

```python


def test_item_da_gaveta_tambem_fica_ativo(cliente):
    entrar(cliente)
    html = cliente.get("/painel/aprender").text
    assert html.count('data-menu="aprender" aria-current="page"') == 2  # menu lateral + gaveta
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_frontend.py tests/test_web.py -q`
Expected: FAIL nos três testes novos.

- [ ] **Step 3: Navegação de celular no parcial**

Em `src/spectra_link_guard/web/parciais/menu.html`, depois do `</aside>`, acrescentar:

```html

<header class="topo-movel">
  <a class="chancela" href="/inicio">
    <span class="chancela-marca" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
    </span>
    <span class="chancela-nome">SPECTRA</span>
  </a>
  <button type="button" class="topo-conta" data-abrir-mais aria-controls="gaveta-mais" aria-expanded="false" aria-label="Abrir o menu da conta">
    <span class="conta-inicial" data-conta-inicial aria-hidden="true"></span>
  </button>
</header>

<nav class="barra-abas" aria-label="Navegação rápida">
  <a class="aba-item" href="/painel" data-menu="verificar">
    <i data-lucide="search-check" aria-hidden="true"></i><span>Verificar</span>
  </a>
  <a class="aba-item" href="/painel/visao-geral" data-menu="visao-geral">
    <i data-lucide="layout-dashboard" aria-hidden="true"></i><span>Visão geral</span>
  </a>
  <a class="aba-item" href="/painel/historico" data-menu="historico">
    <i data-lucide="history" aria-hidden="true"></i><span>Histórico</span>
  </a>
  <button type="button" class="aba-item" data-abrir-mais aria-controls="gaveta-mais" aria-expanded="false">
    <i data-lucide="menu" aria-hidden="true"></i><span>Mais</span>
  </button>
</nav>

<dialog class="gaveta" id="gaveta-mais" aria-labelledby="gaveta-titulo">
  <div class="gaveta-topo">
    <h2 class="gaveta-titulo" id="gaveta-titulo">Mais</h2>
    <button type="button" class="gaveta-fechar" data-fechar-gaveta aria-label="Fechar">
      <i data-lucide="x" aria-hidden="true"></i>
    </button>
  </div>
  <nav class="gaveta-menu" aria-label="Outras páginas">
    <a class="gaveta-item" href="/painel/aprender" data-menu="aprender">
      <i data-lucide="book-open" aria-hidden="true"></i>Aprender
    </a>
  </nav>
  <div class="gaveta-conta" data-conta hidden>
    <span class="conta-inicial" data-conta-inicial aria-hidden="true"></span>
    <span class="conta-nome" data-conta-nome></span>
    <button type="button" class="conta-sair" data-sair>
      <i data-lucide="log-out" aria-hidden="true"></i><span>Sair</span>
    </button>
  </div>
</dialog>
```

- [ ] **Step 4: Gaveta no `menu.js`**

Em `src/spectra_link_guard/web/static/menu.js`, antes do `})();` final, acrescentar:

```js

  const gaveta = document.getElementById("gaveta-mais");
  const abridores = document.querySelectorAll("[data-abrir-mais]");
  if (gaveta && typeof gaveta.showModal === "function") {
    let ultimoAbridor = null;

    abridores.forEach((botao) => botao.addEventListener("click", () => {
      ultimoAbridor = botao;
      gaveta.showModal();
      abridores.forEach((b) => b.setAttribute("aria-expanded", "true"));
    }));

    gaveta.addEventListener("close", () => {
      abridores.forEach((b) => b.setAttribute("aria-expanded", "false"));
      if (ultimoAbridor) ultimoAbridor.focus();
    });

    // Toque fora da gaveta (no fundo escurecido) fecha. Compara coordenadas
    // porque o clique no ::backdrop chega com o próprio <dialog> como alvo.
    gaveta.addEventListener("click", (evento) => {
      const caixa = gaveta.getBoundingClientRect();
      const fora = evento.clientY < caixa.top || evento.clientY > caixa.bottom
        || evento.clientX < caixa.left || evento.clientX > caixa.right;
      if (fora) gaveta.close();
    });

    gaveta.querySelector("[data-fechar-gaveta]").addEventListener("click", () => gaveta.close());

    // Se a tela atual mora dentro da gaveta, a aba "Mais" aparece ativa.
    if (gaveta.querySelector('[aria-current="page"]')) {
      document.querySelector(".barra-abas [data-abrir-mais]")?.classList.add("ativo");
    }
  }
```

- [ ] **Step 5: Bloco responsivo do `laudo.css`**

Em `src/spectra_link_guard/web/static/laudo.css`, trocar a seção `/* ─── responsivo */` inteira — o comentário, o `@media (max-width: 1180px) { … }` e o `@media (max-width: 860px) { … }` — por:

```css
/* ───────────────────────────────────────────────────── responsivo
 *
 * ≥ 1024: menu lateral completo · 600–1023: menu só de ícones ·
 * ≤ 599: barra superior compacta + barra de abas embaixo ·
 * ≥ 1440: conteúdo com largura máxima.
 */

.topo-movel, .barra-abas { display: none; }

@media (min-width: 1440px) {
  .grade { max-width: 1320px; margin-inline: auto; }
}

@media (max-width: 1180px) {
  .q-sinais { grid-column: span 12; }
  .faixa { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 1023px) {
  :root { --trilho-l: 72px; }
  .trilho { padding: 16px 6px; align-items: center; gap: 22px; }
  .trilho .chancela-texto, .trilho .conta-texto, .trilho .conta-sair-rotulo { display: none; }
  .menu { align-items: center; }
  .menu-item {
    flex-direction: column; gap: 4px;
    width: 60px; padding: 8px 4px;
    font-size: .6rem; line-height: 1.2; text-align: center;
  }
  .menu-icone { width: 20px; height: 20px; }
  .trilho .conta { flex-direction: column; gap: 6px; padding: 8px 6px; margin-bottom: 0; }
  .trilho .conta-sair { margin-left: 0; min-width: 44px; min-height: 44px; justify-content: center; }
}

@media (max-width: 860px) {
  .barra { position: static; height: auto; padding: var(--vao); flex-wrap: wrap; }
  .busca { max-width: none; flex-basis: 100%; }
  .barra-estado { margin-left: 0; }
  .subnav-analise { top: 0; }
  .busca button, .busca input, .amostra, .hist-busca, .hist-filtro { min-height: 44px; }
  .cadeia { flex-direction: column; }
  .elo { margin: 0 0 24px; width: 100%; }
  .elo::after { right: auto; left: 24px; top: auto; bottom: -24px; width: 1px; height: 24px; }
  .hist-controles { margin-left: 0; width: 100%; }
  .hist-busca { flex: 1; min-width: 0; }
}

@media (max-width: 599px) {
  :root { --trilho-l: 0px; --abas-h: 60px; --vao: 12px; }
  .app { flex-direction: column; }
  .trilho { display: none; }

  .topo-movel {
    position: sticky; top: 0; z-index: 25;
    display: flex; align-items: center; justify-content: space-between;
    min-height: 52px;
    padding: env(safe-area-inset-top) 10px 0 14px;
    background: color-mix(in srgb, var(--base) 85%, transparent);
    -webkit-backdrop-filter: blur(14px);
    backdrop-filter: blur(14px);
    border-bottom: 1px solid var(--linha);
  }
  .topo-movel .chancela-marca { width: 30px; height: 30px; }
  .topo-conta {
    width: 44px; height: 44px;
    display: grid; place-items: center;
    border: 0; background: none; cursor: pointer;
  }
  .topo-conta:focus-visible { outline: 2px solid var(--primaria); outline-offset: 2px; }
  .subnav-analise { top: 52px; }

  .barra-abas {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 40;
    display: grid; grid-template-columns: repeat(4, 1fr);
    height: calc(var(--abas-h) + env(safe-area-inset-bottom));
    padding-bottom: env(safe-area-inset-bottom);
    background: color-mix(in srgb, var(--base-2) 92%, transparent);
    -webkit-backdrop-filter: blur(14px);
    backdrop-filter: blur(14px);
    border-top: 1px solid var(--linha);
  }
  .aba-item {
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;
    min-height: 44px; padding: 0;
    border: 0; background: none;
    color: var(--texto-3);
    font-family: var(--fonte-corpo); font-size: .64rem; text-decoration: none;
    cursor: pointer;
  }
  .aba-item svg { width: 20px; height: 20px; }
  .aba-item[aria-current="page"], .aba-item.ativo { color: var(--primaria-clara); }
  .aba-item:focus-visible { outline: 2px solid var(--primaria); outline-offset: -4px; }

  .corpo { margin-left: 0; padding-bottom: calc(var(--abas-h) + env(safe-area-inset-bottom)); }
  .faixa, .faixa-checklist { grid-template-columns: 1fr; }
  .q-hist-resumo, .q-hist-lista { grid-column: span 12; }
  .vg-kpis { grid-template-columns: repeat(2, 1fr); }
  .hist-controles { flex-direction: column; align-items: stretch; }

  /* Tabelas viram cards: cada linha é um bloco; o cabeçalho vira rótulo. */
  .tabela-checklist thead, .tabela-hist thead { display: none; }
  .tabela-checklist tr, .tabela-hist tr {
    display: block; padding: 10px 0;
    border-bottom: 1px solid var(--linha);
  }
  .tabela-checklist tr:last-child, .tabela-hist tr:last-child { border-bottom: none; }
  .tabela-checklist td, .tabela-hist td {
    display: flex; justify-content: space-between; align-items: center; gap: 14px;
    padding: 4px 0; border: 0; text-align: right;
  }
  .tabela-checklist td::before, .tabela-hist td::before {
    content: attr(data-rotulo);
    flex: none; text-align: left;
    font-family: var(--fonte-mono); font-size: .58rem;
    letter-spacing: .1em; text-transform: uppercase; color: var(--texto-3);
  }
  .tabela-checklist td[data-rotulo="Explicação"] { display: block; text-align: left; }
  .tabela-checklist td[data-rotulo="Explicação"]::before { display: block; margin-bottom: 2px; }
  .hist-apagar { width: 44px; height: 44px; }

  .copiloto-caixa {
    right: 12px;
    bottom: calc(var(--abas-h) + env(safe-area-inset-bottom) + 12px);
  }
}

/* Gaveta "Mais" (celular): folha que sobe da borda de baixo. */
.gaveta {
  width: 100%; max-width: 100%; max-height: 80vh;
  margin: auto 0 0;
  padding: 16px 16px calc(16px + env(safe-area-inset-bottom));
  border: 0; border-top: 1px solid var(--linha-forte);
  background: var(--base-2); color: var(--texto);
}
.gaveta::backdrop { background: rgb(var(--base-rgb) / .7); }
.gaveta[open] { animation: gaveta-subir .26s var(--ease-saida) both; }
@keyframes gaveta-subir { from { transform: translateY(100%); } to { transform: none; } }
.gaveta-topo { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.gaveta-titulo { font-size: 1rem; }
.gaveta-fechar {
  width: 44px; height: 44px; display: grid; place-items: center;
  border: 0; background: none; color: var(--texto-2); cursor: pointer;
}
.gaveta-fechar svg { width: 20px; height: 20px; }
.gaveta-menu { display: grid; gap: 2px; }
.gaveta-item {
  display: flex; align-items: center; gap: 12px;
  min-height: 48px; padding: 0 10px;
  color: var(--texto); text-decoration: none; font-size: .95rem;
}
.gaveta-item svg { width: 20px; height: 20px; color: var(--texto-3); }
.gaveta-item[aria-current="page"] { color: var(--primaria-clara); background: var(--base-3); }
.gaveta-item:focus-visible, .gaveta-fechar:focus-visible { outline: 2px solid var(--primaria); outline-offset: -2px; }
.gaveta-conta {
  display: flex; align-items: center; gap: 10px;
  margin-top: 12px; padding-top: 12px;
  border-top: 1px solid var(--linha);
}
```

- [ ] **Step 6: Acessibilidade acima da barra de abas e transições do celular**

Em `rodape.css`, trocar `@media (max-width: 640px) { .a11y-caixa { left: 12px; bottom: 12px; } }` por:

```css
@media (max-width: 640px) { .a11y-caixa { left: 12px; bottom: 12px; } }
@media (max-width: 599px) {
  body:has(.barra-abas) .a11y-caixa {
    bottom: calc(var(--abas-h, 60px) + env(safe-area-inset-bottom) + 12px);
  }
}
```

Em `animacoes.css`, logo abaixo de `.trilho { view-transition-name: trilho; }`, acrescentar:

```css
.topo-movel { view-transition-name: topo-movel; }
.barra-abas { view-transition-name: barra-abas; }
```

- [ ] **Step 7: Rótulos da checklist e `viewport-fit`**

Em `laudo.js`, dentro de `renderChecklist`, depois de cada `td` criado:

```js
    tdRotulo.dataset.rotulo = "Critério";
```
(logo após `const tdRotulo = …`),
```js
    tdResultado.dataset.rotulo = "Resultado";
```
(logo após `const tdResultado = elemento("td");`) e
```js
    tdMotivo.dataset.rotulo = "Explicação";
```
(logo após `const tdMotivo = …`).

Em `inicio.html`, `laudo.html`, `historico.html`, `aprender.html`, `privacidade.html` e `termos.html`, trocar `<meta name="viewport" content="width=device-width, initial-scale=1">` por:

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

- [ ] **Step 8: Rodar tudo**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 9: Conferir no navegador, largura por largura**

Para cada largura 320, 360, 390, 414, 768, 1024, 1280, 1440 e 1920 (preview: `resize_window` com largura × 800), em cada tela (`/inicio`, `/painel` com um laudo aberto, `/painel/visao-geral`, `/painel/historico`, `/painel/aprender`, `/privacidade`, `/termos`), rodar no console:

```js
({
  largura: innerWidth,
  rolagemHorizontal: document.documentElement.scrollWidth > innerWidth,
  abas: getComputedStyle(document.querySelector(".barra-abas") || document.body).display,
  trilho: document.querySelector(".trilho")?.getBoundingClientRect().width ?? null,
})
```

Expected em todas: `rolagemHorizontal: false`. Nas telas do painel: até 599px, `abas: "grid"` e `trilho: 0`; de 600 a 1023px, `abas: "none"` e `trilho: 72`; a partir de 1024px, `trilho: 236`. Em 390px: tocar em "Mais" abre a gaveta (Esc, o X e o toque fora fecham, e o foco volta ao botão); em `/painel/aprender`, a aba "Mais" aparece ativa. A checklist e o histórico aparecem como cards. Os botões do copiloto e de acessibilidade ficam acima da barra de abas. Voltar o viewport para `desktop` no fim.

- [ ] **Step 10: Commit**

```bash
git add src/spectra_link_guard/web/parciais/menu.html src/spectra_link_guard/web/static/menu.js \
  src/spectra_link_guard/web/static/laudo.css src/spectra_link_guard/web/static/rodape.css \
  src/spectra_link_guard/web/static/animacoes.css src/spectra_link_guard/web/static/laudo.js \
  src/spectra_link_guard/web/static/*.html tests/test_frontend.py tests/test_web.py
git commit -m "$(cat <<'EOF'
Responsividade de 320px a 1920px

Celular: barra superior compacta, barra de abas fixa embaixo e gaveta
"Mais"; tabelas viram cards; áreas seguras do iPhone respeitadas.
Tablet e notebook pequeno: menu lateral só de ícones. Telas largas:
conteúdo com largura máxima. Nenhuma tela rola na horizontal.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Verificação final e documentação

**Files:**
- Modify: `README.md`, `COMO-CONTINUAR.md`
- Modify: `docs/superpowers/specs/2026-10-08-fundacao-visual-design.md` (nota sobre `cubos.js`)

**Interfaces:**
- Consumes: tudo das Tasks 1–7.
- Produces: documentação atualizada; branch pronta para o `/finishing-a-development-branch`.

- [ ] **Step 1: Suíte completa**

Run: `python -m pytest -q`
Expected: PASS, sem testes pulados além dos que já eram pulados.

- [ ] **Step 2: Passada final no navegador**

- Temas escuro, claro e alto contraste em todas as telas (inclusive `/inicio`): texto legível, nada com a cor do fundo.
- "Movimento parado" em todas as telas: nada se mexe, nada some.
- Dois usuários em sequência (janela normal e anônima): nenhum vê dado do outro em Histórico ou Visão geral.
- Navegação só por teclado (Tab/Shift+Tab/Enter/Esc) em `/painel` e `/painel/historico`: foco sempre visível, diálogo e gaveta prendem e devolvem o foco.
- Console sem erros em todas as telas.

- [ ] **Step 3: README**

Em `README.md`, na tabela "Endereço | O que é" da seção "App web", trocar as linhas de `/painel`, `GET /api/painel` e `DELETE /api/painel/{id}` por:

```markdown
| `http://localhost:8000/painel` | Verificar um link. Exige sessão; sem ela volta para `/inicio` |
| `http://localhost:8000/painel/visao-geral` | Dashboard: indicadores e gráficos das suas análises |
| `http://localhost:8000/painel/historico` | Histórico com busca, filtro e exclusão |
| `http://localhost:8000/painel/aprender` | Guia de phishing e glossário |
| `GET /api/painel` | Indicadores do usuário logado (401 sem sessão) |
| `GET /api/painel/historico` | Todas as análises do usuário (até 500) |
| `GET /api/painel/estatisticas` | Números agregados da Visão geral |
| `DELETE /api/painel/{id}` | Remove uma análise sua (404 se não existe ou é de outra pessoa) |
| `DELETE /api/painel` | Apaga todo o seu histórico |
```

E trocar o parágrafo **"Privacidade do histórico:"** por:

```markdown
**Privacidade do histórico:** cada usuário só vê o próprio histórico, que
fica no SQLite (tabela `analises`, até 500 por conta, apagadas junto com a
conta). Guarda-se host, domínio, nota, nível, horário e os códigos dos
sinais de risco — a URL completa não é retida, porque caminho e query podem
conter token de sessão ou dados pessoais. Análises feitas sem login (CLI,
integrações) não são guardadas.
```

- [ ] **Step 4: COMO-CONTINUAR**

Em `COMO-CONTINUAR.md`, na seção 5, acrescentar ao fim da lista numerada:

```markdown
12. Fundação visual (branch `fundacao-visual`): fundo `#070B14` com tokens
    únicos (`static/tokens.css`), histórico por usuário no SQLite, tela
    **Visão geral** (`/painel/visao-geral`), menu/rodapé/acessibilidade
    como parciais (`web/parciais/`), animações, efeitos de fundo e
    responsividade de 320px a 1920px.
```

Na tabela "Mapa rápido", acrescentar:

```markdown
| Cores (todas) | `src/spectra_link_guard/web/static/tokens.css` |
| Menu, rodapé e acessibilidade (um lugar só) | `src/spectra_link_guard/web/parciais/` |
| Histórico por usuário e estatísticas | `src/spectra_link_guard/web/analises.py` |
```

E, na seção 6, trocar a frase "mesmo bloco de rodapé repetido nos 6 arquivos, não há template engine no projeto" por "agora num lugar só: `web/parciais/rodape.html`".

- [ ] **Step 5: Nota no spec**

Em `docs/superpowers/specs/2026-10-08-fundacao-visual-design.md`, na lista de "Cores fixas espalhadas que viram token", trocar "e cores em `cubos.js`" por "(`cubos.js` mantém sua paleta: só usa cores de marca, nenhum neutro)".

- [ ] **Step 6: Commit**

```bash
git add README.md COMO-CONTINUAR.md docs/superpowers/specs/2026-10-08-fundacao-visual-design.md
git commit -m "$(cat <<'EOF'
Documenta a fundação visual e o novo contrato do histórico

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 7: Integração**

Invocar `superpowers:finishing-a-development-branch` (pedido do usuário) para decidir como integrar `fundacao-visual` na `main`.
