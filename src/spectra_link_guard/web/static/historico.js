/* Spectra — Histórico.
 *
 * Consome GET /api/painel/historico (lista completa da sessão, até 50 itens)
 * e DELETE /api/painel/{id} (já existia, usado pelo laudo). Busca e filtro
 * são só no cliente — a lista já é pequena e fica toda em memória.
 */

const $ = (id) => document.getElementById(id);

const NOME_NIVEL = { seguro: "seguro", baixo: "baixo", atencao: "atenção", alto: "alto", critico: "crítico" };
const TOKEN_NIVEL = {
  seguro: "secundaria", baixo: "secundaria", atencao: "terciaria", alto: "perigo", critico: "perigo",
};

function corNivel(nivel) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(`--${TOKEN_NIVEL[nivel]}`).trim();
}

let itensTodos = [];
let graficoHist = null;

function elemento(tag, classe, texto) {
  const el = document.createElement(tag);
  if (classe) el.className = classe;
  if (texto !== undefined && texto !== null) el.textContent = String(texto);
  return el;
}

function formatarQuando(iso) {
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso || "—";
  }
}

function itensFiltrados() {
  const busca = $("hist-busca").value.trim().toLowerCase();
  const filtro = $("hist-filtro").value;
  return itensTodos.filter((item) => {
    if (filtro && item.nivel !== filtro) return false;
    if (!busca) return true;
    return (item.host || "").toLowerCase().includes(busca) || (item.dominio || "").toLowerCase().includes(busca);
  });
}

async function apagar(id) {
  try {
    await fetch(`/api/painel/${id}`, { method: "DELETE" });
  } catch {
    /* segue mesmo se a chamada falhar: a linha some da UI, próxima carga sincroniza */
  }
  itensTodos = itensTodos.filter((i) => i.id !== id);
  renderizarTudo();
}

function linhaHist(item) {
  const tr = elemento("tr");

  tr.append(elemento("td", "mono", formatarQuando(item.quando)));
  tr.append(elemento("td", "mono copiavel", item.host || "—"));
  tr.append(elemento("td", "mono copiavel", item.dominio || "—"));

  const tdVeredito = elemento("td");
  const badge = elemento("span", "hist-veredito", NOME_NIVEL[item.nivel] || item.nivel);
  badge.dataset.nivel = item.nivel;
  tdVeredito.append(badge);
  tr.append(tdVeredito);

  tr.append(elemento("td", "mono", `${item.risco}/100`));

  const tdAcao = elemento("td");
  const botao = elemento("button", "hist-apagar");
  botao.type = "button";
  botao.setAttribute("aria-label", `Apagar análise de ${item.host || "item"} do histórico`);
  const i = document.createElement("i");
  i.setAttribute("data-lucide", "trash-2");
  i.setAttribute("aria-hidden", "true");
  botao.append(i);
  botao.addEventListener("click", () => apagar(item.id));
  tdAcao.append(botao);
  tr.append(tdAcao);

  return tr;
}

function renderizarTabela() {
  const filtrados = itensFiltrados();
  const corpo = $("hist-corpo");
  corpo.replaceChildren();
  for (const item of filtrados) corpo.append(linhaHist(item));
  $("hist-vazio").hidden = filtrados.length > 0;
  $("hist-contagem").textContent = `${filtrados.length} de ${itensTodos.length}`;
  if (window.lucide) window.lucide.createIcons();
}

function renderizarResumo() {
  $("hist-total").textContent = `${itensTodos.length} análise${itensTodos.length === 1 ? "" : "s"}`;

  const contagem = { seguro: 0, baixo: 0, atencao: 0, alto: 0, critico: 0 };
  for (const item of itensTodos) contagem[item.nivel] = (contagem[item.nivel] || 0) + 1;

  const legenda = $("hist-legenda");
  legenda.replaceChildren();
  for (const nivel of Object.keys(contagem)) {
    const li = elemento("li");
    const ponto = elemento("span", "ponto");
    ponto.style.background = corNivel(nivel);
    li.append(ponto, elemento("span", "", NOME_NIVEL[nivel]), elemento("span", "qtd", contagem[nivel]));
    legenda.append(li);
  }

  if (!window.Chart) return;
  const semMovimento = window.spectraMovimentoLigado && !window.spectraMovimentoLigado();
  if (graficoHist) graficoHist.destroy();
  graficoHist = new Chart($("hist-grafico"), {
    type: "doughnut",
    data: {
      labels: Object.keys(contagem).map((n) => NOME_NIVEL[n]),
      datasets: [{ data: Object.values(contagem), backgroundColor: Object.keys(contagem).map(corNivel), borderWidth: 0 }],
    },
    options: {
      cutout: "62%",
      animation: semMovimento ? false : { duration: 500 },
      plugins: { legend: { display: false } },
    },
  });
}

function renderizarTudo() {
  renderizarResumo();
  renderizarTabela();
}

async function carregar() {
  try {
    const resp = await fetch("/api/painel/historico");
    if (resp.status === 401) {
      window.location.href = "/inicio?erro=entre_primeiro";
      return;
    }
    const dados = await resp.json();
    itensTodos = dados.itens || [];
  } catch {
    itensTodos = [];
  }
  renderizarTudo();
}

$("hist-busca").addEventListener("input", renderizarTabela);
$("hist-filtro").addEventListener("change", renderizarTabela);

window.addEventListener("spectra:tema", renderizarResumo);
carregar();
