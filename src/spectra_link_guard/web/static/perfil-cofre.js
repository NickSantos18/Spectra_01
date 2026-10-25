/* Entrada interativa no perfil: 1 s de transformação + 2 s após encaixar a chave.
 * O tempo para arrastar é livre. O cadeado é uma transição visual, não autenticação.
 */
(() => {
  const raiz = document.documentElement;
  const armazenamento = 'spectra:perfil-cofre';
  const tempos = { abertura: 1000, encaixe: 300, giro: 300, fragmentos: 650, navegacao: 750 };
  const movimento = () => window.spectraMovimentoLigado?.() ?? raiz.dataset.movimento !== 'off';
  let chegada = null;
  try {
    chegada = JSON.parse(sessionStorage.getItem(armazenamento) || 'null');
    sessionStorage.removeItem(armazenamento);
  } catch { /* A navegação também funciona sem armazenamento. */ }
  if (location.pathname !== '/painel/perfil' || location.search || chegada?.versao !== 1 ||
      !Number.isFinite(chegada.instante) || Date.now() - chegada.instante > 15000 || !movimento()) chegada = null;
  if (chegada) raiz.classList.add('perfil-cofre-chegando');
  let dialogo, chave, cadeado, mensagem, acesso, destino, arrasto = null;
  let fase = 'fechado', escolhida = false, operacao = 0, revelando = false;
  const animacoes = new Set();
  let voo = null, conteudoInerte = null;

  function medirArea() {
    const visivel = seletor => {
      const no = document.querySelector(seletor);
      return no && getComputedStyle(no).display !== 'none' ? no.getBoundingClientRect() : null;
    };
    const trilho = visivel('.trilho'), topo = visivel('.topo-movel'), abas = visivel('.barra-abas');
    raiz.style.setProperty('--cofre-esquerda', Math.max(0, trilho?.right || 0) + 'px');
    raiz.style.setProperty('--cofre-topo', Math.max(0, topo?.bottom || 0) + 'px');
    raiz.style.setProperty('--cofre-inferior', Math.max(0, abas ? innerHeight - abas.top : 0) + 'px');
  }

  function estado(valor) {
    fase = valor;
    if (dialogo) dialogo.dataset.fase = valor;
    if (valor === 'fechado') delete raiz.dataset.perfilTransicao;
    else raiz.dataset.perfilTransicao = valor;
    window.dispatchEvent(new Event('spectra:perfil-transicao'));
  }
  async function animar(elemento, quadros, duracao) {
    const animacao = elemento.animate(quadros, { duration: duracao, easing: 'cubic-bezier(.22,.7,.25,1)', fill: 'forwards' });
    animacoes.add(animacao);
    try { await animacao.finished; } finally { animacoes.delete(animacao); }
  }
  function limpar() {
    operacao++;
    chegada = null;
    for (const a of animacoes) a.cancel();
    animacoes.clear();
    voo?.remove(); voo = null;
    dialogo?.getAnimations({ subtree: true }).forEach(a => a.cancel());
    if (dialogo?.open) dialogo.close();
    if (conteudoInerte) { conteudoInerte.no.inert = conteudoInerte.anterior; conteudoInerte = null; }
    dialogo?.querySelector('[data-cofre-fragmentos]').replaceChildren();
    arrasto = null; escolhida = false;
    raiz.classList.remove('perfil-cofre-aberto', 'perfil-cofre-chegando', 'perfil-cofre-revelando');
    estado('fechado');
  }
  function irDireto() {
    const href = destino || acesso?.href;
    limpar();
    if (href) location.assign(href);
  }
  function cancelar() { limpar(); acesso?.focus({ preventScroll: true }); }
  function selecionar() {
    if (fase !== 'aguardando') return;
    escolhida = !escolhida;
    chave.setAttribute('aria-pressed', String(escolhida));
    cadeado.setAttribute('aria-disabled', String(!escolhida));
    mensagem.textContent = escolhida ? 'Chave selecionada. Ative o cadeado para encaixar.' : 'Arraste a chave até a fechadura.';
  }
  function centroFechadura() {
    const r = dialogo.querySelector('[data-cofre-fechadura]').getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  }
  async function abrirCadeado() {
    if (fase !== 'aguardando') return;
    const atual = operacao;
    arrasto = null;
    escolhida = false;
    chave.disabled = true;
    cadeado.setAttribute('aria-disabled', 'true');
    chave.setAttribute('aria-pressed', 'false');
    mensagem.textContent = 'Abrindo seu perfil…';
    estado('encaixando');
    const ponto = centroFechadura(), r = chave.getBoundingClientRect();
    Object.assign(chave.style, { position: 'fixed', left: r.left + 'px', top: r.top + 'px', transform: 'none' });
    const encaixe = `translate3d(${ponto.x - 12 - r.left}px,${ponto.y - 26 - r.top}px,0)`;
    try {
      await animar(chave, [
        { transform: 'translate3d(0,0,0) rotate(0deg)' },
        { transform: `${encaixe} rotate(0deg)` }
      ], tempos.encaixe);
      if (atual !== operacao) return;
      estado('girando');
      await animar(chave, [{ transform: `${encaixe} rotate(0deg)` }, { transform: `${encaixe} rotate(82deg)` }], tempos.giro);
      if (atual !== operacao) return;
      estado('fragmentando');
      const fragmentos = dialogo.querySelector('[data-cofre-fragmentos]');
      for (let i = 0; i < 18; i++) {
        const parte = document.createElement('i');
        const angulo = i * Math.PI * 2 / 18;
        const distancia = 95 + (i % 4) * 32;
        parte.style.setProperty('--cofre-x', Math.cos(angulo) * distancia + 'px');
        parte.style.setProperty('--cofre-y', Math.sin(angulo) * distancia + 'px');
        parte.style.setProperty('--cofre-rotacao', (i % 2 ? 160 : -140) + 'deg');
        parte.style.setProperty('--cofre-atraso', (i % 3) * 15 + 'ms');
        fragmentos.append(parte);
      }
      await animar(cadeado, [{ transform: 'scale(1)', opacity: 1 }, { transform: 'scale(1.12)', opacity: 0 }], tempos.fragmentos);
      if (atual !== operacao) return;
      // Apenas um marcador visual atravessa a navegação; nenhum dado de perfil.
      let guardou = false;
      try {
        sessionStorage.setItem(armazenamento, JSON.stringify({ versao: 1, instante: Date.now() }));
        guardou = true;
      } catch { /* Sem storage, o fade termina na página de origem. */ }
      if (!guardou) await animar(dialogo, [{ opacity: 1 }, { opacity: 0 }], tempos.navegacao);
      if (atual === operacao) location.assign(destino);
    } catch {
      if (atual === operacao) irDireto();
    }
  }
  async function abrir(evento) {
    if (evento.button !== 0 || evento.ctrlKey || evento.metaKey || evento.shiftKey || evento.altKey ||
        !movimento() || !Element.prototype.animate || !dialogo?.show) return;
    evento.preventDefault();
    if (fase !== 'fechado') return;
    destino = evento.currentTarget.href;
    const atual = ++operacao;
    chave.disabled = true;
    chave.removeAttribute('style');
    cadeado.removeAttribute('style');
    chave.setAttribute('aria-pressed', 'false');
    cadeado.setAttribute('aria-disabled', 'true');
    mensagem.textContent = 'Preparando seu espaço…';
    const foto = dialogo.querySelector('[data-cofre-foto]');
    const avatar = acesso.querySelector('[data-conta-inicial]');
    const origem = avatar.getBoundingClientRect();
    foto.replaceChildren();
    const imagem = avatar?.querySelector('img');
    if (imagem) {
      const copia = document.createElement('img'); copia.src = imagem.src; copia.alt = ''; foto.append(copia);
    } else foto.textContent = avatar?.textContent || '';
    try {
      medirArea(); dialogo.show();
      const conteudo = document.querySelector('.corpo') || document.querySelector('main');
      if (conteudo) { conteudoInerte = { no: conteudo, anterior: conteudo.inert }; conteudo.inert = true; }
      raiz.classList.add('perfil-cofre-aberto'); estado('abertura');
      const alvo = foto.getBoundingClientRect();
      voo = document.createElement('div'); voo.className = 'perfil-cofre-voo'; voo.setAttribute('aria-hidden', 'true');
      if (imagem) { const img = document.createElement('img'); img.src = imagem.src; img.alt = ''; voo.append(img); }
      else voo.textContent = foto.textContent;
      Object.assign(voo.style, { left: alvo.left + 'px', top: alvo.top + 'px', width: alvo.width + 'px', height: alvo.height + 'px' });
      const inicio = `translate3d(${origem.left - alvo.left}px,${origem.top - alvo.top}px,0) scale(${origem.width / alvo.width},${origem.height / alvo.height})`;
      document.body.append(voo);
      await Promise.all([
        animar(dialogo, [{ opacity: 0 }, { opacity: 1, offset: .24 }, { opacity: 1 }], tempos.abertura),
        animar(voo, [
          { transform: inicio, opacity: 1, borderRadius: '0' },
          { transform: 'translate3d(0,0,0) scale(1)', opacity: 1, borderRadius: '0', offset: .72 },
          { transform: 'translate3d(0,0,0) scale(1,.7857)', opacity: 0, borderRadius: '9px' }
        ], tempos.abertura)
      ]);
      if (atual !== operacao) return;
      voo.remove(); voo = null;
      estado('aguardando'); chave.disabled = false;
      mensagem.textContent = 'Arraste a chave até a fechadura.';
      chave.focus({ preventScroll: true });
    } catch { if (atual === operacao) irDireto(); }
  }
  function pegar(evento) {
    if (fase !== 'aguardando' || (evento.pointerType === 'mouse' && evento.button !== 0)) return;
    const r = chave.getBoundingClientRect();
    arrasto = { id: evento.pointerId, x: evento.clientX, y: evento.clientY, dx: evento.clientX - r.left, dy: evento.clientY - r.top, moveu: false };
    chave.setPointerCapture(evento.pointerId);
  }
  function mover(evento) {
    if (!arrasto || arrasto.id !== evento.pointerId) return;
    arrasto.moveu ||= Math.hypot(evento.clientX - arrasto.x, evento.clientY - arrasto.y) > 6;
    if (!arrasto.moveu) return;
    evento.preventDefault();
    Object.assign(chave.style, {
      position: 'fixed',
      left: Math.max(0, Math.min(innerWidth - chave.offsetWidth, evento.clientX - arrasto.dx)) + 'px',
      top: Math.max(0, Math.min(innerHeight - chave.offsetHeight, evento.clientY - arrasto.dy)) + 'px',
      transform: 'rotate(0deg)'
    });
    const ponto = centroFechadura();
    dialogo.dataset.perto = String(Math.hypot(evento.clientX - ponto.x, evento.clientY - ponto.y) <= 66);
  }
  function soltar(evento) {
    if (!arrasto || arrasto.id !== evento.pointerId) return;
    const moveu = arrasto.moveu, ponto = centroFechadura(), r = chave.getBoundingClientRect();
    arrasto = null;
    if (chave.hasPointerCapture(evento.pointerId)) chave.releasePointerCapture(evento.pointerId);
    delete dialogo.dataset.perto;
    if (!moveu) return; // O click normal seleciona a chave para toque ou teclado.
    suprimirClique = true;
    setTimeout(() => { suprimirClique = false; }, 0);
    const encaixou = Math.hypot(evento.clientX - ponto.x, evento.clientY - ponto.y) <= 66 ||
      Math.hypot(r.left + 12 - ponto.x, r.top + 26 - ponto.y) <= 44;
    if (encaixou) abrirCadeado();
    else {
      chave.removeAttribute('style');
      mensagem.textContent = 'Aproxime a chave do centro do cadeado e solte.';
    }
  }
  let suprimirClique = false;
  function interromperArrasto() {
    arrasto = null;
    if (fase === 'aguardando') chave.removeAttribute('style');
    if (dialogo) delete dialogo.dataset.perto;
  }
  function revelar() {
    if (!chegada || revelando) return;
    revelando = true;
    raiz.classList.add('perfil-cofre-revelando');
    const finalizar = () => {
      if (!chegada) return;
      chegada = null;
      raiz.classList.remove('perfil-cofre-chegando', 'perfil-cofre-revelando');
      estado('fechado');
      const titulo = document.getElementById('titulo');
      if (titulo) { titulo.setAttribute('tabindex', '-1'); titulo.focus({ preventScroll: true }); }
    };
    raiz.addEventListener('animationend', evento => { if (evento.animationName === 'perfil-cofre-revelar') finalizar(); }, { once: true });
    setTimeout(finalizar, tempos.navegacao + 100);
  }
  window.addEventListener('spectra:perfil-pronto', revelar);
  window.addEventListener('pagereveal', evento => {
    if (chegada && evento.viewTransition) { evento.viewTransition.ready.catch(() => {}); evento.viewTransition.skipTransition(); }
  });
  window.addEventListener('pageswap', evento => {
    if (fase !== 'fechado' && evento.viewTransition) { evento.viewTransition.ready.catch(() => {}); evento.viewTransition.skipTransition(); }
  });
  window.addEventListener('pageshow', evento => { if (evento.persisted) { chegada = null; limpar(); } });
  window.addEventListener('spectra:movimento', () => {
    if (!movimento() && fase !== 'fechado') { if (chegada) limpar(); else irDireto(); }
  });
  window.addEventListener('resize', interromperArrasto);
  window.addEventListener('resize', medirArea);
  document.addEventListener('keydown', evento => {
    if (evento.key === 'Escape' && fase !== 'fechado' && !document.querySelector('dialog:modal')) {
      evento.preventDefault(); cancelar();
    }
  });
  document.addEventListener('click', evento => {
    if (fase !== 'fechado' && evento.target.closest('.trilho a, .barra-abas a, .gaveta-menu a')) limpar();
  }, true);
  function iniciar() {
    acesso = document.querySelector('[data-perfil-acesso]');
    dialogo = document.querySelector('[data-perfil-cofre]');
    if (!acesso || !dialogo) { raiz.classList.remove('perfil-cofre-chegando'); return; }
    chave = dialogo.querySelector('[data-cofre-chave]');
    cadeado = dialogo.querySelector('[data-cofre-cadeado]');
    mensagem = dialogo.querySelector('[data-cofre-mensagem]');
    acesso.addEventListener('click', abrir);
    chave.addEventListener('pointerdown', pegar);
    chave.addEventListener('pointermove', mover);
    chave.addEventListener('pointerup', soltar);
    chave.addEventListener('pointercancel', interromperArrasto);
    chave.addEventListener('lostpointercapture', () => { if (arrasto) interromperArrasto(); });
    chave.addEventListener('click', () => { if (!suprimirClique) selecionar(); });
    cadeado.addEventListener('click', () => { if (escolhida) abrirCadeado(); });
    dialogo.querySelector('[data-cofre-cancelar]').addEventListener('click', cancelar);
    dialogo.addEventListener('cancel', evento => { evento.preventDefault(); cancelar(); });
    if (chegada) { medirArea(); estado('revelando'); setTimeout(revelar, 2500); }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar, { once: true });
  else iniciar();
})();
