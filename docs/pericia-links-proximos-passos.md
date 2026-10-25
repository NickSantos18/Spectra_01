# Como ampliar a perícia de links do Spectra

Revisão do código em 24/10/2026. Esta lista descreve o motor atual e uma proposta de evolução; não afirma que as novas verificações já foram implementadas.

## O que já é observado

- Sintaxe e estrutura da URL: domínio, marcas imitadas, caracteres suspeitos, IP literal, portas incomuns, iscas e extensões de executáveis.
- TLS: conexão negociada, dados do certificado, validade, correspondência do nome e cadeia de confiança.
- RDAP e DNS: idade e registro do domínio, status, hospedagem e registros MX, NS, SPF, DMARC e CAA. O campo DNSSEC do registro não é uma validação criptográfica completa da cadeia DNS.
- Reputação: integração com Google Safe Browsing, VirusTotal e PhishTank, quando configurados. Nesta instalação inicial as três chaves estão ausentes; a existência da integração não significa que as consultas estejam sendo feitas.
- A interface já tem avisos de cobertura limitada. A nota de risco continua sendo uma agregação de sinais, não uma probabilidade estatística ou uma garantia de segurança.

## O que ainda não é verificado

| Evidência | Limite atual | Evolução proposta |
|---|---|---|
| Redirecionamentos | O motor não requisita a página do link nem segue sua cadeia HTTP. Os redirects de RDAP são de outro serviço. | Mostrar cada salto, destino final, troca de domínio, downgrade HTTPS e loops. Revalidar cada destino e limitar saltos. |
| Cabeçalhos HTTP | Sem GET/HEAD ao alvo, não lê CSP, HSTS, nosniff, anti-frame, Referrer-Policy ou Permissions-Policy. | Observar a política efetivamente recebida; distinguir ausência, configuração fraca e política somente em relatório. Ausência não comprova fraude. |
| Cookies | Não observa Set-Cookie ou escopo dos cookies do alvo. | Relatar flags observáveis: Secure, HttpOnly, SameSite, Domain e Path. Uma visita anônima não revela necessariamente cookies de sessão após login. |
| HTML e formulários | Não baixa conteúdo nem inspeciona ações de formulários. | Em modo HTTP limitado, verificar destinos, envio por HTTP, iframes e recursos externos sem submeter formulários. Nenhum envio de senha, documento ou pagamento. |
| Scripts e comportamento | Não executa JavaScript, analisa downloads ou observa navegação dinâmica. | Uma etapa posterior pode usar navegador descartável e isolado, com limites rigorosos. Não usar o navegador pessoal do visitante nem executar arquivos baixados. |
| Configuração completa de TLS | Uma conexão bem-sucedida mostra apenas a configuração negociada com aquele cliente. | Separar isso de testes de versões/cifras e revogação OCSP/CRL, atualmente não implementados. Uma auditoria mais ativa pertence ao modo do proprietário. |
| Identidade e reputação comercial | Marca na URL, idade, país de hospedagem e certificado não provam legitimidade comercial. | Exibir evidências e limitações; integrações de fontes confiáveis devem ter contexto e não virar selo automático de confiança. |
| Falhas internas da aplicação | Não testa autenticação, autorização, SQL injection, XSS, lógica de negócio, backups nem acesso administrativo. | Oferecer avaliação separada de sites próprios/autorizados, com escopo, contas de teste e acesso ao código/configuração. Não inferir ausência de falhas a partir da página pública. |

## Ordem recomendada

1. **Proteger a saída do Spectra:** bloquear redes internas, loopback, link-local e outros destinos especiais em IPv4/IPv6; conectar somente ao IP validado; preservar SNI e validação TLS; impor política de portas e saída em rede.
2. **Ativar e medir a reputação:** configurar fornecedores, tratar cota/timeout/erro e mostrar quais fontes realmente responderam. Evitar enviar URLs com dados sensíveis sem tratamento adequado.
3. **Adicionar modo de observação HTTP:** pequeno orçamento de requisições, timeout, tamanho máximo, leitura em streaming, redirecionamento manual e revalidação de cada salto. Não executar scripts, não enviar cookies do usuário e não baixar arquivos automaticamente. Essa etapa amplia o escopo atual, que não faz HTTP ao alvo, e exige atualização da documentação/privacidade.
4. **Ampliar o laudo de cobertura:** por critério, separar observado favorável, observado desfavorável, inconclusivo, indisponível e não verificado; registrar data, fonte e destino efetivamente inspecionado. Não tratar falta de dados como aprovação e não misturar higiene de configuração com prova de golpe.
5. **Avaliação de proprietário:** só depois, criar testes mais profundos para sistemas próprios/autorizados, com ambiente e escopo definidos.

## Fontes

- [OWASP HTTP Headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html): finalidade e limites dos cabeçalhos.
- [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html): validação dos IPs, DNS rebinding e proteção de rede.
- [OWASP Web Security Testing Guide](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/): áreas de avaliação além da leitura de uma URL.
