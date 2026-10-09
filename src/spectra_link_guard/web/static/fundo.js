/* Spectra — efeitos de fundo em canvas.
 *
 * Inicializa todo <canvas class="fundo-animado" data-efeito="..."> da página:
 *   - "varredura": grade com um feixe de scanner que acende pontos ao passar;
 *   - "chuva-hex": colunas de caracteres hexadecimais caindo.
 * O canvas ocupa o elemento pai. As cores vêm dos tokens: feixe, pontos e
 * chuva releem a cada quadro; a grade fica pronta num canvas fora da tela e é
 * refeita no redimensionamento e no evento `spectra:tema`.
 *
 * Desempenho: resolução limitada a 1,5x; no máximo 30 quadros por segundo;
 * pausa com a aba em segundo plano e com o canvas fora da tela; no celular, a
 * chuva tem menos quadros e o feixe anda mais devagar. Só uma mudança de
 * largura sorteia pontos/colunas de novo: mudar só a altura mantém o efeito
 * onde estava.
 * Movimento parado: a varredura desenha só a grade, uma vez; a chuva some.
 */

(function () {
  const raiz = document.documentElement;
  const DPR = Math.min(window.devicePixelRatio || 1, 1.5);
  const HEX = "0123456789ABCDEF";
  const consultaCelular = window.matchMedia("(max-width: 599px)");

  const movimentoLigado = () => raiz.dataset.movimento !== "off";
  const celular = () => consultaCelular.matches;

  /** Uma leitura de estilo por chamada; devolve cor(token, alfa). */
  function paleta() {
    const estilo = getComputedStyle(raiz);
    return (token, alfa) => `rgb(${estilo.getPropertyValue(`--${token}-rgb`).trim()} / ${alfa})`;
  }

  const varredura = {
    iniciar: () => ({ y: -60, pontos: [], ultimo: 0, grade: document.createElement("canvas") }),
    redimensionar(estado, largura, altura, mudouLargura) {
      if (!mudouLargura) return;
      const quantidade = Math.max(6, Math.min(40, Math.round((largura * altura) / 26000)));
      estado.pontos = Array.from({ length: quantidade }, () => ({
        x: Math.random() * largura,
        y: Math.random() * altura,
        aceso: -Infinity,
        perigo: Math.random() < 0.3,
      }));
    },
    intervaloMs: () => 33,
    prepararCores(estado, largura, altura, cor) {
      const grade = estado.grade;
      grade.width = Math.round(largura * DPR);
      grade.height = Math.round(altura * DPR);
      const g = grade.getContext("2d");
      g.setTransform(DPR, 0, 0, DPR, 0, 0);
      g.strokeStyle = cor("linha-forte", 0.35);
      g.lineWidth = 1;
      g.beginPath();
      for (let x = 0.5; x < largura; x += 22) { g.moveTo(x, 0); g.lineTo(x, altura); }
      for (let y = 0.5; y < altura; y += 22) { g.moveTo(0, y); g.lineTo(largura, y); }
      g.stroke();
    },
    estatico(ctx, estado, largura, altura) {
      ctx.clearRect(0, 0, largura, altura);
      ctx.drawImage(estado.grade, 0, 0, largura, altura);
    },
    quadro(ctx, estado, largura, altura, agora, cor) {
      const passo = estado.ultimo ? Math.min(agora - estado.ultimo, 100) : 16;
      estado.ultimo = agora;
      estado.y += (celular() ? 0.036 : 0.06) * passo; // px por ms
      if (estado.y > altura + 60) estado.y = -60;

      this.estatico(ctx, estado, largura, altura);

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
    redimensionar(estado, largura, altura, mudouLargura) {
      if (!mudouLargura) return;
      estado.tamanho = celular() ? 16 : 14;
      // As colunas que já existem continuam caindo; só as novas começam acima do topo.
      const total = Math.ceil(largura / estado.tamanho);
      const colunas = estado.colunas.slice(0, total);
      while (colunas.length < total) colunas.push(Math.floor(Math.random() * -40));
      estado.colunas = colunas;
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
      const corRara = cor("texto", 0.5);
      const corComum = cor("primaria-clara", 0.35);
      estado.colunas.forEach((linha, i) => {
        const y = linha * estado.tamanho;
        if (y > 0) {
          ctx.fillStyle = Math.random() < 0.04 ? corRara : corComum;
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
        efeito.estatico(ctx, estado, largura, altura);
        return;
      }
      if (visivel && !document.hidden) pedido = requestAnimationFrame(laco);
    }

    function prepararCores() {
      if (largura && efeito.prepararCores) efeito.prepararCores(estado, largura, altura, paleta());
    }

    function medir() {
      const caixa = pai.getBoundingClientRect();
      const novaLargura = Math.max(1, Math.round(caixa.width));
      const novaAltura = Math.max(1, Math.round(caixa.height));
      if (novaLargura === largura && novaAltura === altura) return;
      const mudouLargura = novaLargura !== largura;
      largura = novaLargura;
      altura = novaAltura;
      canvas.width = Math.round(largura * DPR);
      canvas.height = Math.round(altura * DPR);
      canvas.style.width = `${largura}px`;
      canvas.style.height = `${altura}px`;
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
      efeito.redimensionar(estado, largura, altura, mudouLargura);
      prepararCores();
      atualizar();
    }

    new ResizeObserver(medir).observe(pai);
    new IntersectionObserver((entradas) => {
      visivel = entradas[entradas.length - 1].isIntersecting;
      atualizar();
    }).observe(canvas);
    document.addEventListener("visibilitychange", atualizar);
    window.addEventListener("spectra:movimento", atualizar);
    window.addEventListener("spectra:tema", () => {
      prepararCores();
      if (!movimentoLigado()) atualizar();
    });
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
