/* Plano de melhorias — o que o DONO do site pode fazer.
 *
 * O copiloto existente responde a quem recebeu um link ("posso abrir isso?").
 * Este módulo atende o outro lado: quem analisou o próprio site e quer saber o
 * que arrumar.
 *
 * REGRA DURA DESTE ARQUIVO: toda sugestão nasce de um dado que a análise
 * realmente coletou — um achado, o certificado, o RDAP ou o DNS. Nada de
 * conselho genérico de segurança apresentado como se fosse diagnóstico. O que
 * a análise passiva não enxerga (cabeçalhos, cookies, CORS, código) é
 * declarado como não verificado, nunca chutado.
 *
 * Cada sugestão carrega `origem`: de qual evidência ela saiu. É o que separa
 * recomendação de palpite.
 */

const PRIORIDADE_PESO = { alta: 0, media: 1, baixa: 2 };

/** Cria uma sugestão. `como` é uma lista de passos concretos. */
function sugestao(prioridade, titulo, porque, como, origem) {
  return { prioridade, titulo, porque, como, origem };
}

/* ── regras sobre o certificado e o transporte ─────────────────────────── */

function deTLS(r) {
  const fora = [];
  const t = r.tls;
  const tem = (codigo) => r.achados.some((a) => a.codigo === codigo);

  if (tem("sem_https")) {
    fora.push(
      sugestao(
        "alta",
        "Ligar HTTPS e redirecionar todo o tráfego",
        "Sem criptografia, senha e dado de cliente trafegam em texto puro, e navegador marca o site como “Não seguro”. Também derruba o ranqueamento.",
        [
          "Emita um certificado gratuito: sudo certbot --nginx -d " + (r.dominio_registravel || "seudominio.com.br"),
          "Redirecione 80 → 443 com return 301 https://$host$request_uri;",
          "Depois que estiver estável, ligue o HSTS: Strict-Transport-Security: max-age=31536000; includeSubDomains",
        ],
        "achado sem_https"
      )
    );
    return fora; // sem HTTPS, o resto das regras de certificado não se aplica
  }

  if (tem("certificado_expirado")) {
    fora.push(
      sugestao(
        "alta",
        "Renovar o certificado — ele já venceu",
        "Todo visitante vê a tela de “conexão não é particular”. Na prática o site está fora do ar para quem não ignora o aviso.",
        [
          "Renove agora: sudo certbot renew --force-renewal",
          "Recarregue o servidor: sudo systemctl reload nginx",
          "Confirme que o timer de renovação automática está ativo: systemctl list-timers | grep certbot",
        ],
        "achado certificado_expirado"
      )
    );
  } else if (tem("certificado_perto_do_vencimento")) {
    fora.push(
      sugestao(
        "alta",
        "Automatizar a renovação do certificado",
        `Vence em ${t?.dias_para_expirar} dia(s). Renovação manual é a causa mais comum de site fora do ar por certificado.`,
        [
          "Teste a renovação sem aplicar: sudo certbot renew --dry-run",
          "Garanta o timer: sudo systemctl enable --now certbot.timer",
        ],
        "achado certificado_perto_do_vencimento"
      )
    );
  }

  if (tem("certificado_invalido") || tem("certificado_autoassinado")) {
    fora.push(
      sugestao(
        "alta",
        "Corrigir a cadeia do certificado",
        "O certificado não é reconhecido pelas autoridades em que os navegadores confiam. Costuma ser cadeia intermediária faltando, não o certificado em si.",
        [
          "Sirva o fullchain, não só o cert: ssl_certificate /etc/letsencrypt/live/DOMINIO/fullchain.pem",
          "Verifique a cadeia: openssl s_client -connect " + (r.host || "seudominio") + ":443 -showcerts",
        ],
        t?.erro ? `certificado: ${t.erro}` : "achado certificado_invalido"
      )
    );
  }

  if (tem("certificado_host_divergente")) {
    fora.push(
      sugestao(
        "alta",
        "Incluir este host no certificado",
        `O certificado não cobre ${r.host}. Quem acessa por esse endereço leva aviso de segurança.`,
        [
          "Reemita cobrindo todos os nomes: certbot --nginx -d " + (r.dominio_registravel || "dominio") + " -d www." + (r.dominio_registravel || "dominio"),
          "Confira os SAN do certificado depois de reemitir.",
        ],
        "achado certificado_host_divergente"
      )
    );
  }

  if (tem("tls_obsoleto")) {
    fora.push(
      sugestao(
        "alta",
        "Desligar as versões antigas de TLS",
        `O servidor aceita ${t?.versao_tls}, descontinuado pela IETF (RFC 8996). Reprova em auditoria e em questionário de seguro.`,
        [
          "No nginx: ssl_protocols TLSv1.2 TLSv1.3;",
          "Recarregue e valide em ssllabs.com/ssltest",
        ],
        "achado tls_obsoleto"
      )
    );
  } else if (t?.disponivel && t.versao_tls && t.versao_tls !== "TLSv1.3") {
    fora.push(
      sugestao(
        "baixa",
        "Habilitar TLS 1.3",
        `O handshake fechou em ${t.versao_tls}. O 1.3 é mais rápido e corta cifras problemáticas.`,
        ["No nginx: ssl_protocols TLSv1.2 TLSv1.3;", "Exige OpenSSL 1.1.1 ou superior."],
        `certificado: ${t.versao_tls}`
      )
    );
  }

  if (tem("tls_indisponivel")) {
    fora.push(
      sugestao(
        "alta",
        "O servidor não respondeu na porta 443",
        "Não foi possível abrir conexão segura. Ou o site está fora do ar, ou o DNS aponta para outro lugar, ou o firewall bloqueia.",
        [
          "Confirme que o serviço está de pé e ouvindo em 443.",
          "Confira se o DNS aponta para o servidor certo.",
          "Verifique a regra de firewall / grupo de segurança.",
        ],
        r.tls?.erro ? `erro: ${r.tls.erro}` : "achado tls_indisponivel"
      )
    );
  }

  return fora;
}

/* ── regras sobre o domínio e a reputação ──────────────────────────────── */

function deDominio(r) {
  const fora = [];
  const tem = (codigo) => r.achados.some((a) => a.codigo === codigo);
  const dominio = r.dominio_registravel || "seu domínio";

  if (tem("listado_como_malicioso")) {
    const achado = r.achados.find((a) => a.codigo === "listado_como_malicioso");
    fora.push(
      sugestao(
        "alta",
        "Pedir revisão nas listas que marcaram o site",
        "Enquanto estiver listado, navegador mostra tela vermelha e e-mail com o link cai em spam. Resolver a causa não tira da lista sozinho — é preciso pedir revisão.",
        [
          "Descubra a causa antes de pedir revisão (site invadido, script de terceiro, redirecionamento).",
          "Google: Search Console → Segurança e ações manuais → Solicitar revisão.",
          "VirusTotal: peça reanálise na página da URL e conteste o motor que marcou.",
        ],
        achado ? `denunciado por: ${(achado.evidencia?.provedores || []).join(", ")}` : "achado listado_como_malicioso"
      )
    );
  }

  if (tem("dominio_recem_registrado") || tem("dominio_novo")) {
    const idade = r.registro?.idade_dias;
    fora.push(
      sugestao(
        "media",
        "Construir reputação — o domínio é novo",
        `Registrado há ${idade} dia(s). Filtro de spam e antivírus tratam domínio novo com desconfiança por padrão; não é falha sua, é o tempo.`,
        [
          "Cadastre no Google Search Console e no Bing Webmaster Tools.",
          "Publique SPF, DKIM e DMARC antes de disparar qualquer e-mail — domínio novo sem isso vai direto para spam.",
          "Evite disparo em massa nas primeiras semanas: aumente volume aos poucos.",
        ],
        `RDAP: criado em ${r.registro?.criado_em?.slice(0, 10) || "data não publicada"}`
      )
    );
  }

  if (tem("dominio_sosia") || tem("typosquatting")) {
    const achado = r.achados.find((a) => a.codigo === "dominio_sosia" || a.codigo === "typosquatting");
    const oficial = achado?.evidencia?.oficial;
    fora.push(
      sugestao(
        "alta",
        "Há um domínio parecido com o seu em circulação",
        `Este endereço imita ${oficial || "uma marca conhecida"}. Se a marca é sua, alguém está se passando por você — e seus clientes é que pagam.`,
        [
          "Registre defensivamente as variações mais óbvias (troca de letra, hífen, .com/.com.br).",
          "Denuncie o domínio ao registrador e ao Google Safe Browsing.",
          "Se houver uso de marca registrada, o caminho é notificação extrajudicial ao registrador.",
        ],
        achado ? `${achado.evidencia?.suspeito} ≈ ${oficial}` : "achado de sósia"
      )
    );
  }

  if (tem("tld_de_risco")) {
    const tld = r.achados.find((a) => a.codigo === "tld_de_risco")?.evidencia?.tld;
    fora.push(
      sugestao(
        "media",
        `A extensão .${tld} atrapalha a entrega`,
        "Essa extensão concentra abuso, então filtros de e-mail e de navegação a tratam com suspeita mesmo quando o site é legítimo.",
        [
          "Para um site que recebe cliente, prefira .com.br ou .com.",
          "Se precisar manter, redirecione o .${tld} para o domínio principal em vez de divulgá-lo.".replace("${tld}", tld),
        ],
        `domínio: ${dominio}`
      )
    );
  }

  return fora;
}

/* ── regras sobre a forma das URLs públicas ────────────────────────────── */

function deEstrutura(r) {
  const fora = [];
  const tem = (codigo) => r.achados.some((a) => a.codigo === codigo);

  if (tem("url_embutida")) {
    fora.push(
      sugestao(
        "alta",
        "Fechar o redirecionamento aberto",
        "A URL leva outro endereço nos parâmetros. Se o servidor redireciona para o que vier ali, qualquer um usa o seu domínio para levar vítimas a um site de golpe — e a culpa cai na sua reputação.",
        [
          "Nunca redirecione para valor vindo da query sem validar.",
          "Mantenha uma lista de destinos permitidos, ou aceite apenas caminhos relativos.",
          "Se for rastreamento de clique, assine o destino e verifique a assinatura.",
        ],
        "achado url_embutida"
      )
    );
  }

  if (tem("palavras_isca")) {
    const termos = r.achados.find((a) => a.codigo === "palavras_isca")?.evidencia?.termos || [];
    fora.push(
      sugestao(
        "baixa",
        "Repensar as palavras no caminho da URL",
        `O caminho usa ${termos.slice(0, 3).map((t) => `“${t}”`).join(", ")} — os mesmos termos que campanhas de phishing usam. Filtros pontuam isso, mesmo em site legítimo.`,
        [
          "Prefira /conta, /acesso ou /entrar a caminhos que juntem senha, verificação e urgência.",
          "Evite montar URL com o CPF ou o e-mail do cliente no caminho.",
        ],
        "achado palavras_isca"
      )
    );
  }

  if (tem("subdominios_excessivos")) {
    fora.push(
      sugestao(
        "baixa",
        "Encurtar a cadeia de subdomínios",
        "Muitos níveis empurram o domínio real para fora da tela no celular — é exatamente a técnica que golpes usam, e o seu link fica parecido com um.",
        ["Use no máximo um nível (app.seudominio.com.br).", "Deixe o domínio principal legível no começo da barra."],
        "achado subdominios_excessivos"
      )
    );
  }

  if (tem("encurtador")) {
    fora.push(
      sugestao(
        "media",
        "Não usar encurtador em link de marca",
        "O cliente não vê para onde vai, e você treina ele a clicar em link opaco — que é o que o golpista precisa.",
        [
          "Publique o link completo, ou use um encurtador no seu próprio domínio.",
          "Em SMS e WhatsApp, o domínio visível é o que dá confiança.",
        ],
        "achado encurtador"
      )
    );
  }

  return fora;
}

/* ── regras sobre DNS e e-mail ─────────────────────────────────────────── */

function deDNS(r) {
  const fora = [];
  const d = r.dns;
  const tem = (codigo) => r.achados.some((a) => a.codigo === codigo);
  const dominio = r.dominio_registravel || "seudominio.com.br";

  if (tem("dominio_suspenso")) {
    fora.push(
      sugestao(
        "alta",
        "Resolver a suspensão do domínio no registro",
        `O registry marcou o domínio como ${(r.registro?.status || []).join(", ")}. Nesse estado ele para de resolver e o site some da internet.`,
        [
          "Fale com o registrador: costuma ser pagamento pendente ou dado cadastral desatualizado.",
          "Se foi denúncia de abuso, resolva a causa antes de pedir a liberação.",
        ],
        `RDAP status: ${(r.registro?.status || []).join(", ")}`
      )
    );
  }

  if (r.registro?.dias_para_expirar != null && r.registro.dias_para_expirar >= 0 && r.registro.dias_para_expirar <= 45) {
    fora.push(
      sugestao(
        "alta",
        "Renovar o domínio — ele vence em breve",
        `Faltam ${r.registro.dias_para_expirar} dia(s). Domínio que expira sai do ar e pode ser registrado por outra pessoa.`,
        [
          "Renove agora e ative a renovação automática no registrador.",
          "Confirme que o e-mail de contato do domínio é lido por alguém.",
        ],
        `RDAP: vence em ${(r.registro.expira_em || "").slice(0, 10)}`
      )
    );
  }

  if (!d || !d.consultado) return fora;

  if (tem("sem_spf")) {
    fora.push(
      sugestao(
        "alta",
        "Publicar SPF — hoje qualquer um manda e-mail no seu nome",
        "O domínio recebe e-mail mas não declara quem pode enviar por ele. É a porta aberta para alguém aplicar golpe usando o nome da sua empresa, e os e-mails chegam parecendo legítimos.",
        [
          `Crie um TXT em ${dominio} com: v=spf1 include:SEU_PROVEDOR -all`,
          "Liste todos os serviços que enviam por você (e-mail, ERP, ferramenta de marketing).",
          "Termine com -all só depois de conferir que nada legítimo ficou de fora.",
        ],
        `MX ativo (${(d.mx || []).slice(0, 2).join(", ")}) e nenhum registro SPF`
      )
    );
  }

  if (tem("sem_dmarc")) {
    fora.push(
      sugestao(
        "media",
        "Publicar DMARC para bloquear e-mail falsificado",
        "O DMARC diz ao Gmail e ao Outlook o que fazer quando alguém falsifica seu domínio. Sem ele, a falsificação é entregue normalmente na caixa do seu cliente.",
        [
          `Crie um TXT em _dmarc.${dominio} com: v=DMARC1; p=none; rua=mailto:dmarc@${dominio}`,
          "Acompanhe os relatórios por algumas semanas para achar o que envia legitimamente.",
          "Depois suba para p=quarantine e então p=reject.",
        ],
        "nenhum registro em _dmarc"
      )
    );
  } else if (tem("dmarc_permissivo")) {
    fora.push(
      sugestao(
        "media",
        "Endurecer o DMARC — ele está só observando",
        "Está em p=none, que gera relatório mas entrega o e-mail falsificado assim mesmo.",
        ["Passe para p=quarantine e, depois de estabilizar, p=reject."],
        `DMARC atual: ${(d.dmarc || "").slice(0, 60)}`
      )
    );
  }

  if (tem("sem_caa")) {
    fora.push(
      sugestao(
        "baixa",
        "Publicar CAA para limitar quem emite certificado",
        "Sem CAA, qualquer autoridade certificadora do mundo pode emitir um certificado válido para o seu domínio — inclusive para quem conseguir enganá-la.",
        [`Crie um CAA em ${dominio}: 0 issue "letsencrypt.org"`, "Inclua todas as CAs que você realmente usa."],
        "nenhum registro CAA"
      )
    );
  }

  if (r.registro && r.registro.dnssec === false) {
    fora.push(
      sugestao(
        "baixa",
        "Considerar DNSSEC",
        "Sem DNSSEC, respostas de DNS podem ser falsificadas no caminho, levando seu visitante a outro servidor sem que nada pareça errado.",
        ["Verifique se o seu registrador e o provedor de DNS suportam.", "No Registro.br é uma chave por domínio, na área de DNS."],
        "RDAP: delegationSigned ausente"
      )
    );
  }

  return fora;
}

/* ── o que a análise passiva não consegue ver ──────────────────────────── */

function limites(r) {
  return sugestao(
    "media",
    "O que esta análise não conseguiu verificar",
    "A verificação é passiva: ela lê o endereço, o certificado e registros públicos, mas não busca o conteúdo do site. Então nada aqui diz respeito a cabeçalhos, cookies, CORS, formulários ou código.",
    [
      "Verificado: certificado, registro do domínio, DNS, SPF, DMARC, CAA e listas públicas.",
      "Não verificado: HSTS, Content-Security-Policy, X-Content-Type-Options.",
      "Não verificado: flags HttpOnly/Secure/SameSite nos cookies de sessão.",
      "Não verificado: CORS, rotas administrativas expostas, injeção, XSS.",
      "Para cobrir isso é preciso uma varredura ativa, com autorização do dono do site.",
    ],
    "escopo da análise passiva"
  );
}

/* ── montagem ──────────────────────────────────────────────────────────── */

/** Devolve as sugestões ordenadas por prioridade. */
function sugerirMelhorias(relatorio) {
  if (!relatorio) return [];

  const lista = [
    ...deTLS(relatorio),
    ...deDominio(relatorio),
    ...deDNS(relatorio),
    ...deEstrutura(relatorio),
  ];

  // Nada a apontar: registra o que está bem, sem inventar problema.
  if (!lista.length) {
    const t = relatorio.tls;
    const bons = [];
    if (t?.cadeia_valida) bons.push("o certificado é válido");
    if (t?.versao_tls === "TLSv1.3") bons.push("o transporte usa TLS 1.3");
    if (relatorio.registro?.idade_dias >= 730) bons.push("o domínio tem histórico");
    lista.push(
      sugestao(
        "baixa",
        "Nada a corrigir no que foi verificado",
        bons.length
          ? `Dentro do escopo passivo, ${bons.join(", ")}.`
          : "Dentro do escopo passivo, nenhum problema apareceu.",
        ["Mantenha a renovação do certificado automatizada.", "Revise de novo depois de qualquer mudança de infraestrutura."],
        "nenhum achado de severidade relevante"
      )
    );
  }

  // Ordena só as recomendações de verdade; a ressalva de escopo é rodapé e
  // entra sempre por último, senão ela passa na frente do "nada a corrigir".
  lista.sort((a, b) => PRIORIDADE_PESO[a.prioridade] - PRIORIDADE_PESO[b.prioridade]);
  lista.push(limites(relatorio));
  return lista;
}

window.sugerirMelhorias = sugerirMelhorias;
