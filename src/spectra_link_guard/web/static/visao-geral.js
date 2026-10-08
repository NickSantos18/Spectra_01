/* Spectra — Visão geral.
 *
 * Lê GET /api/painel/estatisticas (já agregado no servidor) e desenha os
 * indicadores e três gráficos. Cores vêm dos tokens; os gráficos se
 * redesenham quando o tema ou o movimento mudam. Carregado com defer, depois
 * do Chart.js.
 */

const $ = (id) => document.getElementById(id);

const NIVEIS = ["seguro", "baixo", "atencao", "alto", "critico"];
const NOME_NIVEL = { seguro: "Seguro", baixo: "Baixo", atencao: "Atenção", alto: "Alto", critico: "Crítico" };
const COR_NIVEL = {
  seguro: ["secundaria", 1],
  baixo: ["primaria-clara", 1],
  atencao: ["terciaria", 1],
  alto: ["perigo", 0.6],
  critico: ["perigo", 1],
};

let dados = null;
let graficos = [];

function cor(token, alfa = 1) {
  const canais = getComputedStyle(document.documentElement).getPropertyValue(`--${token}-rgb`).trim();
  return `rgb(${canais} / ${alfa})`;
}

function semMovimento() {
  return window.spectraMovimentoLigado && !window.spectraMovimentoLigado();
}

function diaCurto(iso) {
  const [, mes, dia] = iso.split("-");
  return `${dia}/${mes}`;
}

function graficoTempo(animacao) {
  return new Chart($("g-tempo"), {
    data: {
      labels: dados.por_dia.map((d) => diaCurto(d.dia)),
      datasets: [
        {
          type: "bar", label: "Análises", order: 2, yAxisID: "y",
          data: dados.por_dia.map((d) => d.total),
          backgroundColor: cor("primaria", 0.55), borderRadius: 3,
        },
        {
          type: "line", label: "Risco médio", order: 1, yAxisID: "y1",
          data: dados.por_dia.map((d) => (d.total ? d.risco_medio : null)),
          borderColor: cor("terciaria"), backgroundColor: cor("terciaria"),
          pointRadius: 2, tension: 0.3, spanGaps: true,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      animation: animacao,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 8 } },
        y: { beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: "análises" } },
        y1: {
          position: "right", min: 0, max: 100,
          grid: { drawOnChartArea: false }, title: { display: true, text: "risco" },
        },
      },
      plugins: { legend: { labels: { boxWidth: 12 } } },
    },
  });
}

function graficoNiveis(animacao) {
  return new Chart($("g-niveis"), {
    type: "doughnut",
    data: {
      labels: NIVEIS.map((n) => NOME_NIVEL[n]),
      datasets: [{
        data: NIVEIS.map((n) => dados.por_nivel[n] || 0),
        backgroundColor: NIVEIS.map((n) => cor(...COR_NIVEL[n])),
        borderWidth: 0,
      }],
    },
    options: {
      maintainAspectRatio: false,
      cutout: "62%",
      animation: animacao,
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12 } } },
    },
  });
}

function graficoSinais(animacao) {
  return new Chart($("g-sinais"), {
    type: "bar",
    data: {
      labels: dados.sinais_frequentes.map((s) => s.rotulo),
      datasets: [{
        label: "Vezes",
        data: dados.sinais_frequentes.map((s) => s.vezes),
        backgroundColor: cor("perigo", 0.55), borderRadius: 3,
      }],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      animation: animacao,
      scales: { x: { beginAtZero: true, ticks: { precision: 0 } }, y: { grid: { display: false } } },
      plugins: { legend: { display: false } },
    },
  });
}

/** Os canvas são imagens para o leitor de tela: o rótulo carrega os números. */
function descreverGraficos() {
  const niveis = NIVEIS.map((n) => `${dados.por_nivel[n] || 0} ${NOME_NIVEL[n].toLowerCase()}`).join(", ");
  $("g-niveis").setAttribute("aria-label", `Distribuição de vereditos: ${niveis}.`);

  const sinais = dados.sinais_frequentes.map((s) => `${s.rotulo}: ${s.vezes}`).join("; ");
  $("g-sinais").setAttribute("aria-label", sinais
    ? `Sinais mais frequentes: ${sinais}.`
    : "Nenhum sinal de risco registrado ainda.");

  const dias = dados.por_dia.filter((d) => d.total);
  const totalPeriodo = dias.reduce((soma, d) => soma + d.total, 0);
  $("g-tempo").setAttribute("aria-label",
    `Últimos ${dados.por_dia.length} dias: ${totalPeriodo} análises em ${dias.length} dias.`);
}

function desenhar() {
  graficos.forEach((grafico) => grafico.destroy());
  graficos = [];
  if (!window.Chart || !dados || !dados.total) return;

  Chart.defaults.color = cor("texto-3");
  Chart.defaults.borderColor = cor("linha");
  Chart.defaults.font.family = '"Inter", system-ui, sans-serif';
  const animacao = semMovimento() ? false : { duration: 700 };

  graficos.push(graficoTempo(animacao), graficoNiveis(animacao));
  const temSinais = dados.sinais_frequentes.length > 0;
  if (temSinais) graficos.push(graficoSinais(animacao));
  $("vg-sinais-vazio").hidden = temSinais;
  descreverGraficos();
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

  const vazio = !dados.total;
  $("vg-vazio").hidden = !vazio;
  document.querySelectorAll("[data-com-dados]").forEach((el) => { el.hidden = vazio; });
  desenhar();
}

window.addEventListener("spectra:tema", desenhar);
window.addEventListener("spectra:movimento", desenhar);
carregar();
