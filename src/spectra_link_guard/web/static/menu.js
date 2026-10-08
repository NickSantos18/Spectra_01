/* Menu compartilhado do painel (web/parciais/menu.html): bloco da conta e
 * botões de sair. A conta pode aparecer em mais de um lugar (menu lateral,
 * barra do celular, gaveta), por isso os alvos são atributos data-*, não ids.
 * Todo texto vindo do servidor entra por textContent.
 */

(function () {
  function preencherConta(usuario) {
    const inicial = usuario.nome.trim().charAt(0).toUpperCase();
    document.querySelectorAll("[data-conta-inicial]").forEach((el) => { el.textContent = inicial; });
    document.querySelectorAll("[data-conta-nome]").forEach((el) => { el.textContent = usuario.nome; });
    document.querySelectorAll("[data-conta]").forEach((el) => { el.hidden = false; });
  }

  async function sair() {
    try {
      await fetch("/api/auth/sair", { method: "POST" });
    } finally {
      window.location.href = "/inicio";
    }
  }

  fetch("/api/auth/eu")
    .then((resposta) => resposta.json())
    .then(({ usuario }) => { if (usuario) preencherConta(usuario); })
    .catch(() => {});

  document.querySelectorAll("[data-sair]").forEach((botao) => botao.addEventListener("click", sair));

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
