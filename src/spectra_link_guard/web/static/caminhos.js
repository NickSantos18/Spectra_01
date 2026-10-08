/* Caminhos flutuantes — usado pela entrada (/inicio) e pelo painel (/painel).
 *
 * Porte do componente BackgroundPaths (React + framer-motion) para SVG + CSS.
 * A curva é a mesma do original. O que muda é o motor: em vez de animar
 * `pathLength`/`pathOffset` via JavaScript a cada quadro, cada caminho recebe
 * `pathLength="1"` e a animação roda em CSS (`stroke-dashoffset`) — o navegador
 * cuida dela na composição, sem custo de JS por quadro.
 *
 * Arquivo compartilhado de propósito: sem bundler, duplicar esta função nos
 * dois scripts significaria corrigir bug em dois lugares.
 */

const SVG_NS_CAMINHOS = "http://www.w3.org/2000/svg";

/** Curva do componente original, parametrizada pelo índice e pelo sentido. */
function traçadoDoCaminho(i, posicao) {
  const dx = i * 5 * posicao;
  const dy = i * 6;
  return (
    `M-${380 - dx} -${189 + dy}` +
    `C-${380 - dx} -${189 + dy} -${312 - dx} ${216 - dy} ${152 - dx} ${343 - dy}` +
    `C${616 - dx} ${470 - dy} ${684 - dx} ${875 - dy} ${684 - dx} ${875 - dy}`
  );
}

/**
 * Preenche um <svg> com os caminhos.
 *
 * @param {SVGElement|null} svg  alvo; ignorado em silêncio se não existir
 * @param {number} posicao       1 ou -1 — o sentido em que a curva se abre
 * @param {{quantidade?: number, opacidade?: number}} opcoes
 *        `opacidade` é o teto: no painel ele é baixo de propósito, para os
 *        caminhos ficarem como ambiente e não disputarem com os dados.
 */
function desenharCaminhosFlutuantes(svg, posicao, opcoes = {}) {
  if (!svg) return;

  const quantidade = opcoes.quantidade ?? 36;
  const teto = opcoes.opacidade ?? 0.42;
  const fragmento = document.createDocumentFragment();

  for (let i = 0; i < quantidade; i += 1) {
    const caminho = document.createElementNS(SVG_NS_CAMINHOS, "path");
    const opacidade = Math.min(0.06 + i * 0.012, teto);

    caminho.setAttribute("d", traçadoDoCaminho(i, posicao));
    caminho.setAttribute("stroke", "currentColor");
    caminho.setAttribute("stroke-width", (0.5 + i * 0.03).toFixed(2));
    caminho.setAttribute("fill", "none");
    caminho.setAttribute("pathLength", "1");
    caminho.classList.add("caminho");

    // Duração e fase próprias: sem isso os caminhos pulsam todos em bloco.
    caminho.style.setProperty("--dur", `${20 + (i % 11) * 1.4}s`);
    caminho.style.setProperty("--op-min", opacidade.toFixed(3));
    caminho.style.setProperty("--op-max", Math.min(opacidade * 2.4, teto * 1.7).toFixed(3));
    caminho.style.animationDelay = `-${i * 0.55}s, -${i * 0.31}s`;

    fragmento.append(caminho);
  }
  svg.append(fragmento);
}

/**
 * Quebra um texto em letras animáveis dentro de `alvo`.
 *
 * O texto real fica no `aria-label` do elemento e os spans vão `aria-hidden`:
 * sem isso o leitor de tela soletra a frase letra por letra.
 */
function animarPorLetra(alvo, texto, { atrasoInicial = 0.1, passo = 0.028 } = {}) {
  if (!alvo) return;

  alvo.setAttribute("aria-label", texto);
  alvo.replaceChildren();

  let indice = 0;
  for (const palavra of texto.split(" ")) {
    const bloco = document.createElement("span");
    bloco.className = "bloco-palavra";
    bloco.setAttribute("aria-hidden", "true");

    for (const letra of palavra) {
      const vao = document.createElement("span");
      vao.className = "letra";
      vao.style.setProperty("--atraso", `${atrasoInicial + indice * passo}s`);
      vao.textContent = letra;
      bloco.append(vao);
      indice += 1;
    }
    alvo.append(bloco, document.createTextNode(" "));
  }
}
