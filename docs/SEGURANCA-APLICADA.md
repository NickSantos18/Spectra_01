# Correções de segurança — 24/10/2026

As correções abaixo foram aplicadas ao código local. As animações de perfil e os fundos foram preservados. A ativação do Google e do envio de e-mail depende das credenciais do proprietário; os testes automatizados de identidade usam respostas simuladas, sem autenticar uma conta real no Google.

## Vulnerabilidades corrigidas

| Área | Comportamento aplicado |
|---|---|
| Privilégios editoriais | E-mail verificado obrigatório para editor, publicação no blog e aceite de convite. IDs de contas verificadas podem definir editores. |
| SSRF no TLS | Somente porta 443 e IPs públicos; rejeição de DNS com qualquer resposta interna/especial, incluindo IPv6. O socket conecta ao IP já validado, mantendo o host original no SNI. O diagnóstico de certificado inválido usa a mesma lista de destinos. |
| Cookies malformados | Assinaturas e Base64 inválidos são recusados sem gerar erro 500. |
| Senhas | Argon2id para hashes novos; migração do scrypt no login correto. Verificação fictícia para conta inexistente; limite de operações de hash simultâneas. |
| Sessões | HttpOnly, SameSite=Lax, Secure em produção, revogação no logout, limite absoluto de 30 dias e renovação de até 14 dias. |
| CSRF | Política central para todas as mutações `/api/`: Origin/Referer, Fetch Metadata e conteúdo JSON. Requisições com cookie de sessão precisam apresentar origem válida. Sem CORS permissivo. |
| Abuso de APIs | Contadores SQLite compartilhados entre processos que usam o mesmo banco. Limites para cadastro, login por IP e por conta, recuperação, upload, mensagens e análise. Limites de tamanho do corpo e de análises simultâneas. |
| Imagens | Verificação completa e recodificação de PNG/JPEG/WebP; descarte de metadados, limites de pixels/dimensões, rejeição de truncamento e animação; no máximo dois processamentos simultâneos por processo. |
| Armazenamento | Cota atômica de 200 MB por conta e 1 GiB total para anexos, além dos limites por arquivo. |
| Navegador | CSP com nonce por resposta, sem `unsafe-eval` para scripts; nosniff, DENY, no-referrer e restrição de câmera/microfone/localização. HSTS em produção. |
| Cache privado | `no-store` para APIs, painel, OAuth e páginas de confirmação/redefinição. |
| Recuperação e confirmação | SMTP com TLS, tokens aleatórios de uso único guardados por hash, validade de 20 minutos; redefinição encerra todas as sessões. Sem provedor configurado, o site informa indisponibilidade. |
| Google | Código de autorização, PKCE S256, state assinado e uso único, nonce e ID token validado pelo SDK oficial. Verificação de destinatário do token, identificador, e-mail verificado e vínculo explícito para contas existentes. |

Para cumprir a CSP, o Tailwind da entrada passou a ser compilado em CSS local. O estilo não depende mais de executar o compilador de Tailwind no navegador. Os arquivos de efeitos e a sequência da animação de perfil não foram alterados nesta etapa.

## Validação

- Preparação para publicação em **25/10/2026**: suíte completa com **273 testes Python aprovados** e **nove testes JavaScript aprovados**. Uma advertência de depreciação do TestClient/HTTPX permanece. Os resultados abaixo registram também as verificações anteriores, em 24/10/2026.

- Suíte Python: **271 testes aprovados** na execução completa; após os últimos ajustes, **98 testes aprovados** na verificação final das rotas web, comunidade e upload, incluindo **43 casos de regressão de segurança**. Uma advertência de depreciação do TestClient/HTTPX, sem falhas nesses testes. Essas execuções têm testes em comum; as contagens não devem ser somadas.
- Consulta OSV: **46 pacotes Python instalados, nenhum aviso conhecido encontrado** em 24/10/2026. O resultado é uma consulta de versões, não uma garantia contra falhas desconhecidas.
- Auditoria npm: **74 dependências de desenvolvimento, zero avisos após a atualização**. O analisador CSS transitivo com aviso de complexidade quadrática foi fixado em `postcss-selector-parser@7.1.6`; o CSS foi recompilado e a tela de acesso conferida.
- Teste real do perfil em navegador isolado: movimento desde o botão, barra lateral, espaçamento, arrastar, toque, teclado, cancelar, navegação e movimento reduzido aprovados.
- Telas de acesso e recuperação, CSS local e laudos de análise aprovados no navegador com a CSP ativa. O teste antigo de tempo da rolagem inicial oscilou nos limites de quadros/650 ms neste notebook; a animação foi preservada conforme solicitado.
- Os testes usam bancos temporários e não alteram contas reais.

## Ativações pendentes

1. Criar o cliente OAuth no Google Cloud e preencher as credenciais no `.env`, conforme [CONFIGURAR-GOOGLE.md](CONFIGURAR-GOOGLE.md). Até lá, o login Google fica indisponível e explica o motivo.
2. Configurar um provedor SMTP para confirmação e recuperação por e-mail. Contas verificadas pelo Google não dependem do SMTP para entrar.
3. Antes da publicação, configurar domínio e HTTPS, proxy confiável, volume persistente, backup externo e segredos no servidor. O `.env` e o banco local não devem ser publicados.

## Limites que continuam relevantes

Vídeos têm validação de tipo e assinatura do contêiner, limites e acesso autenticado. Ainda não há decodificação completa, transcodificação em processo isolado nem antivírus. Não há MFA, painel de revogação de dispositivos ou mitigação distribuída de DDoS. Os limites SQLite funcionam para processos no mesmo banco; múltiplas máquinas precisam de limitador compartilhado e proteção na borda. Conteúdo CSS inline continua autorizado pela CSP; scripts inline só executam com nonce. Dependências externas de ícones/gráficos continuam sujeitas às URLs e integridade configuradas.

A proteção contra destinos internos foi aplicada ao handshake TLS do link. Consultas de reputação e RDAP usam provedores definidos no programa; restrições de saída na infraestrutura continuam recomendadas. A ferramenta de análise de links segue passiva e não comprova a segurança completa de um site nem a identidade comercial do responsável.

## Reproduzir as verificações

```powershell
.venv/Scripts/python.exe -m pytest -q
node --test tests/foto_editor.test.cjs tests/fundo.test.cjs
node scripts/verificar_explorar.cjs --perfil
node scripts/verificar_explorar.cjs --acesso
node scripts/verificar_explorar.cjs --laudo
```

Para reconstruir os estilos, use a versão de pnpm compatível com o lockfile:

```powershell
pnpm install --frozen-lockfile
pnpm run build:css
```

No Windows sem permissão de links simbólicos, com pnpm 11: `pnpm fetch` e depois `pnpm install --offline --frozen-store`. O CSS compilado fica no repositório; não é necessário Node no servidor para servir o site.

O arquivo `requirements-lock.txt` registra as versões Python verificadas neste computador. Para reproduzir o ambiente em Python 3.12, instale esse arquivo e depois o projeto com `pip install --no-deps -e .`. Atualizações futuras devem repetir a auditoria e os testes. O iniciador local desativa o access log do Uvicorn para evitar registrar códigos OAuth na URL; configure também a filtragem dos logs do proxy ao publicar.
