/* Spectra — Laudo de Link.
 *
 * Consome só a própria API. Todo texto vindo do servidor entra por textContent:
 * a tela exibe strings escritas por golpistas (URLs, nomes de certificado) e
 * não pode virar vetor de XSS para quem a usa.
 */

const $ = (id) => document.getElementById(id);

/** Valor atual de um token de tokens.css (muda com o tema). */
function token(nome) {
  return getComputedStyle(document.documentElement).getPropertyValue(`--${nome}`).trim();
}

/* ══════════════════════════════════════════════════ o polígrafo
 *
 * O elemento-assinatura da tela. Não é um gráfico decorativo: o traço é
 * derivado dos caracteres da própria URL analisada — o mesmo link sempre
 * desenha a mesma onda, como uma assinatura. O nível de risco muda o
 * comportamento do instrumento: seguro respira devagar, malicioso rasga.
 */

function semente(texto) {
  let h = 2166136261;
  for (let i = 0; i < texto.length; i += 1) {
    h ^= texto.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function gerador(estado) {
  return () => {
    estado = (Math.imul(estado, 1664525) + 1013904223) >>> 0;
    return estado / 4294967296;
  };
}

class Poligrafo {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.tensao = 0;
    this.cor = token("texto-3");
    this.corMarcas = `rgb(${token("texto-rgb")} / .07)`;
    this.harmonicas = this.montarHarmonicas("spectra");
    this.t = 0;
    this.calmo = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    this.redimensionar = this.redimensionar.bind(this);
    window.addEventListener("resize", this.redimensionar, { passive: true });
    this.redimensionar();

    if (this.calmo) this.desenhar();
    else requestAnimationFrame(this.quadro.bind(this));
  }

  montarHarmonicas(texto) {
    const aleatorio = gerador(semente(texto));
    return Array.from({ length: 5 }, (_, i) => ({
      freq: 0.7 + aleatorio() * (1.6 + i * 1.5),
      fase: aleatorio() * Math.PI * 2,
      amp: (1 - i / 6) * (0.45 + aleatorio() * 0.55),
      vel: 0.18 + aleatorio() * 0.5,
    }));
  }

  configurar({ url, tensao, cor }) {
    if (url) this.harmonicas = this.montarHarmonicas(url);
    this.tensao = tensao;
    this.cor = cor;
    this.corMarcas = `rgb(${token("texto-rgb")} / .07)`;
    if (this.calmo) this.desenhar();
  }

  redimensionar() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const { width, height } = this.canvas.getBoundingClientRect();
    this.l = Math.max(width, 1);
    this.a = Math.max(height, 1);
    this.canvas.width = this.l * dpr;
    this.canvas.height = this.a * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (this.calmo) this.desenhar();
  }

  quadro() {
    this.t += 0.0125;
    this.desenhar();
    requestAnimationFrame(this.quadro.bind(this));
  }

  /** Papel milimetrado do instrumento: marcas verticais discretas. */
  marcasDeFundo(ctx) {
    ctx.strokeStyle = this.corMarcas;
    ctx.lineWidth = 1;
    for (let x = 0; x < this.l; x += 46) {
      const alto = x % 230 < 46 ? 13 : 6;
      ctx.beginPath();
      ctx.moveTo(Math.round(x) + 0.5, this.a - 20 - alto);
      ctx.lineTo(Math.round(x) + 0.5, this.a - 20);
      ctx.stroke();
    }
  }

  desenhar() {
    const ctx = this.ctx;
    const tensao = this.tensao;
    // Em tela estreita a manchete ocupa quase tudo: o traço desce para o rodapé
    // do bloco e perde peso, para nunca disputar legibilidade com o texto.
    const estreito = this.l < 760;
    const meio = this.a * (estreito ? 0.82 : 0.62);
    ctx.clearRect(0, 0, this.l, this.a);
    this.marcasDeFundo(ctx);

    // O traço some sob a manchete (à esquerda) e ganha corpo à direita.
    const fade = ctx.createLinearGradient(0, 0, this.l, 0);
    const forte = estreito ? "99" : "ff";
    const medio = estreito ? "66" : "cc";
    fade.addColorStop(0, "transparent");
    fade.addColorStop(0.42, this.cor + "26");
    fade.addColorStop(0.72, this.cor + medio);
    fade.addColorStop(1, this.cor + forte);
    ctx.strokeStyle = fade;
    ctx.lineWidth = 1.5 + tensao * 1.2;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    const base = this.a * (0.06 + tensao * 0.05);
    const passo = 3;
    const aleatorio = gerador(semente(String(Math.floor(this.t * 6))));

    // Fatias horizontais deslocadas: o "atrito" visual do estado malicioso.
    const fatias = tensao > 0.55 ? Math.floor(1 + tensao * 3) : 0;
    const cortes = [];
    for (let i = 0; i < fatias; i += 1) {
      const inicio = aleatorio() * this.l;
      cortes.push({
        de: inicio,
        ate: inicio + 40 + aleatorio() * 150,
        desloca: (aleatorio() - 0.5) * 46 * tensao,
      });
    }

    ctx.beginPath();
    for (let x = 0; x <= this.l; x += passo) {
      const u = x / this.l;
      let y = meio;

      for (const h of this.harmonicas) {
        y += Math.sin(u * Math.PI * 2 * h.freq + h.fase + this.t * h.vel) * base * h.amp;
      }

      if (tensao > 0.15) {
        // Ruído de alta frequência — quanto mais risco, mais a agulha treme.
        y += Math.sin(u * 240 + this.t * 9) * base * tensao * 0.3;
        y += (aleatorio() - 0.5) * base * tensao * 0.75;
      }

      if (tensao > 0.5) {
        // Picos: a agulha bate no fim de escala em pontos fixos da onda.
        const pico = Math.pow(Math.max(0, Math.sin(u * Math.PI * 2 * 3.5 + this.t * 0.6)), 26);
        y -= pico * base * 3.4 * tensao;
      }

      let px = x;
      for (const corte of cortes) {
        if (x >= corte.de && x <= corte.ate) px += corte.desloca;
      }

      if (x === 0) ctx.moveTo(px, y);
      else ctx.lineTo(px, y);
    }
    ctx.stroke();
  }
}

/* ══════════════════════════════════════════════════ apresentação */

const SENTENCA = {
  seguro: ["Nenhum sinal", "de fraude neste link"],
  baixo: ["Sinais fracos,", "nada grave"],
  atencao: ["Atenção:", "múltiplos sinais de alerta"],
  alto: ["Risco alto:", "não informe seus dados"],
  critico: ["Perigo:", "site malicioso detectado"],
};

const ETIQUETA = {
  seguro: "laudo concluído · sem apontamentos",
  baixo: "laudo concluído · apontamentos leves",
  atencao: "laudo concluído · com ressalvas",
  alto: "laudo concluído · desaconselhado",
  critico: "laudo concluído · não abra",
};

const PASTILHA = {
  seguro: "liberado",
  baixo: "liberado",
  atencao: "com ressalvas",
  alto: "desaconselhado",
  critico: "não abra",
};

const TENSAO = { seguro: 0.05, baixo: 0.2, atencao: 0.5, alto: 0.75, critico: 1 };

const ICONE_NIVEL = {
  seguro: "shield-check",
  baixo: "shield-check",
  atencao: "shield-alert",
  alto: "shield-x",
  critico: "octagon-alert",
};

// Item 7: classificação simplificada em 3 faixas, mapeada a partir do nível
// de risco já calculado e testado em pontuacao.py — não é um segundo placar.
const CLASSIFICACAO_3 = {
  seguro: "Seguro",
  baixo: "Seguro",
  atencao: "Suspeito",
  alto: "Perigoso",
  critico: "Perigoso",
};

/** Reprocessa os ícones lucide inseridos dinamicamente (veredito, checklist). */
function atualizarIcones() {
  if (window.lucide && typeof window.lucide.createIcons === "function") {
    window.lucide.createIcons();
  }
}

const NOME_PROVEDOR = {
  google_safe_browsing: "Google Safe Browsing",
  virustotal: "VirusTotal",
  phishtank: "PhishTank",
};

const ORDEM_GRAU = ["critica", "alta", "media", "baixa", "info"];

function elemento(tag, classe, texto) {
  const el = document.createElement(tag);
  if (classe) el.className = classe;
  if (texto !== undefined && texto !== null) el.textContent = String(texto);
  return el;
}

/** Marca um valor como alerta. A cor é o sinal visível, o triângulo do CSS é a
 *  forma, e este rótulo oculto é o que o leitor de tela ouve — nenhum dos três
 *  sozinho carrega a informação. */
function marcarAlerta(el, ativo, rotulo = "sinal de alerta") {
  el.classList.toggle("alerta", ativo);
  const antigo = el.querySelector(".oculto");
  if (antigo) antigo.remove();
  if (ativo) el.append(elemento("span", "oculto", ` — ${rotulo}`));
}

/** Acende as fontes (abaixo da busca) a partir do que a análise de fato consultou. */
function marcarFonte(chave, estado, descricao) {
  const li = document.querySelector(`.fonte[data-fonte="${chave}"]`);
  if (!li) return;
  li.dataset.estado = estado;
  const antigo = li.querySelector(".oculto");
  if (antigo) antigo.remove();
  li.append(elemento("span", "oculto", ` — ${descricao}`));
}

function corDoSinal() {
  return getComputedStyle(document.body).getPropertyValue("--sinal").trim() || token("texto-3");
}

function encurtar(texto, limite = 46) {
  const s = String(texto || "");
  return s.length > limite ? `${s.slice(0, limite - 1)}…` : s;
}

/** "31 anos", "8 meses", "2 dias" — a unidade que a pessoa usa para pensar. */
function idadeLegivel(dias) {
  if (dias === null || dias === undefined) return null;
  if (dias < 45) return `${dias} dia${dias === 1 ? "" : "s"}`;
  if (dias < 730) return `${Math.round(dias / 30)} meses`;
  return `${Math.floor(dias / 365)} anos`;
}

/* ── parecer em linguagem natural, montado só com o que foi de fato apurado */

function montarParecer(r) {
  const frases = [];
  const consultas = [
    r.tls ? "certificado" : null,
    r.registro ? "registro do domínio" : null,
    r.hospedagem ? "rede do servidor" : null,
    (r.reputacao || []).some((p) => p.status === "limpo" || p.status === "malicioso")
      ? "listas públicas de ameaça"
      : null,
  ].filter(Boolean);

  const n = r.achados.length;
  frases.push(
    consultas.length
      ? `Conferimos ${n} ${n === 1 ? "sinal" : "sinais"} entre a estrutura do endereço, ${consultas.join(", ")}.`
      : `Conferimos ${n} ${n === 1 ? "sinal" : "sinais"} na estrutura do endereço.`
  );

  if (r.registro && r.registro.idade_dias !== null && r.registro.idade_dias !== undefined) {
    const idade = idadeLegivel(r.registro.idade_dias);
    frases.push(
      r.registro.idade_dias <= 90
        ? `O domínio ${r.dominio_registravel} foi criado há ${idade}.`
        : `O domínio ${r.dominio_registravel} existe há ${idade}.`
    );
  }

  if (r.tls) {
    if (r.tls.disponivel && r.tls.cadeia_valida) frases.push("O certificado é válido.");
    else if (r.tls.disponivel) frases.push("O certificado não é confiável.");
    else frases.push("Não houve conexão segura para checar o certificado.");
  }

  const marcados = (r.reputacao || []).filter((p) => p.status === "malicioso");
  const limpos = (r.reputacao || []).filter((p) => p.status === "limpo");
  if (marcados.length) {
    frases.push(`Já foi denunciado em ${marcados.map((p) => NOME_PROVEDOR[p.provedor] || p.provedor).join(" e ")}.`);
  } else if (limpos.length) {
    frases.push(`Nenhuma denúncia em ${limpos.length} lista${limpos.length === 1 ? "" : "s"} pública${limpos.length === 1 ? "" : "s"}.`);
  }

  return frases.join(" ");
}

/* ── seções */

function renderVeredito(r) {
  const [inicio, resto] = SENTENCA[r.nivel] || SENTENCA.atencao;
  const sentenca = $("sentenca");

  const icone = $("veredito-icone");
  icone.replaceChildren();
  const i = document.createElement("i");
  i.setAttribute("data-lucide", ICONE_NIVEL[r.nivel] || "shield-question");
  icone.append(i);

  // A sentença se monta letra a letra: o veredito chega, não aparece pronto.
  // O trecho em destaque é animado à parte para manter a cor do nível.
  sentenca.replaceChildren();
  sentenca.setAttribute("aria-label", `${inicio} ${resto}`);

  const parteDestaque = elemento("span", "destaque");
  const parteResto = elemento("span", "");
  sentenca.append(parteDestaque, document.createTextNode(" "), parteResto);

  animarPorLetra(parteDestaque, inicio, { atrasoInicial: 0.05, passo: 0.026 });
  animarPorLetra(parteResto, resto, {
    atrasoInicial: 0.05 + inicio.length * 0.026,
    passo: 0.026,
  });
  parteDestaque.removeAttribute("aria-label");
  parteResto.removeAttribute("aria-label");

  $("etiqueta").textContent = ETIQUETA[r.nivel] || "laudo concluído";
  $("parecer").textContent = montarParecer(r);

  $("f-dominio").textContent = r.dominio_registravel || "—";
  $("f-host").textContent = r.host || "—";
  $("f-risco").textContent = `${r.risco}/100`;
  $("ficha").hidden = false;
}

function elo(papel, valor, classe) {
  const li = elemento("li", classe ? `elo ${classe}` : "elo");
  li.append(elemento("span", "elo-papel", papel), elemento("span", "elo-valor", valor));
  return li;
}

function renderCadeia(r) {
  const lista = $("cadeia");
  lista.replaceChildren();

  lista.append(elo("endereço recebido", encurtar(r.url_original, 58)));

  const encurtado = r.achados.some((a) => a.codigo === "encurtador");
  const desviado = r.achados.some((a) => a.codigo === "userinfo_no_host");

  if (desviado) {
    lista.append(elo("aparenta ir para", r.achados.find((a) => a.codigo === "userinfo_no_host").evidencia.antes_do_arroba));
  }

  lista.append(elo("quem responde", r.host || "—", encurtado ? "" : "destino"));

  if (encurtado) {
    lista.append(elo("destino final", "oculto pelo encurtador", "oculto-destino"));
  }
}

function renderEvidencias(r) {
  // idade do domínio
  const reg = r.registro;
  const idade = reg && reg.idade_dias !== null && reg.idade_dias !== undefined ? reg.idade_dias : null;
  const idadeValor = $("idade-valor");
  idadeValor.textContent = idade === null ? "sem dado" : idadeLegivel(idade);
  marcarAlerta(idadeValor, idade !== null && idade <= 90, "domínio recente");
  $("idade-apoio").textContent = idade !== null
    ? `Registrado em ${(reg.criado_em || "").slice(0, 10)}${reg.registrador ? ` · ${reg.registrador}` : ""}`
    : (reg && reg.erro) || "O registro público não respondeu.";

  // certificado
  const tls = r.tls;
  const certValor = $("cert-valor");
  let certTexto = "não checado";
  let certAlerta = false;
  if (tls) {
    if (!tls.disponivel) { certTexto = "sem conexão"; certAlerta = true; }
    else if (tls.cadeia_valida) certTexto = "válido";
    else { certTexto = "não confiável"; certAlerta = true; }
  }
  certValor.textContent = certTexto;
  marcarAlerta(certValor, certAlerta, "certificado com problema");
  $("cert-apoio").textContent = tls && tls.disponivel
    ? [tls.versao_tls, tls.emissor].filter(Boolean).join(" · ")
    : (tls && tls.erro) || "";

  // motores de ameaça
  const vt = (r.reputacao || []).find((p) => p.provedor === "virustotal");
  const motoresValor = $("motores-valor");
  if (vt && vt.total_motores) {
    motoresValor.textContent = `${vt.positivos}/${vt.total_motores}`;
    marcarAlerta(motoresValor, vt.positivos > 0, "apontado como nocivo");
    $("motores-apoio").textContent = vt.positivos > 0
      ? "motores classificam este endereço como nocivo"
      : "motores analisaram e nenhum apontou problema";
  } else {
    motoresValor.textContent = "sem dado";
    marcarAlerta(motoresValor, false);
    $("motores-apoio").textContent =
      "Nenhum motor consultado — falta a chave de API do VirusTotal no servidor.";
  }

  // e-mail e DNS
  const d = r.dns;
  const emailValor = $("email-valor");
  if (!d || !d.consultado) {
    emailValor.textContent = "sem dado";
    emailValor.classList.remove("alerta");
    $("email-apoio").textContent = (d && d.erro) || "DNS não consultado.";
  } else {
    // Conta o que falta, do ponto de vista de quem é dono do domínio.
    const faltando = [];
    if (d.mx.length && !d.spf) faltando.push("SPF");
    if (!d.dmarc) faltando.push("DMARC");
    if (!d.caa.length) faltando.push("CAA");
    emailValor.textContent = faltando.length ? `faltam ${faltando.length}` : "configurado";
    emailValor.classList.toggle("alerta", faltando.includes("SPF"));
    $("email-apoio").textContent = faltando.length
      ? `Sem ${faltando.join(", ")}${d.mx.length ? ` · MX em ${d.mx[0]}` : " · sem MX"}`
      : `SPF, DMARC e CAA publicados${d.mx.length ? ` · MX em ${d.mx[0]}` : ""}`;
  }

  // origem do servidor
  const hosp = r.hospedagem;
  const servidorValor = $("servidor-valor");
  if (hosp && hosp.ips && hosp.ips.length) {
    servidorValor.textContent = hosp.pais || hosp.rede || hosp.ips[0];
    $("servidor-apoio").textContent = [hosp.ips[0], hosp.rede, hosp.reverso].filter(Boolean).join(" · ");
  } else {
    servidorValor.textContent = "não resolve";
    $("servidor-apoio").textContent = (hosp && hosp.erro) || "O nome não aponta para nenhum servidor.";
  }
  marcarAlerta(servidorValor, !!(hosp && !hosp.ips.length), "nome não resolve");
}

function renderFontes(r) {
  marcarFonte("sintaxe", "consultada", "consultada");

  if (!r.tls) marcarFonte("tls", "ocioso", "não consultada");
  else if (r.tls.disponivel) marcarFonte("tls", "consultada", "consultada");
  else marcarFonte("tls", "indisponivel", "sem resposta");

  const reg = r.registro && !r.registro.erro;
  const dns = r.hospedagem && r.hospedagem.ips && r.hospedagem.ips.length;
  if (reg || dns) marcarFonte("rede", "consultada", "consultada");
  else if (r.registro || r.hospedagem) marcarFonte("rede", "indisponivel", "sem resposta");
  else marcarFonte("rede", "ocioso", "não consultada");
}

function renderSinais(r) {
  const lista = $("sinais");
  lista.replaceChildren();

  const ordenados = [...r.achados].sort(
    (a, b) => ORDEM_GRAU.indexOf(a.severidade) - ORDEM_GRAU.indexOf(b.severidade)
  );

  $("sinais-nota").textContent = ordenados.length
    ? "Em ordem de gravidade. A nota é a soma destes itens, nada além disso."
    : "Nenhum sinal disparou nesta análise.";

  ordenados.forEach((a, i) => {
    const item = elemento("li", "sinal entrar");
    item.style.animationDelay = `${i * 55}ms`;

    const grau = elemento("span", "grau", a.severidade);
    grau.dataset.grau = a.severidade;

    const cabeca = elemento("div", "sinal-cabeca");
    cabeca.append(
      grau,
      elemento("h3", "sinal-titulo", a.titulo),
      elemento("span", "sinal-codigo", a.codigo)
    );

    const corpo = elemento("div", "sinal-corpo");
    corpo.append(
      elemento("p", "sinal-detalhe", a.detalhe),
      elemento("p", "sinal-recomendacao", a.recomendacao)
    );

    item.append(cabeca, corpo);
    lista.append(item);
  });
}

/* ── checklist heurística (item 7/8) ───────────────────────────────────── */

let graficoPontuacao = null;

function renderChecklist(r) {
  const corpo = $("checklist-corpo");
  corpo.replaceChildren();

  const lista = r.checklist || [];
  const falhas = lista.filter((c) => !c.passou).length;

  $("checklist-resumo").textContent = lista.length
    ? `${lista.length - falhas} de ${lista.length} critérios sem apontamento`
    : "sem critérios avaliados";

  for (const c of lista) {
    const linha = elemento("tr");

    const tdRotulo = elemento("td", "", c.rotulo);

    const tdResultado = elemento("td");
    const resultado = elemento("span", `checklist-resultado ${c.passou ? "passou" : "falhou"}`);
    const i = document.createElement("i");
    i.setAttribute("data-lucide", c.passou ? "check-circle-2" : "x-circle");
    i.setAttribute("aria-hidden", "true");
    resultado.append(i, document.createTextNode(c.passou ? "Passou" : "Falhou"));
    tdResultado.append(resultado);

    const tdMotivo = elemento("td", "checklist-motivo", c.motivo);

    linha.append(tdRotulo, tdResultado, tdMotivo);
    corpo.append(linha);
  }

  atualizarIcones();
}

function renderGrafico(r, { animar = true } = {}) {
  if (animar) animarNumero($("pontuacao-numero"), r.risco);
  else $("pontuacao-numero").textContent = r.risco;
  $("pontuacao-classificacao").textContent = `${CLASSIFICACAO_3[r.nivel] || "—"} · estimativa`;

  if (!window.Chart) return; // CDN pode não ter carregado ainda em conexões muito lentas
  const cor = corDoSinal();
  const semMovimento = window.spectraMovimentoLigado && !window.spectraMovimentoLigado();

  if (graficoPontuacao) graficoPontuacao.destroy();
  graficoPontuacao = new Chart($("grafico-pontuacao"), {
    type: "doughnut",
    data: {
      labels: ["Pontuação", "Restante"],
      datasets: [
        {
          data: [r.risco, 100 - r.risco],
          backgroundColor: [cor, token("linha")],
          borderWidth: 0,
        },
      ],
    },
    options: {
      cutout: "76%",
      animation: semMovimento ? false : { duration: 550 },
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });
}

/* ══════════════════════════════════════════════════ fluxo */

const poligrafo = new Poligrafo($("poligrafo"));

// Atmosfera de fundo (caminhos.js). Opacidade baixa: aqui eles são o ambiente,
// não o instrumento — quem carrega significado é o polígrafo do veredito.
desenharCaminhosFlutuantes($("caminhos-a"), 1, { opacidade: 0.38 });
desenharCaminhosFlutuantes($("caminhos-b"), -1, { opacidade: 0.28 });

function avisar(mensagem) {
  const aviso = $("aviso");
  aviso.textContent = mensagem;
  aviso.hidden = !mensagem;
}

async function periciar(url) {
  const botao = $("enviar");
  botao.disabled = true;
  $("grade").setAttribute("aria-busy", "true");
  $("enviar-texto").textContent = "Periciando";
  $("etiqueta").textContent = "lendo o endereço…";
  $("pastilha").textContent = "periciando";
  avisar("");
  const quadroVeredito = $("q-veredito");
  quadroVeredito.style.setProperty("--altura-varredura", `${quadroVeredito.offsetHeight}px`);
  quadroVeredito.classList.add("varrendo");
  document.querySelectorAll(".fonte").forEach((fonte) => fonte.classList.add("pulsando"));

  try {
    const resp = await fetch("/api/analisar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const dados = await resp.json();

    if (!resp.ok) {
      avisar(dados.erro || dados.detail || "Não foi possível periciar este endereço.");
      $("etiqueta").textContent = "laudo interrompido";
      $("pastilha").textContent = "interrompido";
      return;
    }

    document.body.dataset.estado = dados.nivel;
    poligrafo.configurar({
      url: dados.url_original,
      tensao: TENSAO[dados.nivel] ?? 0.5,
      cor: corDoSinal(),
    });

    renderFontes(dados);
    laudoAtual = dados;
    $("copiloto-ctx").textContent = `${dados.host} · ${dados.risco}/100`;
    conversa.replaceChildren();  // laudo novo, conversa nova
    melhoriasAtuais = [];

    renderVeredito(dados);
    renderCadeia(dados);
    renderEvidencias(dados);
    renderSinais(dados);
    renderChecklist(dados);
    renderGrafico(dados);
    atualizarIcones();

    $("protocolo").textContent = `nº ${semente(dados.url_original).toString(16).slice(0, 6).toUpperCase()}`;
    $("pastilha").textContent = PASTILHA[dados.nivel] || "concluído";
    $("q-amostras").hidden = true;
    $("subnav-analise").hidden = false;
    for (const id of ["q-cadeia", "q-evidencias", "q-sinais", "q-checklist"]) $(id).hidden = false;
    const calmo = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    $("q-veredito").scrollIntoView({ behavior: calmo ? "auto" : "smooth", block: "start" });
  } catch (erro) {
    avisar(`Sem resposta do servidor: ${erro.message}`);
    $("etiqueta").textContent = "laudo interrompido";
    $("pastilha").textContent = "interrompido";
  } finally {
    $("q-veredito").classList.remove("varrendo");
    document.querySelectorAll(".fonte").forEach((fonte) => fonte.classList.remove("pulsando"));
    botao.disabled = false;
    $("grade").setAttribute("aria-busy", "false");
    $("enviar-texto").textContent = "Periciar";
  }
}

$("formulario").addEventListener("submit", (evento) => {
  evento.preventDefault();
  const url = $("url").value.trim();
  if (url) periciar(url);
});

for (const amostra of document.querySelectorAll(".amostra")) {
  amostra.addEventListener("click", () => {
    $("url").value = amostra.dataset.url;
    periciar(amostra.dataset.url);
  });
}

// Trocar o tema muda as cores dos tokens: o medidor e o polígrafo redesenham.
window.addEventListener("spectra:tema", () => {
  if (!laudoAtual) return;
  poligrafo.configurar({ tensao: TENSAO[laudoAtual.nivel] ?? 0.5, cor: corDoSinal() });
  renderGrafico(laudoAtual, { animar: false });
});

fetch("/api/saude")
  .then((r) => r.json())
  .then((s) => { $("versao").textContent = `v${s.versao}`; })
  .catch(() => {});

/* ══════════════════════════════════════════════════ copiloto do laudo
 *
 * Não é um chat genérico: ele só fala sobre o laudo que está na tela. Todas as
 * respostas são montadas a partir do relatório que o servidor devolveu — se
 * não houver dado, ele diz que não sabe em vez de inventar.
 */

let laudoAtual = null;

const copiloto = $("copiloto");
const conversa = $("copiloto-conversa");

function falar(texto, autor) {
  const bolha = elemento("p", `bolha ${autor}`, texto);
  conversa.append(bolha);
  conversa.scrollTop = conversa.scrollHeight;
}

function severidadeEmPalavras(nivel) {
  return {
    seguro: "não encontrou sinal de fraude",
    baixo: "encontrou sinais fracos",
    atencao: "encontrou sinais que pedem atenção",
    alto: "encontrou risco alto",
    critico: "encontrou sinais fortes de fraude",
  }[nivel] || "concluiu a análise";
}

// Última lista de melhorias oferecida, para o usuário poder pedir "detalhe 2".
let melhoriasAtuais = [];

function listarMelhorias(r) {
  melhoriasAtuais = window.sugerirMelhorias ? window.sugerirMelhorias(r) : [];
  if (!melhoriasAtuais.length) return "Não consegui montar sugestões para este laudo.";

  const linhas = melhoriasAtuais.map(
    (m, i) => `${i + 1}. [${m.prioridade}] ${m.titulo}`
  );
  return (
    `Para ${r.dominio_registravel}, ${melhoriasAtuais.length} ponto(s), do mais urgente ao menos:\n\n` +
    linhas.join("\n") +
    `\n\nPeça "detalhe 1" (ou qualquer número) para o passo a passo.`
  );
}

function detalharMelhoria(indice) {
  const m = melhoriasAtuais[indice - 1];
  if (!m) return `Só tenho ${melhoriasAtuais.length} item(ns) na lista. Peça de 1 a ${melhoriasAtuais.length}.`;
  return (
    `${indice}. ${m.titulo}  [${m.prioridade}]\n\n` +
    `${m.porque}\n\n` +
    `Como fazer:\n${m.como.map((c) => `• ${c}`).join("\n")}\n\n` +
    `Baseado em: ${m.origem}`
  );
}

function respostaSobreLaudo(pergunta) {
  if (!laudoAtual) {
    return "Ainda não há laudo aberto. Cole um link na barra de cima e eu explico o resultado — e digo o que dá para melhorar, se o site for seu.";
  }
  const p = pergunta.toLowerCase();
  const r = laudoAtual;
  const graves = r.achados.filter((a) => a.severidade === "critica" || a.severidade === "alta");

  // "detalhe 2" ou só "2" — precisa vir antes de tudo, senão outra intenção
  // captura a pergunta. Um número solto só conta se já houver lista aberta.
  if (melhoriasAtuais.length) {
    const soNumero = /^\s*(\d{1,2})\s*$/.exec(pergunta);
    const comPalavra = /(?:detalh|explic|passo|item|n[úu]mero)\D{0,14}(\d{1,2})/.exec(p);
    const escolhido = soNumero || comPalavra;
    if (escolhido) return detalharMelhoria(Number(escolhido[1]));
  }

  // Conselho para o DONO do site. Vem antes da intenção genérica de "o que
  // faço", que é a resposta para quem recebeu o link.
  if (/melhor|sugest|otimiz|meu site|meu dom[íi]nio|corrigir|arrumar|deixar seguro|recomenda/.test(p)) {
    return listarMelhorias(r);
  }

  if (/segur|confi|pode abrir|abrir|clicar/.test(p)) {
    const base = `A análise ${severidadeEmPalavras(r.nivel)} — nota ${r.risco} de 100.`;
    return r.risco >= 55
      ? `${base} Eu não abriria. ${graves[0] ? graves[0].recomendacao : ""}`
      : `${base} Mesmo assim, lembre: não achar sinal não é garantia. Um golpe criado hoje ainda não foi denunciado por ninguém e passa limpo.`;
  }

  if (/por que|porque|motivo|explica/.test(p)) {
    if (!graves.length) {
      return `Nada grave apareceu. O que pesou foi: ${r.achados.map((a) => a.titulo).join("; ")}.`;
    }
    return `O que mais pesou foi: ${graves[0].titulo}. ${graves[0].detalhe}`;
  }

  if (/o que fa|devo|como|resolv/.test(p)) {
    const passos = (graves.length ? graves : r.achados).map((a) => `• ${a.recomendacao}`);
    return passos.length
      ? `Recomendo:\n${passos.join("\n")}`
      : "Não há ação necessária para este link.";
  }

  if (/dono|quem|domínio|dominio|empresa|registr/.test(p)) {
    const reg = r.registro;
    const idade = reg && reg.idade_dias != null ? idadeLegivel(reg.idade_dias) : null;
    return idade
      ? `Quem controla a página é ${r.dominio_registravel}, um domínio que existe há ${idade}${reg.criado_em ? ` (registrado em ${reg.criado_em.slice(0, 10)})` : ""}.`
      : `Quem controla a página é ${r.dominio_registravel}. O registro público não devolveu a data de criação deste domínio.`;
  }

  if (/certificado|https|cadeado|ssl|tls/.test(p)) {
    const t = r.tls;
    if (!t) return "O certificado não foi consultado nesta análise.";
    if (!t.disponivel) return `Não deu para checar o certificado: ${t.erro}`;
    return `O certificado é ${t.cadeia_valida ? "válido" : "não confiável"}, emitido por ${t.emissor || "emissor não identificado"}, usando ${t.versao_tls}. Cadeado verde não quer dizer site honesto — só quer dizer que a conexão é criptografada.`;
  }

  if (/servidor|ip|país|pais|host/.test(p)) {
    const h = r.hospedagem;
    if (!h || !h.ips || !h.ips.length) return "O nome não resolveu para nenhum servidor.";
    return `O site responde em ${h.ips[0]}${h.pais ? `, numa rede registrada em ${h.pais}` : ""}${h.rede ? ` (${h.rede})` : ""}.`;
  }

  // Nenhuma intenção casou: a pergunta cita um sinal específico pelo nome?
  // Esta busca fica por último de propósito — palavras como "domínio" aparecem
  // no título dos achados e sequestrariam perguntas sobre registro e dono.
  const especifico = r.achados.find(
    (a) =>
      p.includes(a.codigo.replace(/_/g, " ")) ||
      a.titulo
        .toLowerCase()
        .split(" ")
        .filter((w) => w.length > 5)
        .some((w) => p.includes(w))
  );
  if (especifico) return `${especifico.detalhe} ${especifico.recomendacao}`;

  return `Sobre este link eu sei o seguinte: ${r.resumo} Pergunte sobre o certificado, o dono do domínio, o servidor, ou o que fazer agora.`;
}

const ATALHOS = [
  "Como melhoro esse site?",
  "Posso abrir esse link?",
  "Por que deu isso?",
  "Quem é o dono do domínio?",
];

function montarAtalhos() {
  const caixa = $("copiloto-atalhos");
  caixa.replaceChildren();
  for (const texto of ATALHOS) {
    const chip = elemento("button", "atalho", texto);
    chip.type = "button";
    chip.addEventListener("click", () => perguntar(texto));
    caixa.append(chip);
  }
}

function perguntar(texto) {
  const pergunta = texto.trim();
  if (!pergunta) return;
  falar(pergunta, "eu");
  $("copiloto-campo").value = "";
  setTimeout(() => falar(respostaSobreLaudo(pergunta), "bot"), 360);
}

function abrirCopiloto(abrir) {
  copiloto.hidden = !abrir;
  $("abrir-copiloto").setAttribute("aria-expanded", String(abrir));
  if (!abrir) {
    $("abrir-copiloto").focus();
    return;
  }
  if (!conversa.childElementCount) {
    falar(
      laudoAtual
        ? `Analisei ${laudoAtual.host}. ${laudoAtual.resumo}\n\nSe o site é seu, pergunte "como melhoro esse site?" que eu monto um plano.`
        : "Cole um link na barra de cima e eu explico, em português, o que a análise encontrou.",
      "bot"
    );
    montarAtalhos();
  }
  $("copiloto-campo").focus();
}

$("abrir-copiloto").addEventListener("click", () => abrirCopiloto(copiloto.hidden));
$("fechar-copiloto").addEventListener("click", () => abrirCopiloto(false));
$("copiloto-form").addEventListener("submit", (evento) => {
  evento.preventDefault();
  perguntar($("copiloto-campo").value);
});
document.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape" && !copiloto.hidden) abrirCopiloto(false);
});
