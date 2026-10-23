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

  // Os novos fundos compartilham o mesmo controle de pausa, tema e resolução.
  const circuitos = {
    iniciar: () => ({ caminhos: [] }), intervaloMs: () => celular() ? 50 : 33,
    redimensionar(e,w,h) {
      const cx=w*.5, cy=Math.min(180,h*.28);
      e.caminhos=Array.from({length:celular()?12:24},(_,i)=>{
        const lado=i%2===0?-1:1, faixa=Math.floor(i/2);
        const inicio={x:cx+lado*(w*.55),y:50+faixa*(h-90)/(celular()?6:12)};
        const fim={x:cx+lado*65,y:cy+(faixa%5-2)*13};
        const curva={x:cx+lado*(110+(faixa%4)*38),y:inicio.y};
        return {pontos:[inicio,curva,{x:curva.x-lado*40,y:fim.y},fim],fase:i*.173};
      });
    },
    desenhar(ctx,e,w,h,tempo,cor) {
      ctx.clearRect(0,0,w,h);
      const t=tempo/1000;
      const brilho=ctx.createRadialGradient(w*.5,Math.min(180,h*.28),10,w*.5,h*.3,w*.6);
      brilho.addColorStop(0,cor('primaria',.23));brilho.addColorStop(1,cor('primaria',0));ctx.fillStyle=brilho;ctx.fillRect(0,0,w,h);
      // Ondas elípticas envolvem a marca, sem cobrir o título da entrada.
      for(let anel=0;anel<3;anel++) {
        const fase=(t*.055+anel/3)%1;
        ctx.strokeStyle=cor('primaria-clara',(1-fase)*.18);ctx.lineWidth=1;
        ctx.beginPath();ctx.ellipse(w*.5,Math.min(180,h*.28),90+fase*w*.3,35+fase*85,0,0,Math.PI*2);ctx.stroke();
      }
      for(const caminho of e.caminhos) {
        const ps=caminho.pontos;
        ctx.strokeStyle=cor('primaria-clara',.13);ctx.lineWidth=1;ctx.beginPath();ps.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.stroke();
        const segmentos=ps.slice(1).map((p,i)=>Math.hypot(p.x-ps[i].x,p.y-ps[i].y));
        const total=segmentos.reduce((a,b)=>a+b,0);
        const avancar=((t*.065+caminho.fase)%1)*total;
        // O rastro acompanha o caminho completo, incluindo os cantos.
        for(let r=1;r<=9;r++) {
          let restant=(avancar-r*5+total)%total;
          for(let i=0;i<segmentos.length;i++) {
            if(restant>segmentos[i]){restant-=segmentos[i];continue;}
            const f=segmentos[i]?restant/segmentos[i]:0;
            ctx.fillStyle=cor('primaria-clara',(1-r/10)*.38);
            ctx.beginPath();ctx.arc(ps[i].x+(ps[i+1].x-ps[i].x)*f,ps[i].y+(ps[i+1].y-ps[i].y)*f,1.4,0,Math.PI*2);ctx.fill();break;
          }
        }
        let distancia=avancar;
        for(let i=0;i<segmentos.length;i++) {
          if(distancia>segmentos[i]){distancia-=segmentos[i];continue;}
          const f=segmentos[i]?distancia/segmentos[i]:0,x=ps[i].x+(ps[i+1].x-ps[i].x)*f,y=ps[i].y+(ps[i+1].y-ps[i].y)*f;
          ctx.shadowBlur=12;ctx.shadowColor=cor('primaria-clara',.65);ctx.fillStyle=cor('primaria-clara',.65);ctx.beginPath();ctx.arc(x,y,2,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;break;
        }
        const p=ps[ps.length-1];ctx.strokeStyle=cor('primaria-clara',.3);ctx.beginPath();ctx.arc(p.x,p.y,3,0,Math.PI*2);ctx.stroke();
      }
    },
    estatico(ctx,e,w,h) { this.desenhar(ctx,e,w,h,0,paleta()); },
    quadro(ctx,e,w,h,t,cor) { this.desenhar(ctx,e,w,h,t,cor); },
  };

  /** Feixes paramétricos: a profundidade e a fase mudam por tela. */
  function ondasTecnologicas(tipo) {
    const conversas = tipo === 'conversas', forum = tipo === 'forum';
    const explorar = tipo === 'explorar', perfil = tipo === 'perfil';
    return {
      iniciar: () => ({}), redimensionar() {},
      intervaloMs: () => celular() ? 50 : 33,
      desenhar(ctx,e,w,h,tempo,cor) {
        ctx.clearRect(0,0,w,h);
        const t=tempo/1000, inicio=celular()?0:236;
        const area=Math.max(1,w-inicio), quantidade=perfil?(celular()?20:36):(celular()?16:26);
        // Luz ambiente nas bordas; evita um foco brilhante atrás dos textos.
        for(const lado of [0,1]) {
          const x=inicio+area*lado, y=h*(.4+Math.sin(t*.14+lado*2)*.13);
          const luz=ctx.createRadialGradient(x,y,0,x,y,area*.65);
          luz.addColorStop(0,cor('primaria',perfil?.32:.18));luz.addColorStop(1,cor('primaria',0));
          ctx.fillStyle=luz;ctx.fillRect(inicio,0,area,h);
        }
        const amostrar=(x,linha,camada)=>{
          const u=(x-inicio)/area, profundidade=linha/quantidade;
          const direcao=conversas&&camada===1?-1:1;
          const fase=t*(explorar?.32:.24)*direcao;
          const amplitude=(celular()?46:90)*(1+profundidade*.45)*(perfil?1.3:1);
          const base=camada===0?h*(perfil?.2:.32):h*(perfil?.88:.78);
          // Fitas que se torcem: o espaçamento varia com a onda principal.
          return base+Math.sin(u*5.5+fase+camada*2)*amplitude
            +Math.sin(u*9-fase*.7+profundidade*.8)*amplitude*.3
            +(profundidade-.5)*(50+Math.pow(Math.sin(u*3+fase*.4),2)*95);
        };
        for(let camada=0;camada<2;camada++) {
          for(let linha=0;linha<quantidade;linha++) {
            const destaque=linha%7===0, profundidade=linha/quantidade;
            const gradiente=ctx.createLinearGradient(inicio,0,w,0);
            const intensidade=(destaque?.48:.11+profundidade*.09)*(perfil?1.45:1);
            gradiente.addColorStop(0,cor('primaria-clara',intensidade));
            gradiente.addColorStop(.48,cor('primaria-clara',intensidade*.18));
            gradiente.addColorStop(1,cor('primaria-clara',intensidade*.85));
            ctx.strokeStyle=gradiente;ctx.lineWidth=destaque?1.4:.65;
            ctx.beginPath();
            for(let x=inicio-12;x<=w+12;x+=celular()?12:9){const y=amostrar(x,linha,camada);if(x===inicio-12)ctx.moveTo(x,y);else ctx.lineTo(x,y);}
            ctx.stroke();
            if(!destaque)continue;
            // Um sinal percorre cada linha principal com um rastro curto.
            const phase=(t*(conversas?.075:perfil?.065:.045)+linha*.071+camada*.37)%1;
            const position=conversas&&camada===1?1-phase:phase;
            const px=inicio+area*position;
            for(let r=5;r>=0;r--) {
              const x=px-r*(conversas&&camada===1?-5:5),y=amostrar(x,linha,camada);
              ctx.fillStyle=cor('primaria-clara',(1-r/6)*.75);
              ctx.beginPath();ctx.arc(x,y,r===0?2.3:1.3,0,Math.PI*2);ctx.fill();
            }
          }
        }
        if(perfil) {
          // Pulsos amplos nas bordas: o centro continua escuro para os formulários.
          for(const lado of [0,1]) {
            const cx=inicio+area*lado,cy=h*(lado?.72:.25);
            for(let i=0;i<4;i++) {
              const fase=(t*.065+i*.25+lado*.12)%1;
              const raio=30+fase*Math.max(area*.55,h*.35);
              ctx.strokeStyle=cor('primaria-clara',Math.sin(Math.PI*fase)*.3);
              ctx.lineWidth=i===0?1.5:.8;ctx.beginPath();
              ctx.ellipse(cx,cy,raio,raio*.6,lado?.35:-.35,0,Math.PI*2);ctx.stroke();
            }
            // Feixes verticais curvos em profundidade, com rastros junto às laterais.
            for(let linha=0;linha<(celular()?5:9);linha++) {
              ctx.beginPath();
              for(let y=-12;y<=h+12;y+=12) {
                const direcao=lado?-1:1;
                const x=cx+direcao*(18+linha*9+Math.sin(y/h*5-t*.3+linha*.13)*area*.07);
                if(y===-12)ctx.moveTo(x,y);else ctx.lineTo(x,y);
              }
              ctx.lineWidth=linha%3===0?1.3:.6;
              ctx.strokeStyle=cor('primaria-clara',linha%3===0?.4:.15);ctx.stroke();
            }
          }
        }
        // Fórum: ondas de transmissão. Explorar: arcos orbitais em profundidade.
        if(forum||explorar) {
          const centros=forum?[[.12,.27],[.88,.72]]:[[.83,.38]];
          for(const [u,v] of centros) {
            const x=inicio+area*u,y=h*v;
            for(let i=0;i<4;i++) {
              const progresso=(t*.07+i*.25)%1;
              ctx.strokeStyle=cor('primaria-clara',(1-progresso)*.2);
              ctx.lineWidth=1;ctx.beginPath();
              ctx.ellipse(x,y,25+progresso*area*.4,(25+progresso*area*.4)*(explorar?.45:1),explorar?-.45:0,0,Math.PI*2);ctx.stroke();
            }
          }
        }
      },
      estatico(ctx,e,w,h){this.desenhar(ctx,e,w,h,0,paleta());},
      quadro(ctx,e,w,h,t,cor){this.desenhar(ctx,e,w,h,t,cor);},
    };
  }

  const EFEITOS = { varredura, "chuva-hex": chuvaHex, "energia-perfil":ondasTecnologicas('perfil'), conversas:ondasTecnologicas('conversas'), forum:ondasTecnologicas('forum'), explorar:ondasTecnologicas('explorar'), ondas:ondasTecnologicas('blog'), circuitos };

  function montar(canvas) {
    const efeito = EFEITOS[canvas.dataset.efeito];
    const pai = canvas.parentElement;
    if (!efeito || !pai) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const estado = efeito.iniciar();
    let largura = 0;
    let altura = 0;
    let visivel = true;
    let pedido = 0;
    let ultimoQuadro = 0;
    let tempoAtivo = 0;
    let anterior = null;

    function laco(agora) {
      pedido = requestAnimationFrame(laco);
      if (agora - ultimoQuadro < efeito.intervaloMs()) return;
      ultimoQuadro = agora;
      if (anterior !== null) tempoAtivo += agora - anterior;
      anterior = agora;
      efeito.quadro(ctx, estado, largura, altura, tempoAtivo, paleta());
    }

    function atualizar() {
      cancelAnimationFrame(pedido);
      pedido = 0;
      anterior = null;
      if (!largura) return;
      if (raiz.dataset.perfilTransicao || raiz.classList.contains('perfil-avatar-entrada')) return;
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
      // A captura de entrada precisa conter o fundo pronto mesmo com o RAF
      // suspenso. Evita revelar uma tela vazia e ligar as ondas só ao terminar.
      if (raiz.dataset.perfilTransicao || raiz.classList.contains('perfil-avatar-entrada')) {
        efeito.quadro(ctx, estado, largura, altura, tempoAtivo, paleta());
      }
      atualizar();
    }

    new ResizeObserver(medir).observe(pai);
    new IntersectionObserver((entradas) => {
      visivel = entradas[entradas.length - 1].isIntersecting;
      atualizar();
    }).observe(canvas);
    document.addEventListener("visibilitychange", atualizar);
    window.addEventListener("spectra:movimento", atualizar);
    window.addEventListener("spectra:perfil-transicao", atualizar);
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
