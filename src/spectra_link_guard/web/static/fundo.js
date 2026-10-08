/* Spectra — efeitos de fundo em canvas.
 *
 * Inicializa todo <canvas class="fundo-animado" data-efeito="..."> da página:
 *   - "varredura": grade com um feixe de scanner que acende pontos ao passar;
 *   - "chuva-hex": colunas de caracteres hexadecimais caindo.
 * O canvas ocupa o elemento pai. As cores vêm dos tokens a cada quadro, então
 * trocar o tema não exige reiniciar nada.
 *
 * Desempenho: resolução limitada a 1,5x; pausa com a aba em segundo plano e
 * com o canvas fora da tela; no celular, menos quadros e feixe mais lento.
 * Movimento parado: a varredura desenha só a grade, uma vez; a chuva some.
 */

(function () {
  const raiz = document.documentElement;
  const DPR = Math.min(window.devicePixelRatio || 1, 1.5);
  const HEX = "0123456789ABCDEF";

  const movimentoLigado = () => raiz.dataset.movimento !== "off";
  const celular = () => window.matchMedia("(max-width: 599px)").matches;

  /** Uma leitura de estilo por quadro; devolve cor(token, alfa). */
  function paleta() {
    const estilo = getComputedStyle(raiz);
    return (token, alfa) => `rgb(${estilo.getPropertyValue(`--${token}-rgb`).trim()} / ${alfa})`;
  }

  const varredura = {
    iniciar: () => ({ y: -60, pontos: [], ultimo: 0 }),
    redimensionar(estado, largura, altura) {
      const quantidade = Math.max(6, Math.min(40, Math.round((largura * altura) / 26000)));
      estado.pontos = Array.from({ length: quantidade }, () => ({
        x: Math.random() * largura,
        y: Math.random() * altura,
        aceso: -Infinity,
        perigo: Math.random() < 0.3,
      }));
    },
    intervaloMs: () => (celular() ? 33 : 16),
    grade(ctx, largura, altura, cor) {
      ctx.strokeStyle = cor("linha-forte", 0.35);
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = 0.5; x < largura; x += 22) { ctx.moveTo(x, 0); ctx.lineTo(x, altura); }
      for (let y = 0.5; y < altura; y += 22) { ctx.moveTo(0, y); ctx.lineTo(largura, y); }
      ctx.stroke();
    },
    estatico(ctx, estado, largura, altura, cor) {
      ctx.clearRect(0, 0, largura, altura);
      this.grade(ctx, largura, altura, cor);
    },
    quadro(ctx, estado, largura, altura, agora, cor) {
      const passo = estado.ultimo ? Math.min(agora - estado.ultimo, 100) : 16;
      estado.ultimo = agora;
      estado.y += (celular() ? 0.036 : 0.06) * passo; // px por ms
      if (estado.y > altura + 60) estado.y = -60;

      ctx.clearRect(0, 0, largura, altura);
      this.grade(ctx, largura, altura, cor);

      const rastro = ctx.createLinearGradient(0, estado.y - 56, 0, estado.y);
      rastro.addColorStop(0, cor("primaria", 0));
      rastro.addColorStop(1, cor("primaria", 0.22));
      ctx.fillStyle = rastro;
      ctx.fillRect(0, estado.y - 56, largura, 56);
      ctx.fillStyle = cor("primaria-clara", 0.8);
      ctx.fillRect(0, estado.y, largura, 1.5);

      for (const ponto of estado.pontos) {
        if (Math.abs(ponto.y - estado.y) < 3) ponto.aceso = agora;
        const forca = 1 - (agora - ponto.aceso) / 1500;
        if (forca <= 0) continue;
        ctx.fillStyle = cor(ponto.perigo ? "perigo" : "terciaria", forca * 0.85);
        ctx.beginPath();
        ctx.arc(ponto.x, ponto.y, 2.5 + 4 * (1 - forca), 0, Math.PI * 2);
        ctx.fill();
      }
    },
  };

  const chuvaHex = {
    iniciar: () => ({ colunas: [], tamanho: 14 }),
    redimensionar(estado, largura) {
      estado.tamanho = celular() ? 16 : 14;
      estado.colunas = Array.from(
        { length: Math.ceil(largura / estado.tamanho) },
        () => Math.floor(Math.random() * -40),
      );
    },
    intervaloMs: () => (celular() ? 90 : 70),
    estatico(ctx, estado, largura, altura) {
      ctx.clearRect(0, 0, largura, altura);
    },
    quadro(ctx, estado, largura, altura, agora, cor) {
      // Rastro: apaga um pouco do quadro anterior em vez de pintar o fundo
      // por cima, para o canvas continuar transparente em qualquer tema.
      ctx.globalCompositeOperation = "destination-out";
      ctx.fillStyle = "rgb(0 0 0 / .16)";
      ctx.fillRect(0, 0, largura, altura);
      ctx.globalCompositeOperation = "source-over";

      ctx.font = `${estado.tamanho}px "JetBrains Mono", ui-monospace, monospace`;
      estado.colunas.forEach((linha, i) => {
        const y = linha * estado.tamanho;
        if (y > 0) {
          ctx.fillStyle = Math.random() < 0.04 ? cor("texto", 0.5) : cor("primaria-clara", 0.35);
          ctx.fillText(HEX[(Math.random() * 16) | 0], i * estado.tamanho, y);
        }
        estado.colunas[i] = y > altura && Math.random() > 0.975 ? 0 : linha + 1;
      });
    },
  };

  const EFEITOS = { varredura, "chuva-hex": chuvaHex };

  function montar(canvas) {
    const efeito = EFEITOS[canvas.dataset.efeito];
    const pai = canvas.parentElement;
    if (!efeito || !pai) return;

    const ctx = canvas.getContext("2d");
    const estado = efeito.iniciar();
    let largura = 0;
    let altura = 0;
    let visivel = true;
    let pedido = 0;
    let ultimoQuadro = 0;

    function laco(agora) {
      pedido = requestAnimationFrame(laco);
      if (agora - ultimoQuadro < efeito.intervaloMs()) return;
      ultimoQuadro = agora;
      efeito.quadro(ctx, estado, largura, altura, agora, paleta());
    }

    function atualizar() {
      cancelAnimationFrame(pedido);
      pedido = 0;
      if (!largura) return;
      if (!movimentoLigado()) {
        efeito.estatico(ctx, estado, largura, altura, paleta());
        return;
      }
      if (visivel && !document.hidden) pedido = requestAnimationFrame(laco);
    }

    function medir() {
      const caixa = pai.getBoundingClientRect();
      largura = Math.max(1, Math.round(caixa.width));
      altura = Math.max(1, Math.round(caixa.height));
      canvas.width = Math.round(largura * DPR);
      canvas.height = Math.round(altura * DPR);
      canvas.style.width = `${largura}px`;
      canvas.style.height = `${altura}px`;
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
      efeito.redimensionar(estado, largura, altura);
      atualizar();
    }

    new ResizeObserver(medir).observe(pai);
    new IntersectionObserver(([entrada]) => {
      visivel = entrada.isIntersecting;
      atualizar();
    }).observe(canvas);
    document.addEventListener("visibilitychange", atualizar);
    window.addEventListener("spectra:movimento", atualizar);
    window.addEventListener("spectra:tema", () => { if (!movimentoLigado()) atualizar(); });
  }

  function iniciar() {
    document.querySelectorAll("canvas.fundo-animado[data-efeito]").forEach(montar);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
