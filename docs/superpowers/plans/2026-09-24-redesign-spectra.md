# Redesign Spectra (11 itens) — Plano de Implementação

> Execução inline nesta mesma sessão (não handoff para outro engenheiro) — o
> plano documenta decisões e o manifesto de arquivos, sem cerimônia TDD para
> HTML/CSS estático (não testável por pytest). TDD se aplica ao item 7
> (checklist heurístico, backend).

**Goal:** Redesign visual + funcional do Spectra Link Guard: identidade
"Spectra", ícones, navegação lateral em telas reais, novas telas
(Histórico, Aprender, Privacidade, Termos), checklist heurístico com
gráfico, footer, e acessibilidade (tema, fonte, alto contraste, movimento).

**Tech Stack:** FastAPI + HTML/CSS/JS estático servido por `_pagina()`
(sem templating engine — duplicação controlada de blocos como footer).
Chart.js via CDN para gauge/donut. Ícones Lucide inline (SVG copiado, sem
dependência de CDN extra — mantém o padrão já usado no projeto).

## Decisões confirmadas com o usuário

1. **Checklist heurístico (item 7/8):** estende `sintaxe.py`/`models.py`
   (não cria motor paralelo). Os 11 critérios usam os achados que a etapa 1
   já calcula; a pontuação exibida continua sendo `relatorio.risco` (já
   testado). Classificação Seguro/Suspeito/Perigoso é um mapeamento
   client-side do `nivel` existente — sem novo campo no backend.
2. **Navegação lateral (item 6):** 3 destinos reais — Verificar (`/painel`),
   Histórico (`/painel/historico`), Aprender (`/painel/aprender`). As
   âncoras atuais (Veredito, Destino real, Evidências, Sinais) viram
   sub-navegação secundária, visível só quando há laudo carregado.

## Adaptações a declarar ao usuário (baixo risco, não pedem OK antes)

- **Histórico mostra host/domínio, não a URL completa** — a retenção da URL
  completa já é uma decisão de privacidade documentada no README
  (`_Historico` só guarda host/domínio/nota/hora). O item 9 pede coluna
  "URL"; vou expor host+domínio (o que já existe), não afrouxar a política.
- **Tema claro/escuro** é viável de forma limpa nas páginas do painel
  (laudo.css já usa custom properties). Em `/inicio` (Tailwind CDN), aplico
  overrides `!important` escopados em `:root[data-tema="claro"]` nas
  classes Tailwind realmente usadas — funciona, é um pouco mais frágil a
  mudanças futuras de classe, documento isso no código.
- **Ícones:** em vez de carregar a lib Lucide via `<script>` de CDN, copio
  os paths SVG do Lucide (ISC license) inline, no mesmo padrão que o
  projeto já usa para os ícones existentes (stroke 2, round caps). Evita
  dependência de rede extra e mantém consistência visual.

## Manifesto de arquivos

**Backend**
- `dados.py` — MOD: adiciona "banco", "gratis" a `ISCAS`.
- `models.py` — MOD: `CriterioChecklist` dataclass + campo `checklist` em `AnaliseLink`.
- `sintaxe.py` — MOD: `checklist_heuristico(ctx, achados)` (11 critérios, comentado).
- `analisador.py` — MOD: popula `relatorio.checklist` logo após `analisar_sintaxe`.
- `web/app.py` — MOD: rotas `/painel/historico`, `/painel/aprender`, `/privacidade`, `/termos`; endpoint `GET /api/painel/historico` (lista completa, até 50, para busca/filtro no front).
- `tests/test_checklist.py` — NOVO: cobre os 11 critérios.
- `tests/test_web.py` — MOD: smoke test das novas rotas/endpoint.

**Frontend — compartilhado**
- `web/static/acessibilidade.js` — NOVO: tema, fonte, alto contraste (persistidos), reaproveita `data-movimento` já existente para "desativar animações".
- `web/static/rodape.css` — NOVO: estilos do footer (gradiente animado sutil, responsivo) + tema claro (custom properties) + regras globais de cursor (item 2).
- Bloco de footer HTML duplicado (sem template engine) em todas as páginas, com ano via JS.

**Frontend — painel (Verificar)**
- `web/static/laudo.html` — MOD: sidebar com 3 destinos reais + sub-nav de âncoras, ícones, footer, toolbar de acessibilidade, seção de checklist (card resumo + canvas gauge + tabela), `<title>Spectra</title>`.
- `web/static/laudo.css` — MOD: tema claro, cursor, ícones, checklist/gauge/tabela, footer.
- `web/static/laudo.js` — MOD: renderiza checklist na tabela + inicializa gauge Chart.js.

**Frontend — novas telas**
- `web/static/historico.html` + `historico.js` — NOVO: lista completa, busca, filtro por veredito, apagar (reusa `DELETE /api/painel/{id}`), gráfico resumo (Chart.js doughnut).
- `web/static/aprender.html` — NOVO: seções com `<details>` (phishing, como ler URL, sinais de alerta, o que fazer, glossário).
- `web/static/privacidade.html`, `web/static/termos.html` — NOVO: texto modelo editável.

**Frontend — inicio**
- `web/static/inicio.html` — MOD: título, cursor, ícones, seção "Por que usar nossos serviços?" (4-6 cards, scroll-reveal + hover), footer, toolbar de acessibilidade, tema claro.

## Ordem de execução

1. Backend (checklist) + testes → `pytest -q`
2. Infra compartilhada (ícones/acessibilidade/footer/cursor)
3. Painel (Verificar): sidebar + checklist/gauge/tabela
4. Histórico
5. Aprender + Privacidade + Termos
6. Início: título, cursor, ícones, seção "por que usar", footer, acessibilidade, tema claro
7. Verificação manual no browser + lista final de arquivos
