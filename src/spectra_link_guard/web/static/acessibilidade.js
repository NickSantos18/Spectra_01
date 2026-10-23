/* Acessibilidade — tema claro/escuro, tamanho de fonte e alto contraste.
 *
 * Mesmo padrão de movimento.js: roda cedo, sem `defer`, para aplicar os
 * atributos em <html> antes da primeira pintura (evita flash de tema
 * errado). A escolha de cada pessoa fica em localStorage e vale para todas
 * as páginas do site.
 *
 * O controle de "reduzir movimento" não mora aqui: já existe em
 * movimento.js (`data-movimento`, tecla localStorage "spectra:movimento") e
 * esta barra só reaproveita aquele botão/estado, para não duplicar lógica.
 */

(function () {
  const CHAVE_TEMA = "spectra:tema";
  const CHAVE_FONTE = "spectra:fonte";
  const CHAVE_CONTRASTE = "spectra:contraste";
  const raiz = document.documentElement;

  const NIVEIS_FONTE = [87.5, 93.75, 100, 112.5, 125, 137.5, 150];
  const NIVEL_PADRAO = 2; // índice de 100%

  function lerNumero(chave, padrao) {
    try {
      const bruto = localStorage.getItem(chave);
      // Number(null) e Number("") dão 0, que é um nível válido (87,5%).
      if (bruto === null || bruto.trim() === "") return padrao;
      const v = Number(bruto);
      return Number.isInteger(v) && v >= 0 && v < NIVEIS_FONTE.length ? v : padrao;
    } catch {
      return padrao;
    }
  }

  function lerEscolha(chave) {
    try {
      return localStorage.getItem(chave);
    } catch {
      return null;
    }
  }

  function gravar(chave, valor) {
    try {
      localStorage.setItem(chave, valor);
    } catch {
      /* navegação privada ou armazenamento bloqueado: vale só nesta visita */
    }
  }

  function temaPreferidoDoSistema() {
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "claro" : "escuro";
  }

  function aplicarTema(tema) {
    raiz.dataset.tema = tema;
    // O ícone da aba acompanha a escolha do site, inclusive quando difere do sistema.
    document.querySelectorAll('link[rel="icon"]').forEach(icone => {
      icone.href = '/static/logo-spectra-' + (tema === 'claro' ? 'claro' : 'escuro') + '.svg';
    });
  }

  function aplicarFonte(nivel) {
    raiz.style.fontSize = NIVEIS_FONTE[nivel] + "%";
    raiz.dataset.nivelFonte = String(nivel);
  }

  function aplicarContraste(estado) {
    raiz.dataset.altoContraste = estado;
  }

  let tema = lerEscolha(CHAVE_TEMA) || temaPreferidoDoSistema();
  let nivelFonte = lerNumero(CHAVE_FONTE, NIVEL_PADRAO);
  let contraste = lerEscolha(CHAVE_CONTRASTE) || "off";

  aplicarTema(tema);
  aplicarFonte(nivelFonte);
  aplicarContraste(contraste);

  /* Arrastar o botão de acessibilidade para qualquer canto da tela — ele
   * pode ficar em cima de conteúdo dependendo da página/tamanho de tela, e
   * isto deixa a pessoa tirá-lo do caminho. A posição escolhida fica salva
   * e vale para as próximas páginas.
   *
   * `caixa` é o bloco fixo que se move (botão + painel juntos); `alca` é o
   * elemento que inicia o arrasto — só o botão, para não atrapalhar cliques
   * dentro do painel de opções.
   */
  function tornarArrastavel(caixa, alca) {
    const CHAVE_POS = "spectra:a11y-pos";
    const LIMIAR_PX = 6; // abaixo disso ainda conta como clique, não arrasto

    let arrastando = false;
    let moveu = false;
    let suprimirProximoClique = false;
    let inicioX = 0;
    let inicioY = 0;
    let offsetX = 0;
    let offsetY = 0;

    function limites(x, y) {
      const r = caixa.getBoundingClientRect();
      const maxX = Math.max(window.innerWidth - r.width, 0);
      const maxY = Math.max(window.innerHeight - r.height, 0);
      return [Math.min(Math.max(x, 0), maxX), Math.min(Math.max(y, 0), maxY)];
    }

    function posicionar(x, y) {
      const [cx, cy] = limites(x, y);
      caixa.style.left = `${cx}px`;
      caixa.style.top = `${cy}px`;
      caixa.style.right = "auto";
      caixa.style.bottom = "auto";
    }

    function restaurar() {
      try {
        const salvo = JSON.parse(localStorage.getItem(CHAVE_POS) || "null");
        if (salvo && Number.isFinite(salvo.x) && Number.isFinite(salvo.y)) posicionar(salvo.x, salvo.y);
      } catch {
        /* posição salva inválida: mantém a posição padrão do CSS */
      }
    }

    alca.addEventListener("pointerdown", (evento) => {
      if (evento.pointerType === "mouse" && evento.button !== 0) return;
      arrastando = true;
      moveu = false;
      const r = caixa.getBoundingClientRect();
      inicioX = evento.clientX;
      inicioY = evento.clientY;
      offsetX = evento.clientX - r.left;
      offsetY = evento.clientY - r.top;
    });

    alca.addEventListener("pointermove", (evento) => {
      if (!arrastando) return;
      if (!moveu) {
        const distancia = Math.hypot(evento.clientX - inicioX, evento.clientY - inicioY);
        if (distancia < LIMIAR_PX) return;
        moveu = true;
        alca.setPointerCapture(evento.pointerId);
        alca.classList.add("arrastando");
      }
      posicionar(evento.clientX - offsetX, evento.clientY - offsetY);
    });

    function soltar() {
      if (!arrastando) return;
      arrastando = false;
      alca.classList.remove("arrastando");
      if (moveu) {
        // O gesto de arrasto termina em pointerup, mas o navegador ainda
        // dispara um "click" sintético logo em seguida no mesmo elemento —
        // é esse clique fantasma que precisa ser ignorado, não os próximos.
        // Reseta `moveu` já aqui (não no handler de click): se por algum
        // motivo o clique fantasma não vier (ex.: a pessoa solta e na
        // sequência ativa o botão pelo teclado), o próximo clique real não
        // pode ficar bloqueado para sempre.
        suprimirProximoClique = true;
        setTimeout(() => { suprimirProximoClique = false; }, 400);
        try {
          const r = caixa.getBoundingClientRect();
          gravar(CHAVE_POS, JSON.stringify({ x: r.left, y: r.top }));
        } catch {
          /* sem armazenamento: a posição vale só para esta visita */
        }
      }
      moveu = false;
    }
    alca.addEventListener("pointerup", soltar);
    alca.addEventListener("pointercancel", soltar);

    // Registrado antes do clique que abre o painel (abaixo, em montarPainel):
    // como os dois estão no mesmo elemento, quem foi registrado primeiro
    // roda primeiro, então isto consegue barrar o "abrir" se houve arrasto.
    alca.addEventListener("click", (evento) => {
      if (suprimirProximoClique) {
        suprimirProximoClique = false;
        evento.preventDefault();
        evento.stopImmediatePropagation();
      }
    });

    // A janela pode encolher (girar o celular, redimensionar) depois de a
    // pessoa já ter arrastado o botão para um canto — reencaixa na tela.
    window.addEventListener("resize", () => {
      const r = caixa.getBoundingClientRect();
      if (caixa.style.left || caixa.style.top) posicionar(r.left, r.top);
    });

    restaurar();
  }

  function atualizarRotulos() {
    document.querySelectorAll("[data-a11y-tema-rotulo]").forEach((el) => {
      el.textContent = tema === "claro" ? "Tema claro" : "Tema escuro";
    });
    document.querySelectorAll("[data-a11y-contraste]").forEach((el) => {
      el.setAttribute("aria-pressed", String(contraste === "on"));
    });
    document.querySelectorAll("[data-a11y-fonte-valor]").forEach((el) => {
      el.textContent = `${NIVEIS_FONTE[nivelFonte]}%`;
    });
  }

  function montarPainel() {
    const host = document.getElementById("a11y-painel");
    if (!host) return;

    host.querySelector("[data-a11y-tema]")?.addEventListener("click", () => {
      tema = tema === "claro" ? "escuro" : "claro";
      gravar(CHAVE_TEMA, tema);
      aplicarTema(tema);
      window.dispatchEvent(new CustomEvent("spectra:tema", { detail: tema }));
      atualizarRotulos();
    });

    host.querySelector("[data-a11y-fonte-mais]")?.addEventListener("click", () => {
      nivelFonte = Math.min(NIVEIS_FONTE.length - 1, nivelFonte + 1);
      gravar(CHAVE_FONTE, String(nivelFonte));
      aplicarFonte(nivelFonte);
      atualizarRotulos();
    });

    host.querySelector("[data-a11y-fonte-menos]")?.addEventListener("click", () => {
      nivelFonte = Math.max(0, nivelFonte - 1);
      gravar(CHAVE_FONTE, String(nivelFonte));
      aplicarFonte(nivelFonte);
      atualizarRotulos();
    });

    host.querySelector("[data-a11y-fonte-reset]")?.addEventListener("click", () => {
      nivelFonte = NIVEL_PADRAO;
      gravar(CHAVE_FONTE, String(nivelFonte));
      aplicarFonte(nivelFonte);
      atualizarRotulos();
    });

    host.querySelector("[data-a11y-contraste]")?.addEventListener("click", () => {
      contraste = contraste === "on" ? "off" : "on";
      gravar(CHAVE_CONTRASTE, contraste);
      aplicarContraste(contraste);
      // O contraste também troca tokens: gráficos e canvas precisam relê-los.
      window.dispatchEvent(new CustomEvent("spectra:tema", { detail: tema }));
      atualizarRotulos();
    });

    atualizarRotulos();

    const botao = document.getElementById("a11y-abrir");
    const painel = document.getElementById("a11y-painel");
    if (!botao || !painel) return;

    const caixa = document.querySelector(".a11y-caixa");
    if (caixa) tornarArrastavel(caixa, botao);

    function abrir(mostrar) {
      painel.hidden = !mostrar;
      botao.setAttribute("aria-expanded", String(mostrar));
      if (mostrar) painel.querySelector("button,a")?.focus();
      else botao.focus();
    }
    botao.addEventListener("click", () => abrir(painel.hidden));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !painel.hidden) abrir(false);
    });
    document.addEventListener("click", (e) => {
      if (!painel.hidden && !painel.contains(e.target) && e.target !== botao && !botao.contains(e.target)) {
        abrir(false);
      }
    });
  }

  function preencherAno() {
    document.querySelectorAll("[data-ano-atual]").forEach((el) => {
      el.textContent = String(new Date().getFullYear());
    });
  }

  function iniciarIcones() {
    // Um único ponto de disparo para o lucide.createIcons(), já que este
    // script roda em toda página que tem rodapé — evita repetir a chamada
    // em cada arquivo *.js de página.
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  }

  function iniciar() {
    aplicarTema(tema);
    montarPainel();
    preencherAno();
    iniciarIcones();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
