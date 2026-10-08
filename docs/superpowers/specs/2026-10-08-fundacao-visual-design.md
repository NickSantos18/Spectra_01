# Fundação visual do Spectra — design

**Data:** 2026-10-08
**Sub-projeto:** 1 de 5 (fundação visual → perfil → fórum → blog → chat)
**Branch:** `fundacao-visual`

## Objetivo

Trocar o fundo do site para azul quase preto, deixar todas as telas
responsivas (320px a 1920px), tornar a interface mais dinâmica (dashboard com
gráficos, micro-interações, transições, efeitos de fundo) e preparar a base
sobre a qual fórum, blog, perfil e chat serão construídos.

## Fora de escopo

- Fórum, blog, perfil com foto/IP e chat (sub-projetos 2 a 5, cada um com
  seu próprio spec).
- "Home mais viva" (demo interativa na home) — não escolhida.
- Efeitos "constelação" e "aurora" — não escolhidos.
- Trocar o stack de front-end (framework, build com Node) — descartado na
  escolha de abordagem.

## Decisões tomadas com o usuário

| Tema | Decisão |
|---|---|
| Organização | 5 sub-projetos, um por vez; este é o primeiro |
| Fundo | `#070B14` ("Noite") |
| Abordagem | tokens unificados (`tokens.css` como fonte única de cor) |
| "Dinâmico" | dashboard com gráficos + micro-interações/transições + efeitos de fundo |
| Efeitos de fundo | **Varredura** e **Chuva hexadecimal** |
| Git | repositório próprio em `spectra 01/`, branch por sub-projeto |

---

## 1. Tokens de cor

Novo arquivo `web/static/tokens.css`, carregado **antes** de qualquer outro
CSS em todas as páginas. É o único lugar do projeto onde cores neutras e de
marca são definidas.

Os nomes das variáveis são os que o `laudo.css` já usa (evita renomear
centenas de usos). Para o Tailwind da home, cada cor também existe como
triplet RGB (`--base-rgb: 7 11 20`), porque o Tailwind precisa dos canais
separados para os modificadores de opacidade (`bg-base/95`).

### Tema escuro (padrão)

| Variável | Valor | Nome no Tailwind | Uso |
|---|---|---|---|
| `--base` | `#070B14` | `base` | fundo da página |
| `--base-2` | `#0C1220` | `sup` | cards, quadros |
| `--base-3` | `#121A2B` | `sup-2` | campos, elementos elevados |
| `--base-4` | `#18223A` | `sup-3` | hover |
| `--linha` | `#1C2638` | `linha` | bordas |
| `--linha-forte` | `#2A3852` | `linha-forte` | bordas fortes |
| `--texto` | `#E7EEF0` | `txt` | texto principal (16.7:1) |
| `--texto-2` | `#9FB0C8` | `txt-2` | texto secundário (8.9:1) |
| `--texto-3` | `#7E8DA6` | `txt-3` | texto terciário (5.9:1) |
| `--primaria` | `#118E94` | `marca` | teal da marca |
| `--primaria-clara` | `#3FB6BB` | `marca-claro` | teal em texto/destaque (8.1:1) |
| `--secundaria` | `#5B9986` | `sage` | sálvia |
| `--terciaria` | `#FFFC0E` | `amarelo` | amarelo pontual |
| `--perigo` | `#FF4438` | `perigo` | estado crítico |
| `--sobre-primaria` | `#04191A` | `sobre-marca` | texto sobre botão teal (4.6:1) |

Contrastes medidos contra `#070B14`.

### Tema claro (`:root[data-tema="claro"]`)

`--base #F3F6FA`, `--base-2 #FFFFFF`, `--base-3 #EAF0F6`, `--base-4 #DFE7F0`,
`--linha #D5DEE8`, `--linha-forte #BCC9D8`, `--texto #0D1626`,
`--texto-2 #3A4A63`, `--texto-3 #56657E`, e **`--primaria-clara #0B6E73`**
(o teal `#118E94` como texto em branco dá 3.9:1, abaixo do mínimo de 4.5:1;
`#0B6E73` dá 6.0:1).

### Alto contraste (`:root[data-alto-contraste="on"]`)

Mesma regra que existe hoje (`--linha` = `--linha-forte`, `--texto-2` e
`--texto-3` = `--texto`, bordas e foco mais grossos), movida de
`rodape.css` para `tokens.css`.

### Consequências

- `rodape.css` perde o bloco de tema claro com `!important` sobre classes do
  Tailwind.
- O `tailwind.config` da home aponta cada cor para
  `rgb(var(--X-rgb) / <alpha-value>)` em vez de hex fixo.
- Cores fixas espalhadas que viram token: `body{background:#0f171a}` e
  autofill em `inicio.html`; o degradê da manchete (`.letra`); `#04191a` em
  `laudo.css`; anéis de foco `rgba(17,142,148,…)`; cores do polígrafo em
  `laudo.js`; `COR_NIVEL` em `historico.js` (`cubos.js` mantém sua paleta: só usa cores
  de marca, nenhum neutro). Gráficos e
  canvas leem os tokens com `getComputedStyle`.
- **Teste de regressão:** nenhum arquivo em `web/static/` (exceto
  `tokens.css`) pode conter os neutros antigos `#0f171a`, `#131e22`,
  `#18262b`, `#22353b`, `#2e474f`, `#9fb3b8`, `#85999f` (sem diferenciar
  maiúsculas).
- `acessibilidade.js` dispara o evento `spectra:tema` (com o tema no
  `detail`) a cada troca, para gráficos e canvas se redesenharem.

## 2. Navegação, partes compartilhadas e responsividade

### Partes compartilhadas (parciais)

Nova pasta `web/parciais/` (fora de `static/`, não é servida diretamente):

- `menu.html` — menu lateral, barra de abas inferior, gaveta "Mais" e bloco
  da conta;
- `rodape.html` — o rodapé que hoje está copiado em 6 arquivos;
- `acessibilidade.html` — o painel flutuante que hoje está copiado em 6
  arquivos.

As páginas trocam os blocos duplicados por marcadores:
`<!--PARCIAL:menu-->`, `<!--PARCIAL:rodape-->`,
`<!--PARCIAL:acessibilidade-->`.

`_pagina(arquivo, *ativos, menu=None)` em `app.py`:
1. substitui cada marcador pelo conteúdo do parcial;
2. se `menu` for informado (ex.: `"visao-geral"`), marca o item com
   `data-menu="visao-geral"` acrescentando `aria-current="page"`;
3. faz o cache-busting `?v=` como hoje.

O estilo de item ativo passa a ser `[aria-current="page"]` (não mais a
classe `.ativo`). `pyproject.toml` passa a incluir `parciais/*` no
package-data.

Script compartilhado `web/static/menu.js`: preenche o bloco da conta
(`/api/auth/eu`), liga "Sair" e abre/fecha a gaveta "Mais" (Esc fecha, foco
volta ao botão). O código equivalente sai de `laudo.js`, `historico.js` e do
`<script>` inline de `aprender.html`.

"Fontes consultadas" sai do menu lateral (que agora é compartilhado) e vai
para a tela Verificar, numa linha abaixo da barra de busca. A marcação
(`.fonte[data-fonte=…]`) não muda, então `laudo.js` continua funcionando.

### Itens do menu

Verificar (`/painel`) · Visão geral (`/painel/visao-geral`) · Histórico
(`/painel/historico`) · Aprender (`/painel/aprender`). Os sub-projetos
seguintes acrescentam itens em `menu.html`.

### Faixas de largura

| Largura | Navegação |
|---|---|
| ≤ 599px | barra superior compacta (logo + inicial da conta); **barra de abas fixa embaixo**: Verificar · Visão geral · Histórico · Mais (gaveta com Aprender, conta, sair) |
| 600–1023px | menu lateral só com ícones (72px), rótulo pequeno sob o ícone |
| ≥ 1024px | menu lateral completo (236px), como hoje |
| ≥ 1440px | conteúdo com largura máxima de 1320px, centralizado |

### Regras gerais

- Sem rolagem horizontal a partir de 320px.
- Alvos de toque ≥ 44px.
- Em ≤ 599px, tabelas (`.tabela-checklist`, `.tabela-hist`) viram cards
  empilhados (cada linha é um card; o cabeçalho vira rótulo via
  `data-rotulo`).
- Gráficos ficam em containers com altura definida e
  `maintainAspectRatio: false`.
- `env(safe-area-inset-*)` na barra de abas e nos botões flutuantes.
- Em ≤ 599px, copiloto (direita) e acessibilidade (esquerda) sobem acima
  da barra de abas. Uma posição arrastada salva fora da tela é reencaixada
  (já existe).
- `/inicio` e páginas legais não usam `menu.html`; usam rodapé e
  acessibilidade.

## 3. Histórico por usuário e Visão geral

### Problema que corrige

O `_Historico` de `app.py` é um objeto global em memória: todos os usuários
veem as análises uns dos outros, e tudo some ao reiniciar.

### Dados

Novo módulo `web/analises.py`, usando a conexão de `auth/bd.py`:

```sql
CREATE TABLE IF NOT EXISTS analises (
    id          TEXT PRIMARY KEY,            -- 12 hex, como hoje
    usuario_id  TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    host        TEXT,
    dominio     TEXT,
    risco       INTEGER NOT NULL,
    nivel       TEXT NOT NULL,
    codigos     TEXT NOT NULL DEFAULT '[]',  -- JSON: sinais com severidade != info
    quando      TEXT NOT NULL                -- ISO 8601 UTC
);
CREATE INDEX IF NOT EXISTS idx_analises_usuario_quando ON analises(usuario_id, quando);
```

- A URL completa **não** é guardada (regra do README).
- `codigos` guarda só sinais com severidade diferente de `info`, para o
  gráfico mostrar riscos e não sinais neutros (`sem_spf`,
  `dominio_estabelecido`…).
- Limite: 500 por usuário; ao inserir a 501ª, a mais antiga é apagada.

Funções: `registrar(usuario_id, relatorio) -> str`,
`listar(usuario_id) -> list[dict]`, `remover(usuario_id, id) -> bool`,
`remover_todas(usuario_id) -> int`, `resumo(usuario_id) -> dict`,
`estatisticas(usuario_id, dias=30, hoje=None) -> dict`.

Itens devolvidos por `listar`/`resumo` têm exatamente
`{id, host, dominio, risco, nivel, quando}` — sem `codigos`.

Nomes legíveis dos sinais: dicionário `ROTULOS_SINAIS` em
`web/rotulos_sinais.py`, cobrindo todos os códigos de achado do analisador
(sintaxe, TLS, reputação, rede). Código sem rótulo aparece como o próprio
código.

### Estatísticas

```json
{
  "total": 0, "perigosos": 0, "risco_medio": 0, "pct_seguras": 0,
  "por_nivel": {"seguro": 0, "baixo": 0, "atencao": 0, "alto": 0, "critico": 0},
  "por_dia": [{"dia": "2026-10-08", "total": 0, "risco_medio": 0}],
  "sinais_frequentes": [{"codigo": "tld_de_risco", "rotulo": "Extensão de domínio de risco", "vezes": 0}]
}
```

- `perigosos` = alto + crítico; `pct_seguras` = (seguro + baixo) / total,
  inteiro de 0 a 100 (0 se total for 0).
- `risco_medio` arredondado para inteiro.
- `por_dia`: exatamente `dias` entradas, do mais antigo a hoje (UTC),
  preenchidas com zero.
- `sinais_frequentes`: top 8 por contagem decrescente, empate por código
  em ordem alfabética.

### API

| Rota | Sem sessão | Com sessão |
|---|---|---|
| `POST /api/analisar` | analisa, **não salva** | analisa e salva no histórico do usuário |
| `GET /api/painel` | 401 | resumo do usuário (mesmo formato de hoje) |
| `GET /api/painel/historico` | 401 | `{"itens": [...]}` do usuário |
| `GET /api/painel/estatisticas` | 401 | estatísticas acima |
| `DELETE /api/painel/{id}` | 401 | 204 se é do usuário; **404** se não existe ou é de outro |
| `DELETE /api/painel` | 401 | 204, apaga todo o histórico do usuário |

401 sai pelo handler existente (`{"erro": "..."}`). `_Historico` e a
instância global `historico` são removidos.

### Tela "Visão geral" — `/painel/visao-geral`

Exige login, como as outras do painel.
- 4 indicadores com contador animado: total, perigosas, risco médio,
  % seguras.
- Gráfico combinado dos últimos 30 dias: barras (análises por dia) + linha
  (risco médio).
- Rosca com a distribuição por veredito.
- Barras horizontais com os 8 sinais mais frequentes.
- Estado vazio (total = 0): mensagem e botão "Verificar meu primeiro link"
  → `/painel`.
- Skeleton enquanto carrega; cores dos tokens; redesenha no evento
  `spectra:tema`; sem animação de gráfico com movimento parado.

### Histórico

Passa a usar a API por usuário. Mantém busca, filtro, lixeira e rosca;
ganha **"Apagar tudo"** com confirmação (`<dialog>` acessível) e link para
a Visão geral.

## 4. Animações, transições e efeitos de fundo

Regra geral: tudo obedece a `data-movimento` (interruptor existente +
`prefers-reduced-motion`). Com movimento parado, nada se mexe e nada fica
invisível esperando animação. Animações só usam `transform` e `opacity`.

### Micro-interações — `animacoes.css` + `animacoes.js`

- `[data-revelar]`: entrada ao rolar (generaliza o script inline da home,
  que sai de `inicio.html`).
- Hover em `.quadro` e cards: sobe 2px, borda teal sutil. `:active` em
  botões: `scale(.97)`.
- Skeleton: classe `.esqueleto` com brilho deslizante.
- Contador: `animarNumero(elemento, valor, duracaoMs)` com easing
  cúbico; usado nos indicadores e no número do medidor de risco.
- Durante a análise: LEDs de "fontes consultadas" pulsam (`.fonte.pulsando`)
  e o quadro do veredito recebe `.varrendo` — um feixe da Varredura em CSS
  percorre o quadro de cima a baixo — removido quando o laudo chega.
  Nenhuma etapa simulada.
- Toast: `avisarToast(texto, tipo)` (`aria-live="polite"`), usado no
  histórico (apagar) e em erros de rede.

### Transição entre páginas

`@view-transition { navigation: auto; }`. Menu lateral e barra de abas com
`view-transition-name` próprio (ficam parados); conteúdo faz fade. Com
movimento parado, as animações dos pseudo-elementos de view transition são
zeradas. Navegador sem suporte navega normalmente.

### Efeitos de fundo — `fundo.js`

Inicializa automaticamente todo `<canvas data-efeito="varredura">` ou
`<canvas data-efeito="chuva-hex">`, dimensionando o canvas pelo elemento pai.

| Tela | Efeito |
|---|---|
| Home — hero | cubos (sem mudança) |
| Home — seções abaixo do hero | chuva hexadecimal |
| Verificar | caminhos (sem mudança) + feixe transitório durante a análise |
| Visão geral, Histórico | varredura |
| Aprender | chuva hexadecimal |
| Privacidade, Termos | nenhum |

- **Varredura:** grade (passo de 22px) em `--linha-forte` com baixa
  opacidade; feixe horizontal em `--primaria` descendo em loop; pontos
  aleatórios acendem em `--terciaria`/`--perigo` quando o feixe passa e
  apagam em 1,5s.
- **Chuva hexadecimal:** colunas de `0-9A-F` em JetBrains Mono, cor
  `--primaria-clara` com opacidade ~0,35 (raros caracteres em `--texto`),
  rastro por sobreposição da cor `--base`.
- **Desempenho:** DPR limitado a 1,5; pausa com `document.hidden` e quando o
  canvas sai da tela (IntersectionObserver); ≤ 599px: chuva com fonte 16px e
  quadro a cada 90ms, feixe 40% mais lento.
- **Movimento parado:** varredura desenha só a grade, uma vez; chuva não
  desenha nada.
- Canvas com `aria-hidden="true"` e `pointer-events: none`.

## 5. Testes e critério de pronto

### Automáticos (pytest)

- `analises`: registrar/listar/remover; isolamento entre dois usuários;
  limite de 500; `ON DELETE CASCADE`; `remover_todas`; estatísticas com
  números conferidos à mão (com `hoje` fixo); `codigos` sem severidade
  `info`.
- API: 401 sem sessão nas rotas do painel; analisar sem sessão funciona e
  não salva; com sessão salva; 404 ao apagar item de outro usuário;
  `DELETE /api/painel`.
- Parciais: cada página renderizada tem menu/rodapé/acessibilidade
  encaixados, nenhum `<!--PARCIAL` sobrando, `aria-current="page"` no item
  certo para cada rota do painel.
- Nenhum neutro antigo fora de `tokens.css` (seção 1).
- Os 140 testes existentes passam; os de histórico são reescritos para o
  contrato com login.

### No navegador

- Larguras 320, 360, 390, 414, 768, 1024, 1280, 1440, 1920:
  `document.documentElement.scrollWidth <= innerWidth` em todas as telas;
  barra de abas ≤ 599, ícones 600–1023, menu completo ≥ 1024.
- Temas escuro, claro e alto contraste em todas as telas, inclusive a home.
- Movimento parado: efeitos estáticos.
- Visão geral vazia e com dados; dois usuários em sequência sem ver dados um
  do outro.
- Nenhum erro de console em nenhuma tela.

### Pronto quando

Todos os itens acima passam e o usuário aprova o resultado visual.
`COMO-CONTINUAR.md` e `README.md` atualizados com as rotas novas e o novo
contrato do histórico.
