# Spectra — como continuar em outro notebook

Guia rápido só para destravar o ambiente. Documentação completa do projeto
(endpoints, arquitetura, decisões de segurança) está em [README.md](README.md).

## 1. Requisitos

- Python 3.11 ou mais novo
- (Windows) PowerShell ou Git Bash

Confira a versão:

```bash
python --version
```

## 2. Instalar

Na pasta do projeto (`spectra 01/`):

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[extras,web,dev]"
```

No Linux/Mac, o ativar muda para `source .venv/bin/activate`.

## 3. Rodar o site

```bash
set SPECTRA_SEGREDO=troque-esta-chave-por-qualquer-coisa
python -m uvicorn spectra_link_guard.web.app:app --reload --port 8000
```

No PowerShell, troque `set` por `$env:SPECTRA_SEGREDO = "..."`.

Depois abra **http://localhost:8000** (redireciona para `/inicio`). Clique em
"Cadastrar-se" para criar uma conta — o banco (`dados/spectra.db`) é recriado
na hora, do zero, na primeira vez que o servidor sobe (não veio dentro do
zip de propósito, para não levar contas de teste).

`SPECTRA_SEGREDO` é opcional em dev (sem ele o servidor gera uma chave nova
a cada reinício, o que derruba sessões abertas) — mas sem ele você vai ter
que logar de novo toda hora que reiniciar o servidor.

## 4. Rodar os testes

```bash
python -m pytest -q
```

Eram **193 testes**, todos offline (sem tocar rede), na última execução.

## 5. O que já foi feito (redesign "Spectra")

Os 11 itens pedidos no redesign estão implementados (1 a 11); o item 12 é a
fundação visual, que veio depois:

1. Título da aba = "Spectra" em todas as páginas
2. Cursor de texto removido de elementos não-editáveis (`rodape.css`)
3. Ícones Lucide (via CDN, com SRI) no menu, cards, botões e resultado
4. Seção "Por que usar nossos serviços?" na home, com scroll-reveal
5. Footer com Privacidade/Termos, WhatsApp/Instagram/e-mail, copyright
   automático e fundo animado sutil — em todas as páginas
6. Menu lateral com 3 telas reais: **Verificar** (`/painel`), **Histórico**
   (`/painel/historico`), **Aprender** (`/painel/aprender`)
7. Checklist heurística de 11 critérios (`sintaxe.py::checklist_heuristico`)
8. Resultado com card de veredito, gráfico de pontuação (Chart.js) e
   tabela de critérios passou/falhou
9. Tela de Histórico: busca, filtro, apagar, gráfico resumo
10. Tela Aprender + glossário + botões "?" no laudo
11. Acessibilidade: tema claro/escuro, fonte +/-, alto contraste, "reduzir
    movimento" — botão flutuante arrastável, embaixo à esquerda
12. Fundação visual (branch `fundacao-visual`): fundo `#070B14` com tokens
    únicos (`static/tokens.css`), histórico por usuário no SQLite, tela
    **Visão geral** (`/painel/visao-geral`), menu/rodapé/acessibilidade
    como parciais (`web/parciais/`), animações, efeitos de fundo e
    responsividade de 320px a 1920px.

### Mapa rápido dos arquivos principais

| O quê | Onde |
|---|---|
| Motor de análise (sintaxe, TLS, reputação, RDAP/DNS) | `src/spectra_link_guard/*.py` |
| Checklist heurística (itens 7/8) | `src/spectra_link_guard/sintaxe.py` → `checklist_heuristico()` |
| Rotas e páginas | `src/spectra_link_guard/web/app.py` |
| Telas (HTML) | `src/spectra_link_guard/web/static/*.html` |
| Estilo compartilhado (cursor, fundo da página, rodapé, botão e painel de acessibilidade) | `src/spectra_link_guard/web/static/rodape.css` |
| Acessibilidade (tema/fonte/contraste/arrastar) | `src/spectra_link_guard/web/static/acessibilidade.js` |
| Cores (todas), tema claro e alto contraste | `src/spectra_link_guard/web/static/tokens.css` |
| Menu, rodapé e acessibilidade (um lugar só) | `src/spectra_link_guard/web/parciais/` |
| Histórico por usuário e estatísticas | `src/spectra_link_guard/web/analises.py` |

## 6. Pendente / em aberto

- **Logo**: a primeira proposta foi rejeitada pelo usuário e removida; ainda
  usando o ícone placeholder (escudo simples) que já existia no projeto.
  Ele disse que vai desenhar por conta própria — quando tiver o arquivo,
  é só pedir para aplicar no cabeçalho, hero, sidebar e favicon.
- **Contatos do rodapé são placeholder**: WhatsApp `(11) 99999-9999`,
  Instagram `@spectra.seguranca`, e-mail `contato@spectra.app` — trocar
  pelos reais, agora num lugar só: `web/parciais/rodape.html`.
- **Textos de Política de Privacidade e Termos de Uso** são modelo
  genérico — revisar com jurídico antes de publicar de verdade.

## 7. Nota sobre git

O projeto tem repositório próprio em `spectra 01/`: branch `main` + uma
branch de trabalho por sub-projeto (a fundação visual foi feita em
`fundacao-visual`). O banco `dados/` fica fora do git de propósito, para não
levar contas de teste.
