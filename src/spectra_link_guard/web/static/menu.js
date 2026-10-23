/* Navegação compartilhada: destino após login e gaveta do celular.
 * A conta e o botão de sair são controlados globalmente por conta.js.
 */

(function () {
  const proximo = sessionStorage.getItem("spectra-proximo");
  if (proximo) {
    sessionStorage.removeItem("spectra-proximo");
    if (/^\/painel(?:\/|\?|$)/.test(proximo) && !/[\\\r\n]/.test(proximo) && location.pathname + location.search !== proximo) {
      location.replace(proximo);
      return;
    }
  }
  const gaveta = document.getElementById("gaveta-mais");
  const abridores = document.querySelectorAll("[data-abrir-mais]");
  if (gaveta && typeof gaveta.showModal === "function") {
    let ultimoAbridor = null;

    abridores.forEach((botao) => botao.addEventListener("click", () => {
      ultimoAbridor = botao;
      gaveta.showModal();
      abridores.forEach((b) => b.setAttribute("aria-expanded", "true"));
    }));

    gaveta.addEventListener("close", () => {
      abridores.forEach((b) => b.setAttribute("aria-expanded", "false"));
      if (ultimoAbridor) ultimoAbridor.focus();
    });

    // Toque fora da gaveta (no fundo escurecido) fecha. Compara coordenadas
    // porque o clique no ::backdrop chega com o próprio <dialog> como alvo.
    // O alvo também precisa ser o <dialog>: clique vindo do teclado ou do
    // leitor de tela chega com clientX/Y = 0, que pareceria "fora".
    gaveta.addEventListener("click", (evento) => {
      const caixa = gaveta.getBoundingClientRect();
      const fora = evento.clientY < caixa.top || evento.clientY > caixa.bottom
        || evento.clientX < caixa.left || evento.clientX > caixa.right;
      if (evento.target === gaveta && fora) gaveta.close();
    });

    gaveta.querySelector("[data-fechar-gaveta]").addEventListener("click", () => gaveta.close());

    // Se a tela atual mora dentro da gaveta, a aba "Mais" aparece ativa.
    if (gaveta.querySelector('[aria-current="page"]')) {
      document.querySelector(".barra-abas [data-abrir-mais]")?.classList.add("ativo");
    }
  }
})();
