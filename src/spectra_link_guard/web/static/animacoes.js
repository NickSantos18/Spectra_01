/* Spectra — micro-interações compartilhadas.
 *
 * Carregado no <head>, depois de movimento.js: marca <html> com
 * `revelar-pronto` antes da primeira pintura — sem isso os elementos
 * [data-revelar] apareceriam e sumiriam num piscar. Expõe:
 *   window.animarNumero(el, valor, { sufixo, duracaoMs })
 *   window.avisarToast(texto, tipo)   // "info" | "ok" | "erro"
 */

(function () {
  const raiz = document.documentElement;
  raiz.classList.add("revelar-pronto");

  const movimentoLigado = () => raiz.dataset.movimento !== "off";

  function revelarAoRolar() {
    const alvos = [...document.querySelectorAll("[data-revelar]")];
    if (!alvos.length) return;
    if (!movimentoLigado() || !("IntersectionObserver" in window)) {
      alvos.forEach((el) => el.classList.add("revelado"));
      return;
    }
    const observador = new IntersectionObserver(
      (entradas) => {
        entradas
          .filter((entrada) => entrada.isIntersecting)
          .forEach((entrada, i) => {
            setTimeout(() => entrada.target.classList.add("revelado"), i * 70);
            observador.unobserve(entrada.target);
          });
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" },
    );
    alvos.forEach((el) => observador.observe(el));
  }

  function formatar(valor, sufixo) {
    return `${Math.round(valor).toLocaleString("pt-BR")}${sufixo}`;
  }

  function animarNumero(el, valor, { sufixo = "", duracaoMs = 1100 } = {}) {
    if (!el) return;
    if (!movimentoLigado() || valor === 0) {
      el.textContent = formatar(valor, sufixo);
      return;
    }
    const inicio = performance.now();
    function quadro(agora) {
      const t = Math.min(1, (agora - inicio) / duracaoMs);
      el.textContent = formatar(valor * (1 - Math.pow(1 - t, 3)), sufixo);
      if (t < 1) requestAnimationFrame(quadro);
    }
    requestAnimationFrame(quadro);
  }

  // A região aria-live precisa existir antes do primeiro aviso, senão o
  // leitor de tela não anuncia a primeira mensagem.
  function caixaDeAvisos() {
    let caixa = document.querySelector(".toasts");
    if (!caixa) {
      caixa = document.createElement("div");
      caixa.className = "toasts";
      caixa.setAttribute("role", "status");
      caixa.setAttribute("aria-live", "polite");
      document.body.append(caixa);
    }
    return caixa;
  }

  function avisarToast(texto, tipo = "info") {
    const toast = document.createElement("p");
    toast.className = "toast";
    toast.dataset.tipo = tipo;
    toast.textContent = texto;
    caixaDeAvisos().append(toast);
    setTimeout(() => {
      toast.classList.add("saindo");
      setTimeout(() => toast.remove(), 220);
    }, 3500);
  }

  window.animarNumero = animarNumero;
  window.avisarToast = avisarToast;

  function iniciar() {
    caixaDeAvisos();
    revelarAoRolar();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
