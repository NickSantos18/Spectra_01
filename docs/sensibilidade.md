# Risco detectado e cobertura de verificação

O Spectra mantém uma análise passiva de URL, TLS, registro/DNS e fontes de reputação. A nota continua sendo calculada por achados explicáveis; não é uma probabilidade estatística de segurança nem uma análise de direitos autorais.

## Ajustes

- O nome registrável também é comparado ao nome de marcas conhecidas quando há uma ou duas letras adicionais repetidas. Isso permite reconhecer `steeam.com` como semelhante a Steam, mesmo que os endereços oficiais sejam `steampowered.com` e `steamcommunity.com`. A regra exige marcas de ao menos cinco letras e não transforma qualquer palavra com uma edição de diferença em suspeita. Domínios oficiais são preservados pela verificação existente.
- O novo achado `marca_com_letra_repetida` tem severidade alta, soma 30 pontos e aparece no checklist e nos gráficos como Nome parecido com marca conhecida. Ele indica possível confusão de identidade; não confirma fraude por si só.
- A extensão de downloads é verificada depois de decodificar o caminho da URL, incluindo `%2eexe`.
- A resposta JSON acrescenta `verificacao`: `limitada`, `provedores_consultados` e `motivo`. Só resultados limpo ou malicioso contam como resposta conclusiva de um provedor. Erro, desconhecido, ausência de chave e modo offline não contam como reputação limpa.
- Quando não existe resposta conclusiva de reputação, análises com poucos sinais exibem Verificação limitada / não confirma segurança. A interface deixa de usar Liberado e de agrupar resultados baixos sob Seguro. O copiloto por regras também explica essa limitação.

Os três exemplos fornecidos pelo usuário são regressões de teste. Na análise offline, `steeam.com` gera Atenção. Tokyvideo e Pobreflix recebem cobertura limitada, sem presunção de malware ou de autorização dos vídeos. Não foram incluídas listas arbitrárias de bloqueio desses sites. A detecção de reputação exige configurar os provedores disponíveis no servidor; as chaves não são fornecidas pelo aplicativo.

## Gráficos

Laudo, Histórico e Visão Geral usam os mesmos cinco níveis e tokens de cor. O nome visual Sem sinais substitui Seguro, preservando o identificador interno `seguro` para compatibilidade. As legendas reservam colunas para rótulo, quantidade e porcentagem, com empilhamento adaptativo e suporte a foco por teclado. As barras de frequência usam o total de análises como denominador quando exibem porcentagens; assim o comprimento corresponde ao percentual indicado.

Os registros históricos mantêm suas notas originais, pois não guardam a URL completa e não podem ser reanalisados automaticamente. Para aplicar as novas regras a um endereço, faça uma nova análise.

## Verificação

`python -m pytest -q --basetemp .pytest_tmp_sensibilidade -p no:cacheprovider` valida as regras e a compatibilidade. `node scripts/verificar_explorar.cjs --graficos` verifica cores e ausência de sobreposição em três larguras e nos temas claro e escuro. `node scripts/verificar_explorar.cjs --laudo` valida o resultado no navegador com a API real em modo offline, incluindo avisos de cobertura, exemplos de risco e tratamento de falhas.
