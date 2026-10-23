/* Spectra — gráficos compartilhados, em SVG e HTML (sem biblioteca).
 *
 *   window.spectraGraficos.radial(alvo, itens, { rotulo, legenda })
 *     Barras radiais: um anel por item, de fora para dentro, cada um com o
 *     arco proporcional à fatia do total. A legenda ao lado traz nome, número
 *     e porcentagem — a cor identifica, mas nunca é o único canal.
 *     itens: [{ chave, nome, valor, cor }]
 *
 *   window.spectraGraficos.barras(alvo, itens, { total })
 *     Lista de barras horizontais finas, nome em cima e valor na ponta.
 *     itens: [{ nome, valor }]
 *
 *   window.spectraGraficos.corNivel(nivel)  // cor do token --nivel-<nivel>
 *
 * Passar o mouse num anel (ou na linha da legenda) destaca o par e apaga os
 * outros. Todo texto entra por textContent.
 */

(function () {
  const SVG = "http://www.w3.org/2000/svg";

  function semMovimento() {
    return window.spectraMovimentoLigado && !window.spectraMovimentoLigado();
  }

  function corNivel(nivel) {
    return getComputedStyle(document.documentElement).getPropertyValue(`--nivel-${nivel}`).trim();
  }

  function el(tag, classe, texto) {
    const no = document.createElement(tag);
    if (classe) no.className = classe;
    if (texto !== undefined && texto !== null) no.textContent = String(texto);
    return no;
  }

  function svg(tag, atributos) {
    const no = document.createElementNS(SVG, tag);
    for (const [nome, valor] of Object.entries(atributos)) no.setAttribute(nome, valor);
    return no;
  }

  function porcentagem(valor, total) {
    if (!total) return "0%";
    const p = (100 * valor) / total;
    return p > 0 && p < 1 ? "<1%" : `${Math.round(p)}%`;
  }

  /** Liga anel e linha da legenda: o foco de um destaca os dois. */
  function ligarDestaque(caixa, alvos) {
    for (const alvo of alvos) {
      const chave = alvo.dataset.chave;
      alvo.addEventListener("pointerenter", () => { caixa.dataset.foco = chave; });
      alvo.addEventListener("pointerleave", () => { delete caixa.dataset.foco; });
      alvo.addEventListener("focus", () => { caixa.dataset.foco = chave; });
      alvo.addEventListener("blur", () => { delete caixa.dataset.foco; });
    }
  }

  function radial(alvo, itens, { rotulo = "total", legenda = true } = {}) {
    const total = itens.reduce((soma, item) => soma + item.valor, 0);
    const animar = !semMovimento();

    // Geometria em unidades do viewBox (200 x 200). Anéis de 9 com 5 de folga.
    const externo = 94, espessura = 9, passo = 14;

    const caixa = el("div", "radial");
    const desenho = svg("svg", { viewBox: "0 0 200 200", class: "radial-svg", "aria-hidden": "true" });
    const arcos = [];

    itens.forEach((item, i) => {
      const r = externo - espessura / 2 - i * passo;
      const comum = { cx: 100, cy: 100, r, "stroke-width": espessura, fill: "none" };
      desenho.append(svg("circle", { ...comum, class: "radial-trilho" }));
      if (!item.valor) return;

      const fatia = (100 * item.valor) / total;
      const arco = svg("circle", {
        ...comum,
        class: "radial-arco",
        stroke: item.cor,
        pathLength: 100,
        "stroke-linecap": "round",
        "stroke-dasharray": animar ? "0 100" : `${fatia} 100`,
        transform: "rotate(-90 100 100)",
        "data-chave": item.chave,
      });
      arco.dataset.fatia = fatia;
      arco.style.color = item.cor;
      arcos.push(arco);
      desenho.append(arco);
    });

    const centro = svg("text", { x: 100, y: 100, class: "radial-total", "text-anchor": "middle" });
    centro.textContent = total.toLocaleString("pt-BR");
    const sub = svg("text", { x: 100, y: 116, class: "radial-sub", "text-anchor": "middle" });
    sub.textContent = rotulo;
    desenho.append(centro, sub);

    const figura = el("div", "radial-figura");
    figura.append(desenho);
    caixa.append(figura);

    const linhas = [];
    if (legenda) {
      const lista = el("ul", "radial-legenda");
      for (const item of itens) {
        const li = el("li", "radial-linha");
        li.tabIndex = 0;
        li.dataset.chave = item.chave;
        const ponto = el("span", "radial-ponto");
        ponto.style.background = item.cor;
        li.append(
          ponto,
          el("span", "radial-nome", item.nome),
          el("span", "radial-valor", item.valor.toLocaleString("pt-BR")),
          el("span", "radial-pct", porcentagem(item.valor, total)),
        );
        linhas.push(li);
        lista.append(li);
      }
      caixa.append(lista);
    }

    alvo.replaceChildren(caixa);
    alvo.setAttribute('aria-label', `${rotulo}: ${total}. ` + itens.map(i=>`${i.nome}: ${i.valor}, ${porcentagem(i.valor,total)}`).join('; '));
    ligarDestaque(caixa, [...arcos, ...linhas]);

    if (animar) {
      // Dois quadros: o primeiro pinta o arco vazio, o segundo dispara a transição.
      requestAnimationFrame(() => requestAnimationFrame(() => {
        for (const arco of arcos) arco.setAttribute("stroke-dasharray", `${arco.dataset.fatia} 100`);
      }));
    }
  }

  function barras(alvo, itens, { total = 0 } = {}) {
    const maior = Math.max(1, ...itens.map((item) => item.valor));
    const animar = !semMovimento();

    const linhas = itens.map((item) => {
      const li = el("li", "barra-item");
      const topo = el("div", "barra-topo");
      const valor = el("span", "barra-valor", item.valor.toLocaleString("pt-BR"));
      if (total) valor.append(el("span", "barra-pct", ` · ${porcentagem(item.valor, total)}`));
      topo.append(el("span", "barra-nome", item.nome), valor);

      const trilho = el("div", "barra-trilho");
      const cheio = el("span", "barra-cheia");
      const base = total || maior;
      cheio.style.width = animar ? "0%" : `${Math.min(100,(100 * item.valor) / base)}%`;
      cheio.dataset.largura = `${Math.min(100,(100 * item.valor) / base)}%`;
      trilho.append(cheio);

      li.append(topo, trilho);
      return li;
    });
    alvo.replaceChildren(...linhas);

    if (animar) {
      requestAnimationFrame(() => requestAnimationFrame(() => {
        alvo.querySelectorAll(".barra-cheia").forEach((cheio) => { cheio.style.width = cheio.dataset.largura; });
      }));
    }
  }

  window.spectraGraficos = { radial, barras, corNivel };
})();
