# Spectra Link Guard

Módulo de **análise passiva de risco de links**, para proteção ao consumidor.
Recebe uma URL e devolve um laudo explicando, em português simples, por que
aquele endereço é ou não confiável.

---

## Escopo — o que a ferramenta faz e o que ela não faz

| Faz | Não faz |
| --- | --- |
| Lê a estrutura da URL (offline) | Varredura de portas |
| Um handshake TLS para ler o certificado público | Exploração de vulnerabilidades |
| Consulta listas públicas de ameaças (leitura) | Injeção de código / payloads |
| Explica o resultado ao usuário | Força bruta ou tentativa de autenticação |
| — | Enumeração de diretórios / fuzzing |
| — | Download do conteúdo da página |

Todo o tráfego gerado é **menor** do que o de abrir o link no navegador: um
único handshake TLS, sem requisição HTTP, sem seguir redirecionamentos, sem
baixar conteúdo. Esse handshake é opcional — com
`ConfiguracaoLinkGuard(verificar_tls=False)` a análise fica 100% offline.

Nenhuma das operações se enquadra na conduta descrita no **Art. 154-A do Código
Penal** (Lei 12.737/2012, "Lei Carolina Dieckmann"): não há invasão de
dispositivo, não há violação de mecanismo de segurança e não há obtenção de
dados não públicos. Os dados consultados são: (a) a própria URL informada pelo
usuário, (b) o certificado que o servidor apresenta publicamente a qualquer
visitante e (c) vereditos já publicados por Google Safe Browsing, VirusTotal e
PhishTank.

Sobre privacidade: nenhum dado do usuário é armazenado. O cache de reputação
guarda apenas o hash SHA-256 da URL consultada, em memória, por 15 minutos.

---

## Instalação

```bash
pip install -e ".[extras,dev]"
```

`extras` traz dois opcionais recomendados:

- **tldextract** — usa a Public Suffix List real para achar o domínio
  registrável (sem ele, o módulo cai numa tabela embutida que cobre `.br` e os
  TLDs mais comuns);
- **cryptography** — permite ler o certificado mesmo quando a cadeia não valida.

## Variáveis de ambiente

Listas públicas de ameaça (opcionais — sem elas o provedor é ignorado):

```bash
export SPECTRA_GSB_API_KEY=...        # Google Safe Browsing v4
export SPECTRA_VT_API_KEY=...         # VirusTotal v3
export SPECTRA_PHISHTANK_APP_KEY=...  # PhishTank
```

Acesso e banco:

```bash
export SPECTRA_BD=dados/spectra.db    # arquivo SQLite (padrão)
export SPECTRA_SEGREDO=...            # chave de assinatura do cookie
export SPECTRA_COOKIE_SEGURO=1        # só em HTTPS
```

**`SPECTRA_SEGREDO` é obrigatório em produção.** Sem ele o servidor gera uma
chave nova a cada processo: seguro, mas derruba todas as sessões a cada
reinício e não funciona com mais de uma réplica.

Login com Google (opcional — sem as três, o botão some da tela):

```bash
export SPECTRA_GOOGLE_CLIENT_ID=...apps.googleusercontent.com
export SPECTRA_GOOGLE_CLIENT_SECRET=...
export SPECTRA_GOOGLE_REDIRECT=http://localhost:8000/auth/google/callback
```

No Google Cloud Console → Credenciais → ID do cliente OAuth (aplicativo da
Web), o valor de `SPECTRA_GOOGLE_REDIRECT` precisa estar cadastrado em "URIs de
redirecionamento autorizados", idêntico, incluindo o esquema.

Sem chave, o provedor devolve `nao_configurado` e a análise segue com as etapas
1 e 2. As chaves nunca aparecem no relatório nem em log.

Assistente com IA (opcional — os dois chats, o da página inicial e o copiloto
do laudo, passam a responder com o Claude, em streaming e lembrando a conversa):

```bash
pip install -e ".[web,ia]"
export ANTHROPIC_API_KEY=...
export SPECTRA_IA_MODELO=claude-opus-5   # opcional; este é o padrão
export SPECTRA_IA=0                      # opcional; desliga a IA mesmo com chave
```

Sem a biblioteca ou sem a chave, `POST /api/assistente` responde 503 e os chats
voltam às respostas por regra. O copiloto envia o laudo aberto junto da
pergunta; o chat da página inicial é público, então tem limite próprio por IP
(40 perguntas a cada 5 minutos). `GET /api/saude` diz se a IA está ativa
(`assistente_ia`).

---

## Uso

### Como biblioteca

```python
from spectra_link_guard import analisar_url

relatorio = analisar_url("https://itau.seguranca-cliente.top/atualizar/senha")
print(relatorio.risco, relatorio.nivel.value)   # 62 alto
print(relatorio.resumo)
for achado in relatorio.achados:
    print(achado.severidade.value, achado.titulo, "->", achado.recomendacao)
```

Em código assíncrono (FastAPI), use a classe — ela reaproveita o cache:

```python
from spectra_link_guard import LinkGuard

guard = LinkGuard()
relatorio = await guard.analisar(url)
return relatorio.to_dict()
```

### App web (painel + API)

```bash
pip install -e ".[extras,web]"
```

```bash
python -m uvicorn spectra_link_guard.web.app:app --reload --port 8000
```

Depois abra **<http://localhost:8000>**.

| Endereço | O que é |
| --- | --- |
| `http://localhost:8000/` | Redireciona para `/inicio` — não há mais painel na raiz |
| `http://localhost:8000/inicio` | Porta de entrada: hero, login/cadastro, Google, assistente |
| `http://localhost:8000/painel` | Verificar um link. Exige sessão; sem ela volta para `/inicio` |
| `http://localhost:8000/painel/visao-geral` | Dashboard: indicadores e gráficos das suas análises |
| `http://localhost:8000/painel/historico` | Histórico com busca, filtro e exclusão |
| `http://localhost:8000/painel/aprender` | Guia de phishing e glossário |
| `POST /api/auth/cadastrar` | `{nome, email, senha}` → cria conta e abre sessão |
| `POST /api/auth/entrar` | `{email, senha}` → abre sessão (cookie HttpOnly) |
| `POST /api/auth/sair` | Revoga a sessão no servidor |
| `GET /auth/google` | Início do OAuth 2.0 com o Google |
| `http://localhost:8000/docs` | Documentação interativa da API (Swagger) |
| `POST /api/analisar` | `{"url": "...", "offline": false}` → relatório JSON completo |
| `GET /api/painel` | Indicadores do usuário logado (401 sem sessão) |
| `GET /api/painel/historico` | Todas as análises do usuário (até 500) |
| `GET /api/painel/estatisticas` | Números agregados da Visão geral |
| `DELETE /api/painel/{id}` | Remove uma análise sua (404 se não existe ou é de outra pessoa) |
| `DELETE /api/painel` | Apaga todo o seu histórico |
| `GET /api/saude` | Versão e quais provedores de reputação estão configurados |

O endpoint tem limite de 30 análises por IP a cada 5 minutos (janela em memória,
em [`web/app.py`](src/spectra_link_guard/web/app.py)) — ele consome cota de APIs
de terceiros e abre uma conexão TLS por chamada. Com várias réplicas, troque por
Redis ou pelo rate limit do proxy reverso.

**Privacidade do histórico:** cada usuário só vê o próprio histórico, que
fica no SQLite (tabela `analises`, até 500 por conta, apagadas junto com a
conta). Guarda-se host, domínio, nota, nível, horário e os códigos dos
sinais de risco — a URL completa não é retida, porque caminho e query podem
conter token de sessão ou dados pessoais. Análises feitas sem login (CLI,
integrações) não são guardadas.

**Seleção de texto:** a interface (menu, botões, rótulos) usa
`user-select: none`, para o duplo-clique não arrastar pedaços de UI junto. Todo
o conteúdo — resumo, explicações dos achados, domínio, host, dados do
certificado — leva a classe `.copiavel` e continua totalmente selecionável e
copiável.

### Publicar (sair do localhost)

O app é um ASGI comum, então qualquer plataforma de Python serve. O essencial:

```bash
python -m uvicorn spectra_link_guard.web.app:app --host 0.0.0.0 --port 8000
```

- coloque um proxy reverso na frente (nginx/Caddy) com HTTPS e rate limit;
- as chaves de API entram como variáveis de ambiente no painel do provedor,
  nunca no repositório;
- `--reload` é só para desenvolvimento.

### Linha de comando

```bash
python -m spectra_link_guard "https://exemplo.com/pagina"
```

```bash
python -m spectra_link_guard --offline --json "http://192.0.2.10/boleto.exe"
```

Flags: `--offline` (só sintaxe), `--sem-tls`, `--sem-reputacao`, `--json`.
Sai com código `1` quando o nível é `atencao` ou pior — útil em scripts.

---

## Arquitetura

```
src/spectra_link_guard/
├── models.py       dataclasses do relatório (Achado, CertificadoTLS, ...)
├── dados.py        listas curadas: marcas, sufixos, TLDs, homóglifos, iscas
├── sintaxe.py      etapa 1 — análise da string, 100% offline
├── tls.py          etapa 2 — handshake e leitura do certificado público
├── reputacao.py    etapa 3 — clientes das blacklists públicas
├── rede.py         etapa 4 — RDAP do domínio e do IP + resolução DNS
├── auth/
│   ├── bd.py         SQLite: usuários e sessões
│   ├── seguranca.py  scrypt + assinatura do cookie
│   ├── google.py     OAuth 2.0 (fluxo de código)
│   └── rotas.py      /api/auth/* e /auth/google
├── pontuacao.py    agregação em nota 0-100 e nível
├── analisador.py   orquestrador (etapas 2 e 3 em paralelo)
├── cli.py          interface de linha de comando
└── web/
    ├── app.py      API FastAPI + limite por IP + histórico da sessão
    └── static/     entrada (inicio.*) e painel (laudo.*)
```

### Etapa 1 — Validação sintática (offline)

| Código | O que detecta |
| --- | --- |
| `typosquatting` | domínio a 1-2 caracteres de uma marca real (`bradosco.com.br`) |
| `dominio_sosia` | domínio visualmente idêntico via homóglifos (`bradesc0`, `nubаnk` com "а" cirílico) |
| `marca_em_subdominio` | marca no subdomínio, domínio de terceiro (`itau.seguranca-cliente.top`) |
| `alfabetos_misturados` | letras latinas e não latinas no mesmo host (IDN spoofing) |
| `userinfo_no_host` | destino escondido antes do `@` |
| `host_ip_literal` | link para IP cru |
| `subdominios_excessivos` | ≥ 3 níveis empurrando o domínio real para fora da tela |
| `url_embutida` | segunda URL nos parâmetros (redirecionamento disfarçado) |
| `encurtador` | destino oculto por encurtador |
| `tld_de_risco` | `.zip`, `.top`, `.tk`, ... |
| `download_executavel` | caminho terminando em `.exe`, `.apk`, `.scr`, ... |
| `palavras_isca` | `login`, `senha`, `verificar`, `boleto`, `pix`, ... |
| `esquema_perigoso` | `javascript:`, `data:`, `file:` |

### Etapa 2 — Protocolo e certificado

`sem_https`, `tls_indisponivel`, `certificado_invalido`,
`certificado_autoassinado`, `certificado_host_divergente`,
`certificado_expirado`, `certificado_perto_do_vencimento`,
`certificado_recem_emitido`, `tls_obsoleto`.

> **Nota sobre a verificação de certificado.** O fluxo normal usa
> `ssl.create_default_context()`, com validação completa. Só quando essa
> validação **falha** o módulo refaz o handshake com `CERT_NONE` — e apenas para
> *ler* o certificado que o servidor já entregou e explicar ao usuário qual é o
> problema. Nenhum dado trafega por essa segunda conexão, e o resultado é sempre
> reportado como `cadeia_valida: false`. Não é um bypass de segurança: é o
> equivalente a clicar em "ver detalhes do certificado" na tela de aviso do
> navegador.

### Etapa 4 — Registro, hospedagem e DNS

RDAP (RFC 7483, o sucessor do WHOIS) devolve data de registro, **data de
vencimento, status do domínio, DNSSEC e nameservers**; o DNS resolve o nome
para IP e um segundo RDAP diz de que rede e país é o bloco. Uma terceira
consulta, por **DNS sobre HTTPS** (resolvedor da Cloudflare), lê **MX, NS, SPF,
DMARC e CAA**.
Nenhuma das duas consulta o site analisado — falam com o *registry* e com o
resolvedor, não com o alvo.

A idade do domínio é o sinal isolado mais forte contra phishing: campanhas
registram o domínio poucos dias antes do disparo. Achados:
`dominio_recem_registrado` (≤ 30 dias, ALTA), `dominio_novo` (≤ 90 dias, MEDIA)
e `dominio_estabelecido` (≥ 2 anos, INFO — peso zero, sinal apenas favorável).
Do DNS saem `dominio_suspenso` (ALTA), `dominio_expirado` (MEDIA), e
`sem_spf`, `sem_dmarc`, `dmarc_permissivo`, `sem_caa` — todos **INFO**.

> **Por que SPF/DMARC/CAA não somam risco.** Falta desses registros é problema
> do dono do domínio, não indício de que o link seja perigoso para quem o
> recebeu. A maioria dos sites pequenos e legítimos do Brasil não tem nenhum
> dos três; se entrassem como MEDIA, todo site honesto ganharia +16 de risco e
> a ferramenta viraria alarme falso. Entram com peso zero na nota e aparecem
> com destaque no plano de melhorias do copiloto, que é onde importam.

### Etapa 3 — Reputação

Google Safe Browsing (`threatMatches:find`), VirusTotal (`GET /api/v3/urls/{id}`)
e PhishTank (`checkurl`). O cliente do VirusTotal usa **somente** o endpoint de
consulta; o de submissão (`POST /urls`), que faria o VirusTotal ir buscar o
conteúdo do site, é deliberadamente evitado — há um teste que garante isso
(`test_vt_usa_somente_get_de_consulta`).

### Pontuação

Soma auditável dos pesos por severidade, saturada em 100:

| Severidade | Peso |
| --- | --- |
| `info` | 0 |
| `baixa` | 6 |
| `media` | 16 |
| `alta` | 30 |
| `critica` | 55 |

Achados de mesmo código contam uma vez. Um único achado crítico leva a nota a
pelo menos 80. Faixas: `seguro` 0-9, `baixo` 10-29, `atencao` 30-54, `alto`
55-79, `critico` 80-100.

---

## Limitações (declaradas de propósito)

- **Ausência de sinal não é atestado de idoneidade.** Um site de golpe criado
  hoje ainda não está em nenhuma blacklist e pode passar com nota 0. O resumo
  entregue ao usuário diz isso explicitamente.
- A lista de marcas em `dados.py` é curada e finita — cobre as mais imitadas no
  Brasil, não o mercado inteiro.
- Encurtadores não são resolvidos (isso exigiria uma requisição HTTP ao destino,
  fora do escopo passivo); o link é apenas sinalizado.
- Sem `tldextract`, domínios com sufixos incomuns podem ter o domínio
  registrável calculado de forma imprecisa.

## Testes

```bash
python -m pytest -q
```

190 testes, todos offline: as consultas de reputação usam `httpx.MockTransport`,
os achados de TLS são testados com certificados simulados e a API é exercitada
com `offline: true`. A suíte não abre nenhuma conexão de rede.

---

## Acesso

Senhas com **scrypt** (`hashlib`, N=2^14), sal por senha e comparação em tempo
constante. O hash nunca sai do servidor — `bd.publico()` recorta o registro
antes de qualquer resposta, e há teste travando os campos devolvidos.

A sessão vive no banco, não só no cookie: sem isso "Sair" não revogaria nada.
O cookie carrega apenas o id da sessão, assinado com HMAC, `HttpOnly` +
`SameSite=Lax` — o JavaScript da página não o lê, então um XSS não rouba a
sessão pelo `document.cookie`.

Login errado devolve **a mesma mensagem** para senha incorreta e para conta
inexistente. Dizer qual dos dois falhou transforma a tela de login numa
ferramenta de descoberta de e-mails válidos. Mesma lógica na recuperação de
senha, que responde igual exista ou não a conta.

O `state` do OAuth vai num cookie assinado e é conferido no retorno — sem isso,
um site de terceiro conseguiria disparar o fluxo e ligar a conta do Google dele
à sessão de outra pessoa.
