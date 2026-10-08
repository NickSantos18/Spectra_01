/* Interruptor de movimento — carregado antes de tudo, sem `defer`.
 *
 * Por que existe: o padrão do site é respeitar `prefers-reduced-motion`, que é
 * o certo. Só que quem tem "efeitos de animação" desligado no Windows nunca vê
 * o site se mexer e não tem como saber por quê. Este módulo resolve a
 * preferência do sistema num atributo explícito em <html> e deixa a pessoa
 * trocar — a escolha dela vence a do sistema e fica guardada no navegador.
 *
 * Roda cedo de propósito: define o atributo antes da primeira pintura, senão
 * a página começa animando e trava um quadro depois.
 */

(function () {
  const CHAVE = "spectra:movimento";
  const raiz = document.documentElement;

  const sistemaPrefereParado = () =>
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function lerEscolha() {
    try {
      return localStorage.getItem(CHAVE); // "on" | "off" | null
    } catch {
      return null; // navegação privada ou armazenamento bloqueado
    }
  }

  function aplicar(estado) {
    raiz.dataset.movimento = estado;
    for (const botao of document.querySelectorAll("[data-interruptor-movimento]")) {
      botao.setAttribute("aria-pressed", String(estado === "on"));
      const rotulo = botao.querySelector("[data-rotulo-movimento]");
      if (rotulo) rotulo.textContent = estado === "on" ? "Movimento ligado" : "Movimento parado";
    }
  }

  function resolver() {
    const escolha = lerEscolha();
    if (escolha === "on" || escolha === "off") return escolha;
    return sistemaPrefereParado() ? "off" : "on";
  }

  aplicar(resolver());

  // A UI só existe depois do DOM; o atributo já foi definido acima.
  document.addEventListener("DOMContentLoaded", () => {
    aplicar(raiz.dataset.movimento);

    for (const botao of document.querySelectorAll("[data-interruptor-movimento]")) {
      botao.addEventListener("click", () => {
        const novo = raiz.dataset.movimento === "on" ? "off" : "on";
        try {
          localStorage.setItem(CHAVE, novo);
        } catch {
          /* sem armazenamento: vale só para esta página */
        }
        aplicar(novo);
        // Os efeitos em WebGL leem o estado na inicialização; recarregar é o
        // jeito honesto de aplicar sem manter dois caminhos de código.
        window.dispatchEvent(new CustomEvent("spectra:movimento", { detail: novo }));
      });
    }
  });

  // Consultado por cubos.js e por qualquer efeito em JS.
  window.spectraMovimentoLigado = () => raiz.dataset.movimento === "on";
})();
