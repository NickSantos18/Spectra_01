# Perfil e comunidade Spectra

As páginas `/painel/perfil`, `/painel/chat`, `/painel/blog`, `/painel/forum` e `/painel/explorar` exigem login. As novas tabelas são criadas automaticamente no SQLite existente, preservando usuários e análises.

O perfil permite alterar nome, biografia e foto. O navegador recorta e converte a foto para PNG de 256 × 256 pixels. O endereço IP é o da conexão observada pelo servidor, exibido apenas para o próprio usuário, sem histórico de IPs. Em acesso local, é normal aparecer `127.0.0.1`. Não se consulta um serviço externo para descobrir o IP público.

Ao escolher uma foto, um editor local permite arrastar com mouse ou toque, mover com as setas e ajustar o zoom entre 1× e 4×, com prévia circular. Centralizar restaura o enquadramento inicial. Aplicar foto atualiza a prévia; Salvar perfil persiste o resultado e atualiza o avatar do menu. Cancelar ou pressionar Escape mantém a foto anterior. Ajustar enquadramento reabre o editor: durante a mesma visita usa a imagem original escolhida; depois de recarregar, usa o PNG já salvo, pois o original não é armazenado no servidor.

O Explorar reúne artigos do blog e tópicos do fórum, com foto do autor e botão Seguir. É possível publicar diretamente no Explorar; essas publicações são tópicos do fórum. Seguir e deixar de seguir atualiza todos os cartões daquele autor.

As conversas privadas persistem no banco. A interface busca novas mensagens a cada três segundos enquanto está visível. A lista de contatos contém apenas pessoas que você segue ou que seguem você e expõe apenas identificador, nome e foto, sem e-mail ou IP. O servidor exige esse vínculo para ler ou enviar mensagens, permitindo que o destinatário responda sem precisar seguir de volta. Se não houver mais vínculo em nenhum sentido, o histórico é preservado no banco, mas não fica acessível até que alguém volte a seguir. É necessário ter duas contas para conversar. As mensagens não possuem criptografia de ponta a ponta.

A logo enviada já possui transparência e é usada sem fundo preto. Os fundos da comunidade usam efeitos em canvas: fitas de ondas luminosas nas conversas e no blog, ondas de transmissão no fórum e arcos orbitais no Explorar. A entrada usa circuitos convergentes com rastros e ondas ao redor da marca no lugar dos cubos, sem carregar Three.js ou anime.js. Os outros fundos permanecem como antes. Os novos efeitos respeitam o controle de movimento existente, pausam fora da tela ou com a aba oculta e limitam resolução e quadros no celular. A troca de foto usa um botão que abre o seletor nativo, sem exibir o campo de arquivo.

O fórum permite criar tópicos e responder. O blog permite comentários de membros e artigos de especialistas convidados. Ambos são visíveis para membros autenticados. O autor pode excluir sua publicação; editores também podem excluir publicações da comunidade.

## Visual e navegação

Usuários autenticados podem visitar `/painel/perfil?usuario=ID` clicando no autor de uma publicação, comentário ou conversa. A visualização de membro mostra nome, foto, biografia e publicações do blog e fórum, sem e-mail, IP ou campos de autenticação. A API `GET /api/usuarios/{id}/perfil` exige sessão e retorna apenas esses dados de apresentação, data de criação, estado Seguindo e total de publicações. A lista `GET /api/comunidade/explorar?autor=ID` filtra as postagens por autor. O próprio perfil de edição também mostra Minhas publicações.

O avatar ao lado do nome no menu é quadrado, inclusive após salvar a foto. O editor abre ao selecionar uma imagem e oferece zoom, arraste e controles horizontal e vertical; as posições são limitadas à área da imagem para evitar bordas vazias. Reabrir a mesma imagem na mesma visita mantém o último enquadramento aplicado. As imagens de perfil continuam armazenadas como o recorte PNG, sem guardar o arquivo original no servidor.

O perfil possui um fundo exclusivo `energia-perfil`: ondas em camadas, feixes e pulsos nas laterais, com anéis decorativos ao redor da foto. As cinco páginas da comunidade carregam as mesmas famílias de fontes do painel (Hanken Grotesk, Inter e JetBrains Mono) e usam cartões, campos, botões e balões com cantos retos. Fotos e avatares permanecem circulares. As regras ficam concentradas em `comunidade.css`, sem sobrescritas de cartões no arquivo de identidade.

A navegação lateral segue: Verificar, Visão Geral, Histórico, Explorar, Blog, Fórum e Aprender. Conversas fica na navegação interna do Explorar. No celular, os três primeiros ficam na barra rápida e os demais aparecem nessa ordem em Mais. O perfil foi removido do menu lateral e do Mais.

Nome e foto da conta aparecem no canto superior direito para membros autenticados. Ao abrir o próprio perfil, a foto parte da posição real desse botão e desliza suavemente até o centro da área de conteúdo, onde se transforma em cadeado. Essa abertura dura um segundo. A barra lateral permanece visível e utilizável; no celular, a barra de navegação inferior também fica disponível. A cena mostra apenas o cadeado, a chave, a explicação e Cancelar, com espaçamento organizado em uma composição central. A pessoa arrasta a chave até a fechadura, com mouse ou toque; a espera é livre. Depois do encaixe, a chave entra e gira, o cadeado se desfaz em fragmentos e o perfil aparece. São três segundos de efeitos ao todo, além do tempo de interação e do carregamento da página. Somente um marcador visual com instante e versão atravessa a navegação em sessionStorage, sem transportar dados de perfil. A chegada tem um limite de espera para evitar tela presa em falha de carregamento.

## Explorar: feed, mídia, conexões e jogos

A cena de perfil respeita a preferência resolvida por movimento.js. Movimento reduzido leva diretamente ao perfil. Com teclado ou toque, também é possível selecionar a chave e depois ativar o cadeado, sem arrastar. Cancelar ou Escape volta à página de origem com foco no acesso ao perfil. A navegação lateral pode ser usada para sair da cena. Cliques com modificadores conservam a abertura normal em outra aba. O cadeado é apenas um efeito de navegação e não substitui autenticação ou autorização.

A navegação interna tem Feed, Publicar, Conexões, Conversas e Desafios. O endereço `/painel/explorar` abre o feed; os demais destinos usam `#publicar`, `#conexoes`, `#conversas` e `#desafios`. O endereço antigo `/painel/chat` redireciona para `/painel/explorar#conversas`. O formulário de postagem aparece apenas na aba Publicar. Nas páginas Blog e Fórum o formulário existente continua disponível.

As listas Seguindo e Seguidores são privadas para o dono da sessão, sem e-mails ou IPs. São servidas por `/api/conexoes/seguindo` e `/api/conexoes/seguidores`. Perfis e ações de seguir continuam disponíveis nos cartões do feed.

Cada publicação pode anexar até quatro arquivos: PNG/JPEG/WebP de até 10 MB por foto ou MP4/WebM de até 40 MB por vídeo. A seleção mostra prévia e permite remover arquivos antes de publicar. Fotos são decodificadas, limitadas a 4096 × 4096 pixels e recodificadas sem metadados; fotos de perfil têm limite de 512 × 512. Imagens animadas e truncadas são recusadas. Vídeos usam controles nativos sem reprodução automática e validação da assinatura do contêiner; a reprodução também depende de o navegador suportar o codec. Não há decodificação completa, transcodificação nem antivírus para vídeos.

O envio é binário por `POST /api/midias`, com Content-Type do formato. Os bytes ficam no SQLite na tabela `midias`; `publicacao_midias` associa os arquivos ao post. A conta pode guardar até 200 MB em anexos. Uma mídia ainda não publicada é acessível só ao dono. Depois de associada, pode ser vista por membros autenticados. Não existem URLs públicas de armazenamento. `GET/HEAD /api/midias/{id}` suporta intervalos de bytes para vídeos e usa no-store e nosniff. A publicação só pode vincular mídias próprias e ainda não associadas; a exclusão de um post remove seus arquivos. Anexos não publicados com mais de 24 horas são removidos durante um novo upload.

Os cinco jogos são Investigue o phishing, Proteja uma conta, Reconstrua o incidente, Monte a defesa e Detetive de links. Cada jogo possui três fases sequenciais, com alternativas ou ordenação de itens pelos botões Subir e Descer. As questões são cenários fictícios e não executam operações sobre sistemas externos. A correção, os desbloqueios e os pontos são calculados no servidor. O catálogo e as fases não expõem o gabarito.

`GET /api/desafios` retorna as trilhas e o progresso da própria conta. `GET /api/desafios/{jogo}/fases/{fase}` carrega uma fase desbloqueada; `POST` no mesmo endereço acrescido de `/responder` recebe uma lista de IDs em `itens`. Cada fase concede até 100 pontos; cada tentativa errada reduz 15, até um mínimo de 25. Somente a melhor pontuação por fase é mantida, sem acumular pontos por repetição. A tabela `desafio_fases` guarda as tentativas e conclusões por usuário. As 15 fases totalizam até 1.500 pontos.

Para testes no navegador, `node scripts/verificar_explorar.cjs` usa Edge headless com banco, contas e perfil isolados dentro de `.pytest_tmp_browser`. Ele verifica feed inicial, publicação com foto, navegação, jogos e adaptação ao celular, sem modificar contas reais. Os limites por arquivo não substituem os limites de armazenamento, backup e upload necessários ao hospedar o aplicativo.

## Editores e convites

Defina `SPECTRA_EDITOR_EMAILS` no ambiente do processo com os e-mails autorizados, separados por vírgula, e reinicie o servidor. Não há editor autorizado por padrão. O sistema lê variáveis de ambiente; copiar `.env.example` por si só não as carrega.

No PowerShell, antes de iniciar:

```powershell
$env:SPECTRA_EDITOR_EMAILS = 'seu-email@example.com'
.\.venv\Scripts\python.exe -m uvicorn spectra_link_guard.web.app:app --host 127.0.0.1 --port 8000
```

Ao entrar com esse e-mail, o blog exibe o formulário de convite. O editor gera um link e o compartilha com o especialista. O aplicativo não envia e-mail. O link vale sete dias, só pode ser aceito uma vez e exige uma sessão com o e-mail convidado. O acesso concedido permite publicar artigos. Convites são armazenados como hashes, sem o token original.

## Google

O botão compartilhado acima das abas de login e cadastro usa o OAuth existente. Sem configuração ele permanece visível, desabilitado e acompanhado de uma explicação. Configure `SPECTRA_GOOGLE_CLIENT_ID`, `SPECTRA_GOOGLE_CLIENT_SECRET` e `SPECTRA_GOOGLE_REDIRECT` no ambiente do servidor. A URI de retorno deve coincidir com a cadastrada no Google. Use o mesmo host no navegador e na URI: `localhost` e `127.0.0.1` não compartilham cookies.

O fluxo agora usa PKCE, nonce e contextos de uso único; a identidade vem de ID token validado pelo SDK oficial. Um e-mail igual ao de uma conta existente não cria vínculo automaticamente: entre por senha e use Conectar Google no próprio perfil, até dez minutos após entrar. O Google precisa confirmar o mesmo e-mail. O passo a passo está em [CONFIGURAR-GOOGLE.md](CONFIGURAR-GOOGLE.md).

Privilégios de editor e aceite de convite exigem e-mail verificado. Para liberar uma conta existente, confirme o e-mail por SMTP configurado ou conecte explicitamente a conta Google correspondente. Não marque e-mails como verificados sem comprovar sua titularidade. Prefira configurar editores por `SPECTRA_EDITOR_IDS`.

## Verificação

```powershell
python -m pytest -q --basetemp .pytest_tmp_suite -p no:cacheprovider
```

Os testes de comunidade usam banco temporário e verificam acesso autenticado, isolamento de mensagens, validação de foto, publicação, comentários e autorização e consumo dos convites.


A animacao do avatar usa geometria final fixa e transforma apenas translate3d/scale, sem animar left, top, width, height ou tamanho de fonte. Os fundos em canvas e os ornamentos CSS pausam durante o trajeto e retomam ao terminar. Cabecalho e tela compartilham uma unica consulta de perfil por carregamento. O teste de navegador tambem valida o voo com CPU limitada a quatro vezes mais lenta.
