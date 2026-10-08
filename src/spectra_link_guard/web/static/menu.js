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
})();
