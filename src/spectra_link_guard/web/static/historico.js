/* Spectra — Histórico.
 *
 * Consome a API por usuário: GET /api/painel/historico, DELETE
 * /api/painel/{id} e DELETE /api/painel (apagar tudo). Busca e filtro rodam
 * no cliente: a lista tem no máximo 500 itens. Sem sessão a API responde 401
 * e a tela volta para a entrada.
 */

const $ = (id) => document.getElementById(id);

const NOME_NIVEL = { seguro: "seguro", baixo: "baixo", atencao: "atenção", alto: "alto", critico: "crítico" };
const TOKEN_NIVEL = {
  seguro: "secundaria", baixo: "secundaria", atencao: "terciaria", alto: "perigo", critico: "perigo",
};

let itensTodos = [];
let graficoHist = null;

function corNivel(nivel) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(`--${TOKEN_NIVEL[nivel]}`).trim();
}

function elemento(tag, classe, texto) {
  const el = document.createElement(tag);
  if (classe) el.className = classe;
  if (texto !== undefined && texto !== null) el.textContent = String(texto);
  return el;
}

function celula(rotulo, classe, texto) {
  const td = elemento("td", classe, texto);
  td.dataset.rotulo = rotulo;
  return td;
}

function formatarQuando(iso) {
  const data = new Date(iso);
  return Number.isNaN(data.getTime())
    ? iso
    : data.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function voltarParaEntrada() {
  window.location.href = "/inicio?erro=entre_primeiro";
}

function itensFiltrados() {
  const busca = $("hist-busca").value.trim().toLowerCase();
  const filtro = $("hist-filtro").value;
  return itensTodos.filter((item) => {
    if (filtro && item.nivel !== filtro) return false;
    if (!busca) return true;
    return (item.host || "").toLowerCase().includes(busca)
      || (item.dominio || "").toLowerCase().includes(busca);
  });
}

async function apagar(item) {
  let resp;
  try {
    resp = await fetch(`/api/painel/${item.id}`, { method: "DELETE" });
  } catch {
    avisarToast("Sem resposta do servidor. Tente de novo.", "erro");
    return;
  }
  if (resp.status === 401) return voltarParaEntrada();
  if (!resp.ok && resp.status !== 404) {
    avisarToast("Não foi possível apagar esta análise.", "erro");
    return;
  }
  itensTodos = itensTodos.filter((i) => i.id !== item.id);
  renderizarTudo();
  avisarToast(`Análise de ${item.host || "link"} apagada.`, "ok");
}

async function apagarTudo() {
  let resp;
  try {
    resp = await fetch("/api/painel", { method: "DELETE" });
  } catch {
    avisarToast("Sem resposta do servidor. Tente de novo.", "erro");
    return;
  }
  if (resp.status === 401) return voltarParaEntrada();
  if (!resp.ok) {
    avisarToast("Não foi possível apagar o histórico.", "erro");
    return;
  }
  itensTodos = [];
  renderizarTudo();
  avisarToast("Histórico apagado.", "ok");
}

function linhaHist(item) {
  const tr = elemento("tr");
  tr.append(celula("Quando", "mono", formatarQuando(item.quando)));
  tr.append(celula("Host", "mono copiavel", item.host || "(sem host)"));
  tr.append(celula("Domínio", "mono copiavel", item.dominio || "(sem domínio)"));

  const tdVeredito = celula("Veredito");
  const selo = elemento("span", "hist-veredito", NOME_NIVEL[item.nivel] || item.nivel);
  selo.dataset.nivel = item.nivel;
  tdVeredito.append(selo);
  tr.append(tdVeredito);

  tr.append(celula("Nota", "mono", `${item.risco}/100`));

  const tdAcao = celula("Ações");
  const botao = elemento("button", "hist-apagar");
  botao.type = "button";
  botao.setAttribute("aria-label", `Apagar análise de ${item.host || "link"} do histórico`);
  const icone = document.createElement("i");
  icone.setAttribute("data-lucide", "trash-2");
  icone.setAttribute("aria-hidden", "true");
  botao.append(icone);
  botao.addEventListener("click", () => apagar(item));
  tdAcao.append(botao);
  tr.append(tdAcao);

  return tr;
}

function renderizarTabela() {
  const filtrados = itensFiltrados();
  $("hist-corpo").replaceChildren(...filtrados.map(linhaHist));
  $("hist-vazio").hidden = filtrados.length > 0;
  $("hist-contagem").textContent = `${filtrados.length} de ${itensTodos.length}`;
  $("hist-apagar-tudo").disabled = itensTodos.length === 0;
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
      datasets: [{
        data: Object.values(contagem),
        backgroundColor: Object.keys(contagem).map(corNivel),
        borderWidth: 0,
      }],
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

function esqueletoTabela(linhas = 4) {
  const corpo = $("hist-corpo");
  corpo.replaceChildren();
  for (let i = 0; i < linhas; i += 1) {
    const tr = elemento("tr");
    tr.setAttribute("aria-hidden", "true");
    for (let j = 0; j < 6; j += 1) {
      const td = elemento("td");
      td.append(elemento("span", "esqueleto esqueleto-linha", "carregando"));
      tr.append(td);
    }
    corpo.append(tr);
  }
}

function falhaAoCarregar() {
  avisarToast("Não foi possível carregar o histórico.", "erro");
  itensTodos = [];
  renderizarTudo();
}

async function carregar() {
  esqueletoTabela();
  let resp;
  try {
    resp = await fetch("/api/painel/historico");
  } catch {
    return falhaAoCarregar();
  }
  if (resp.status === 401) return voltarParaEntrada();
  if (!resp.ok) return falhaAoCarregar();
  let dados;
  try {
    dados = await resp.json();
  } catch {
    return falhaAoCarregar();
  }
  itensTodos = dados?.itens || [];
  renderizarTudo();
}

const dialogo = $("dialogo-apagar");
$("hist-busca").addEventListener("input", renderizarTabela);
$("hist-filtro").addEventListener("change", renderizarTabela);
$("hist-apagar-tudo").addEventListener("click", () => {
  dialogo.returnValue = "";
  dialogo.showModal();
});
dialogo.addEventListener("close", () => {
  if (dialogo.returnValue === "apagar") apagarTudo();
});
window.addEventListener("spectra:tema", renderizarResumo);

carregar();
