# Ativar “Entrar com Google” no Spectra

A integração está implementada. A ativação real depende de criar as credenciais na sua conta Google e salvá-las no arquivo `.env` local. Não envie o Client Secret por chat, não coloque no JavaScript nem faça commit dele.

## 1. Criar o projeto e a tela de consentimento

1. Abra o [Google Cloud Console](https://console.cloud.google.com/). No seletor de projetos, crie ou selecione **Spectra**.
2. Entre em **Google Auth Platform**. Se aparecer “Começar/Get started”, preencha o nome **Spectra**, e-mail de suporte e contato do desenvolvedor.
3. Em **Branding/Marca**, confira os dados apresentados aos usuários. Quando publicar, informe as páginas reais de início, privacidade e termos do seu domínio.
4. Em **Audience/Público**, escolha **Externo** para permitir contas Google pessoais. Se estiver em teste, adicione seu e-mail em **Usuários de teste** quando essa opção estiver disponível.
5. Use somente os escopos de identidade `openid`, `email` e `profile`. O Spectra não pede acesso ao Gmail, Drive ou contatos.

## 2. Criar o cliente OAuth

1. Acesse [Google Auth Platform → Clientes](https://console.cloud.google.com/auth/clients).
2. Clique em **Criar cliente** e selecione **Aplicativo da Web**.
3. Nome sugerido: **Spectra local**.
4. Em **URIs de redirecionamento autorizados**, adicione exatamente:

   ```text
   http://127.0.0.1:8000/auth/google/callback
   ```

5. Este fluxo usa redirecionamento pelo servidor; não depende de uma origem JavaScript autorizada. Se preencher esse campo, use `http://127.0.0.1:8000`, sem `/auth/google/callback`.
6. Crie o cliente e copie o **Client ID** e o **Client Secret** para o `.env` local conforme a próxima etapa. Guarde o segredo com cuidado; o Google pode exibi-lo somente na criação.

## 3. Preencher o arquivo local

Abra `Spectra_01/.env`. Preserve o segredo de sessão e as outras configurações existentes. Preencha:

```dotenv
SPECTRA_AMBIENTE=desenvolvimento
SPECTRA_ORIGEM_PUBLICA=http://127.0.0.1:8000
SPECTRA_COOKIE_SEGURO=0
SPECTRA_GOOGLE_CLIENT_ID=cole-aqui-o-client-id
SPECTRA_GOOGLE_CLIENT_SECRET=cole-aqui-o-client-secret
SPECTRA_GOOGLE_REDIRECT=http://127.0.0.1:8000/auth/google/callback
```

Use aspas no valor se ele contiver espaços ou `#`. O arquivo já é ignorado pelo Git. Não altere `SPECTRA_SEGREDO`: trocar essa chave encerra as sessões existentes.

Reinicie o servidor para carregar o `.env`. Em um clone do repositório, execute na pasta do projeto:

```powershell
.venv/Scripts/python.exe -m uvicorn spectra_link_guard.web.app:app --host 127.0.0.1 --port 8000 --env-file .env --no-access-log
```

Na instalação local que já possui `INICIAR-SPECTRA.cmd`, também é possível usar esse atalho. Acesse [a entrada local](http://127.0.0.1:8000/inicio). O botão Google será habilitado quando a configuração estiver completa. A API `/api/auth/provedores` deverá informar `"google": true`.

## 4. Testar com sua conta

- Para uma conta nova: clique em **Entrar com Google**, escolha a conta e conclua a autorização. O retorno deve abrir o painel.
- Para uma conta que já foi cadastrada por senha: entre primeiro com a senha, abra **Perfil → Acesso à conta → Conectar Google** em até 10 minutos após entrar e escolha o mesmo e-mail. Depois poderá entrar com Google normalmente.
- O Spectra não junta contas automaticamente pelo e-mail. Isso impede que um cadastro prévio indevido ganhe acesso ao perfil de outra pessoa.
- Se cancelar a autorização, o site retorna à entrada sem abrir sessão.
- `redirect_uri_mismatch`: confira protocolo, endereço, porta e caminho. `localhost` e `127.0.0.1` são endereços diferentes. Use o endereço acima em todas as configurações.
- `access_denied`: confira as permissões da conta, o público e os usuários de teste no Console.

## 5. Quando publicar

Crie preferencialmente outro cliente para produção. Cadastre o retorno real, por exemplo `https://seu-dominio.com/auth/google/callback`, e configure no servidor:

```dotenv
SPECTRA_AMBIENTE=producao
SPECTRA_ORIGEM_PUBLICA=https://seu-dominio.com
SPECTRA_COOKIE_SEGURO=1
SPECTRA_GOOGLE_REDIRECT=https://seu-dominio.com/auth/google/callback
```

Substitua também o Client ID e o Client Secret pelos do cliente de produção. Use HTTPS válido e um segredo de sessão aleatório de pelo menos 32 caracteres. O servidor rejeita configuração de produção sem essas condições. Atrás de proxy, aceite cabeçalhos encaminhados somente do proxy confiável; não exponha diretamente a porta do Uvicorn. Verifique no Google Auth Platform se o público, a marca e o domínio exigem verificação antes de abrir para usuários externos.

## E-mail de confirmação e recuperação

Google e SMTP são configurações independentes. Para enviar confirmação e recuperação de senha, configure um provedor SMTP com TLS:

```dotenv
SPECTRA_SMTP_HOST=servidor-do-seu-provedor
SPECTRA_SMTP_PORTA=587
SPECTRA_SMTP_USUARIO=usuario-do-provedor
SPECTRA_SMTP_SENHA=senha-ou-token-do-provedor
SPECTRA_SMTP_REMETENTE=Spectra <seu-remetente-verificado@seu-dominio.com>
```

A porta 587 usa STARTTLS; a 465 usa TLS desde a conexão. O remetente precisa estar autorizado no provedor. Sem SMTP, o site informa a indisponibilidade; não afirma que enviou uma mensagem. Os links expiram em 20 minutos e só podem ser usados uma vez. A redefinição encerra todas as sessões da conta.

## Referências oficiais

- [Configuração do cliente e consentimento](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid)
- [OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)
- [OAuth para aplicações Web no servidor](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Validação de identidade no servidor](https://developers.google.com/identity/sign-in/web/backend-auth)

Guia conferido em 24/10/2026. Os nomes dos menus podem aparecer em português ou inglês.
