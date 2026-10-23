/* Spectra — Visão geral.
 *
 * Lê GET /api/painel/estatisticas (já agregado no servidor) e desenha os
 * indicadores e três gráficos:
 *
 *   * área dos últimos 30 dias (Chart.js), uma métrica por vez — análises ou
 *     risco médio, escolhida nos botões do topo. Nunca as duas no mesmo
 *     gráfico: dois eixos inventam uma correlação que os dados não têm;
 *   * barras radiais dos vereditos e barras dos sinais (graficos.js).
 *
 * Cores vêm dos tokens; tudo se redesenha quando o tema ou o movimento mudam.
 * Carregado com defer, depois do Chart.js e de graficos.js.
 */

const $ = (id) => document.getElementById(id);

const NIVEIS = ["seguro", "baixo", "atencao", "alto", "critico"];
const NOME_NIVEL = { seguro: "Sem sinais", baixo: "Baixo", atencao: "Atenção", alto: "Alto", critico: "Crítico" };

const FONTE_MONO = '"JetBrains Mono", ui-monospace, monospace';
const FONTE_CORPO = '"Inter", system-ui, sans-serif';

const METRICAS = {
  total: { nome: "Análises", sub: "Análises feitas por dia" },
  risco: { nome: "Risco médio", sub: "Nota média de risco por dia, de 0 a 100" },
};

let dados = null;
let metrica = "total";
let graficoTempo = null;

function cor(token, alfa = 1) {
  const canais = getComputedStyle(document.documentElement).getPropertyValue(`--${token}-rgb`).trim();
  return `rgb(${canais} / ${alfa})`;
}

function semMovimento() {
  return window.spectraMovimentoLigado && !window.spectraMovimentoLigado();
}

/** "10 set", "qua, 10 set": sem os pontos e o "de" do formato longo. */
function data(iso, opcoes) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("pt-BR", opcoes)
    .replaceAll(".", "").replaceAll(" de ", " ");
}

/** Média do período ponderada pelo número de análises de cada dia. */
function riscoDoPeriodo() {
  const dias = dados.por_dia.filter((d) => d.total);
  const analises = dias.reduce((soma, d) => soma + d.total, 0);
  if (!analises) return 0;
  return Math.round(dias.reduce((soma, d) => soma + d.total * d.risco_medio, 0) / analises);
}

/* ─────────────────────────────────────────────── área: últimos 30 dias */

/** Linha vertical que acompanha o cursor, atrás da área. */
const mira = {
  id: "mira",
  beforeDatasetsDraw(grafico) {
    const ativos = grafico.tooltip?.getActiveElements?.() || [];
    if (!ativos.length) return;
    const { ctx, chartArea } = grafico;
    const x = ativos[0].element.x;
    ctx.save();
    ctx.strokeStyle = cor("linha-forte");
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, chartArea.top);
    ctx.lineTo(x, chartArea.bottom);
    ctx.stroke();
    ctx.restore();
  },
};

function degrade({ chart }) {
  const { ctx, chartArea } = chart;
  if (!chartArea) return "transparent";
  const preenchimento = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
  preenchimento.addColorStop(0, cor("primaria-clara", 0.4));
  preenchimento.addColorStop(1, cor("primaria-clara", 0));
  return preenchimento;
}

function dica() {
  return {
    backgroundColor: cor("base-3"),
    borderColor: cor("linha-forte"),
    borderWidth: 1,
    cornerRadius: 6,
    caretSize: 0,
    padding: { x: 12, y: 9 },
    titleColor: cor("texto-3"),
    titleFont: { family: FONTE_MONO, size: 10, weight: "400" },
    titleMarginBottom: 6,
    bodyColor: cor("texto"),
    bodyFont: { family: FONTE_CORPO, size: 12, weight: "500" },
    usePointStyle: true,
    boxWidth: 7,
    boxHeight: 7,
    boxPadding: 6,
    callbacks: {
      title: ([item]) => data(dados.por_dia[item.dataIndex].dia, { weekday: "short", day: "2-digit", month: "short" }),
      label: (item) => metrica === "risco"
        ? ` Risco médio  ${item.parsed.y}/100`
        : ` Análises  ${item.parsed.y}`,
      labelColor: () => ({ borderColor: cor("primaria-clara"), backgroundColor: cor("primaria-clara") }),
      labelPointStyle: () => ({ pointStyle: "circle", rotation: 0 }),
    },
  };
}

function desenharTempo(animacao) {
  const risco = metrica === "risco";
  const linha = cor("primaria-clara");
  const eixo = { family: FONTE_MONO, size: 10 };

  return new Chart($("g-tempo"), {
    type: "line",
    data: {
      labels: dados.por_dia.map((d) => data(d.dia, { day: "2-digit", month: "short" })),
      datasets: [{
        label: METRICAS[metrica].nome,
        // Dia sem análise não tem risco: vira lacuna ligada, não um falso zero.
        data: dados.por_dia.map((d) => (risco ? (d.total ? d.risco_medio : null) : d.total)),
        borderColor: linha,
        borderWidth: 2,
        borderJoinStyle: "round",
        borderCapStyle: "round",
        // Monotônica: suave, mas nunca passa acima do pico nem abaixo de zero.
        cubicInterpolationMode: "monotone",
        fill: "origin",
        backgroundColor: degrade,
        pointRadius: 0,
        pointHitRadius: 12,
        pointHoverRadius: 5,
        pointHoverBackgroundColor: linha,
        pointHoverBorderColor: cor("base-2"),
        pointHoverBorderWidth: 2,
        spanGaps: true,
      }],
    },
    options: {
      maintainAspectRatio: false,
      animation: animacao,
      interaction: { mode: "index", intersect: false },
      layout: { padding: { top: 12, right: 4 } }, // folga para o ponto do pico não cortar
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: { color: cor("texto-3"), font: eixo, maxRotation: 0, autoSkip: true, maxTicksLimit: 7, padding: 8 },
        },
        y: {
          beginAtZero: true,
          max: risco ? 100 : undefined,
          border: { display: false },
          grid: { color: cor("linha"), drawTicks: false },
          ticks: { color: cor("texto-3"), font: eixo, precision: 0, maxTicksLimit: 5, padding: 10 },
        },
      },
      plugins: { legend: { display: false }, tooltip: dica() },
    },
    plugins: [mira],
  });
}

function descreverTempo() {
  const dias = dados.por_dia.filter((d) => d.total);
  const analises = dias.reduce((soma, d) => soma + d.total, 0);
  const texto = metrica === "risco"
    ? `Risco médio por dia nos últimos ${dados.por_dia.length} dias; média do período ${riscoDoPeriodo()} de 100.`
    : `Últimos ${dados.por_dia.length} dias: ${analises} análises em ${dias.length} dias.`;
  $("g-tempo").setAttribute("aria-label", texto);
}

function escolherMetrica(nova) {
  metrica = nova;
  document.querySelectorAll(".vg-metrica").forEach((botao) => {
    botao.setAttribute("aria-pressed", String(botao.dataset.metrica === nova));
  });
  $("vg-tempo-sub").textContent = METRICAS[nova].sub;
  if (!window.Chart || !dados || !dados.total) return;
  if (graficoTempo) graficoTempo.destroy();
  graficoTempo = desenharTempo(semMovimento() ? false : { duration: 400, easing: "easeOutQuart" });
  descreverTempo();
}

/* ─────────────────────────────────────────────── vereditos e sinais */

function desenharNiveis() {
  const itens = NIVEIS.map((nivel) => ({
    chave: nivel,
    nome: NOME_NIVEL[nivel],
    valor: dados.por_nivel[nivel] || 0,
    cor: spectraGraficos.corNivel(nivel),
  }));
  spectraGraficos.radial($("g-niveis"), itens, { rotulo: "análises" });

}

function desenharSinais() {
  const temSinais = dados.sinais_frequentes.length > 0;
  $("g-sinais").hidden = !temSinais;
  $("vg-sinais-vazio").hidden = temSinais;
  if (!temSinais) return;
  spectraGraficos.barras(
    $("g-sinais"),
    dados.sinais_frequentes.map((s) => ({ nome: s.rotulo, valor: s.vezes })),
    { total: dados.total },
  );
}

function desenhar() {
  if (graficoTempo) graficoTempo.destroy();
  graficoTempo = null;
  if (!dados || !dados.total) return;

  if (window.Chart) {
    graficoTempo = desenharTempo(semMovimento() ? false : { duration: 600, easing: "easeOutQuart" });
    descreverTempo();
  }
  if (window.spectraGraficos) {
    desenharNiveis();
    desenharSinais();
  }
}

async function carregar() {
  try {
    const resp = await fetch("/api/painel/estatisticas");
    if (resp.status === 401) {
      window.location.href = "/inicio?erro=entre_primeiro";
      return;
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    dados = await resp.json();
  } catch {
    avisarToast("Não foi possível carregar a visão geral.", "erro");
    return;
  } finally {
    $("visao").setAttribute("aria-busy", "false");
    document.querySelectorAll(".kpi-valor.esqueleto").forEach((el) => el.classList.remove("esqueleto"));
  }

  animarNumero($("kpi-total"), dados.total);
  animarNumero($("kpi-perigosos"), dados.perigosos);
  animarNumero($("kpi-risco"), dados.risco_medio);
  animarNumero($("kpi-seguras"), dados.pct_seguras, { sufixo: "%" });

  const noPeriodo = dados.por_dia.reduce((soma, d) => soma + d.total, 0);
  $("vg-m-total").textContent = noPeriodo.toLocaleString("pt-BR");
  $("vg-m-risco").textContent = riscoDoPeriodo();

  const vazio = !dados.total;
  $("vg-vazio").hidden = !vazio;
  document.querySelectorAll("[data-com-dados]").forEach((el) => { el.hidden = vazio; });
  desenhar();
}

document.querySelectorAll(".vg-metrica").forEach((botao) => {
  botao.addEventListener("click", () => {
    if (botao.dataset.metrica !== metrica) escolherMetrica(botao.dataset.metrica);
  });
});

window.addEventListener("spectra:tema", desenhar);
window.addEventListener("spectra:movimento", desenhar);
carregar();
