/* Grade de cubos — visual do hero da entrada.
 *
 * Porte do exemplo Three.js + anime.js para o site, com quatro mudanças que o
 * exemplo original não precisava ter e uma página de produção precisa:
 *
 *   1. versões fixadas no esm.sh (sem pin, uma publicação do CDN quebra a home);
 *   2. o laço de render para quando a aba está oculta ou o hero sai da tela —
 *      sem isso a GPU fica desenhando 216 cubos para ninguém, gastando bateria;
 *   3. `prefers-reduced-motion` desenha um quadro parado em vez de animar;
 *   4. paleta da marca no lugar do arco-íris do exemplo.
 *
 * É um módulo ES: carregado com <script type="module">, roda depois do DOM.
 */

// Especificadores nus: as URLs reais estão no import map de inicio.html, que
// é o que mantém uma cópia só do Three.js.
import { animate, createTimer, stagger } from "animejs";
import * as THREE from "three";
import { commitChanges, getInstances } from "animejs/adapters/three";

const alvo = document.getElementById("cubos");
if (alvo) {
  try {
    iniciar(alvo);
  } catch (erro) {
    // Fundo decorativo que depende de CDN de terceiro: se falhar, a página
    // continua inteira e utilizável. Só o enfeite some.
    console.warn("Grade de cubos indisponível:", erro);
    alvo.remove();
  }
}

function iniciar(container) {
  // O estado vem de movimento.js, que já resolveu preferência do sistema +
  // escolha explícita da pessoa. Ler `matchMedia` aqui ignoraria a escolha.
  const ligado = window.spectraMovimentoLigado
    ? window.spectraMovimentoLigado()
    : !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const reduzido = !ligado;

  let { clientWidth: largura, clientHeight: altura } = container;
  if (!largura || !altura) return;

  // ── cena

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  // O exemplo usa devicePixelRatio cheio; em tela 3x isso é 9x os pixels por
  // um fundo decorativo. Teto de 2 mantém a nitidez sem o custo.
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(largura, altura);
  container.appendChild(renderer.domElement);

  const cena = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, largura / altura, 0.01, 100);
  cena.add(camera);

  // A câmera fixa em z=1.5 funciona em tela larga. Em tela estreita o recorte
  // vertical faz os cubos engolirem a manchete — então ela recua conforme a
  // largura, mantendo a grade como fundo em vez de primeiro plano.
  const posicionarCamera = (l, a) => {
    camera.aspect = l / a;
    camera.position.z = l < 520 ? 3.2 : l < 900 ? 2.4 : 1.5;
    camera.updateProjectionMatrix();
  };
  posicionarCamera(largura, altura);

  cena.add(new THREE.AmbientLight(0xffffff, 0.4));
  const luz = new THREE.DirectionalLight(0xffffff, 2.2);
  luz.position.set(2, 3, 4);
  cena.add(luz);

  // ── malha instanciada

  const lado = 6;                          // cubos por eixo → 216 no total
  const celula = 2 / lado;
  const alcance = ((lado - 1) / 2) * celula;

  const geometria = new THREE.BoxGeometry(celula, celula, celula);
  const material = new THREE.MeshLambertMaterial();
  const malha = new THREE.InstancedMesh(geometria, material, lado ** 3);
  cena.add(malha);

  // Paleta da marca, não o arco-íris do exemplo. Família teal/sage com uma
  // única entrada amarela em doze (~8% dos cubos): no design system o amarelo
  // é o tertiary, cor de atenção — em 1/6 dos cubos ele dominava o hero e
  // brigava com a manchete.
  const paleta = [
    "#118e94", "#3fb6bb", "#5b9986", "#1a6d72",
    "#118e94", "#2e7f7a", "#3fb6bb", "#5b9986",
    "#118e94", "#fffc0e", "#1a6d72", "#3fb6bb",
  ];

  // O InstancedMesh só aceita cor por instância depois que `instanceColor`
  // existe, e ele só é alocado no primeiro `setColorAt`. Sem esta semeadura,
  // a animação de `color` roda mas não aparece: os cubos ficam brancos.
  const semente = new THREE.Color();
  for (let i = 0; i < malha.count; i += 1) {
    malha.setColorAt(i, semente.set(paleta[i % paleta.length]));
  }
  malha.instanceColor.needsUpdate = true;

  const instancias = getInstances(malha);
  const eixo = (nome, span = alcance) =>
    stagger([-span, span], { grid: [lado, lado, lado], axis: nome });

  // O exemplo original faz `animate(malha, { rotateY: 360 })`, que depende do
  // adapter do Three estar auto-registrado no anime.js. Neste build do esm.sh
  // ele não está, e `rotateY` acaba resolvido como o MÉTODO Object3D.rotateY
  // (erro "i.includes is not a function"). Animar `malha.rotation` direto é um
  // objeto simples de números — funciona sem adapter. Radianos, não graus.
  const volta = Math.PI * 2;
  const rotacao = animate(malha.rotation, {
    y: volta,
    x: volta,
    duration: 26000,
    loop: true,
    ease: "linear",
    autoplay: !reduzido,
  });

  const pulso = animate(instancias, {
    color: paleta,
    x: [eixo("x", alcance * 0.25), eixo("x")],
    y: [eixo("y", alcance * 0.25), eixo("y")],
    z: [eixo("z", alcance * 0.25), eixo("z")],
    scale: [0.1, 0.26, 0.1],
    delay: stagger([0, 3000], {
      grid: [lado, lado, lado],
      from: "center",
      reversed: true,
    }),
    duration: 2000,
    loopDelay: 500,
    loop: true,
    alternate: true,
    ease: "inOutQuad",
    autoplay: !reduzido,
  });

  // ── laço de render, com pausa

  // `commitChanges` grava nas matrizes da InstancedMesh o que as animações
  // mudaram nos proxies. Sem adapter registrado, é preciso chamar à mão.
  const desenhar = () => {
    commitChanges(malha);
    renderer.render(cena, camera);
  };
  const relogio = createTimer({ onUpdate: desenhar, autoplay: !reduzido });

  if (reduzido) {
    // Um quadro parado — mas não o quadro zero, que é a grade branca fechada.
    // Avançamos as duas animações até um ponto representativo para que a
    // composição estática já mostre a paleta e o espalhamento.
    rotacao.seek(6500);          // ~1/4 de volta: vista em três quartos
    pulso.seek(2000);            // fim da expansão, cubos coloridos e abertos
    desenhar();
    return;
  }

  let naTela = true;
  let abaVisivel = !document.hidden;

  const sincronizar = () => {
    const rodar = naTela && abaVisivel;
    for (const alvo of [relogio, rotacao, pulso]) {
      if (rodar) alvo.play();
      else alvo.pause();
    }
  };

  new IntersectionObserver(
    ([entrada]) => {
      naTela = entrada.isIntersecting;
      sincronizar();
    },
    { threshold: 0 }
  ).observe(container);

  document.addEventListener("visibilitychange", () => {
    abaVisivel = !document.hidden;
    sincronizar();
  });

  // ── redimensionamento

  new ResizeObserver(() => {
    const { clientWidth: l, clientHeight: a } = container;
    if (!l || !a) return;
    largura = l;
    altura = a;
    posicionarCamera(l, a);
    renderer.setSize(l, a);
    desenhar();
  }).observe(container);

  // Trocar o interruptor recarrega: a cena WebGL lê o estado na montagem, e
  // recriar tudo ao vivo seria um segundo caminho de código para manter.
  window.addEventListener("spectra:movimento", () => window.location.reload());

  // ── faxina

  window.addEventListener("pagehide", () => {
    relogio.pause();
    geometria.dispose();
    material.dispose();
    renderer.dispose();
  });
}
