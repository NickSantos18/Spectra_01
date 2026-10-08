/* Spectra — tela de entrada: modais de acesso e widget do assistente.
 *
 * JavaScript puro, sem dependência. Todo texto que vem de fora entra por
 * textContent — nunca innerHTML — porque a mensagem do chat é escrita pelo
 * usuário e não pode virar injeção na própria página.
 */

const $ = (id) => document.getElementById(id);

/* ══════════════════════════════════════════════ modal de acesso */

const modal = $("modal");
const caixa = $("modal-caixa");
const abas = { entrar: $("aba-entrar"), cadastrar: $("aba-cadastrar") };
const paineis = { entrar: $("painel-entrar"), cadastrar: $("painel-cadastrar") };

const CLASSES_ABA_ATIVA = ["text-txt", "border-b-2", "border-marca", "bg-sup-2"];
const CLASSES_ABA_INATIVA = ["text-txt-3"];

let disparador = null; // quem abriu o modal — o foco volta para cá ao fechar

function selecionarAba(nome) {
  for (const [chave, aba] of Object.entries(abas)) {
    const ativa = chave === nome;
    aba.setAttribute("aria-selected", String(ativa));
    aba.classList.toggle("text-txt", ativa);
    aba.classList.toggle("bg-sup-2", ativa);
    aba.classList.toggle("text-txt-3", !ativa);
    paineis[chave].hidden = !ativa;
  }
  $("modal-titulo").textContent =
    nome === "entrar" ? "Acessar o Spectra" : "Criar conta no Spectra";
}

function focaveis() {
  return [...caixa.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )].filter((el) => !el.disabled && el.offsetParent !== null);
}

function abrirModal(nome) {
  disparador = document.activeElement;
  selecionarAba(nome);
  modal.classList.remove("hidden");
  modal.classList.add("flex");
  document.body.style.overflow = "hidden";
  // Primeiro campo do painel visível, não a aba: quem abriu já quer digitar.
  const primeiro = paineis[nome].querySelector("input");
  if (primeiro) primeiro.focus();
}

function fecharModal() {
  modal.classList.add("hidden");
  modal.classList.remove("flex");
  document.body.style.overflow = "";
  limparAvisos();
  if (disparador) disparador.focus();
}

for (const botao of document.querySelectorAll("[data-abrir]")) {
  botao.addEventListener("click", () => abrirModal(botao.dataset.abrir));
}
abas.entrar.addEventListener("click", () => selecionarAba("entrar"));
abas.cadastrar.addEventListener("click", () => selecionarAba("cadastrar"));
$("fechar-modal").addEventListener("click", fecharModal);
$("modal-fundo").addEventListener("click", fecharModal);

document.addEventListener("keydown", (evento) => {
  if (modal.classList.contains("hidden")) return;

  if (evento.key === "Escape") {
    fecharModal();
    return;
  }
  // Prende o foco dentro do modal enquanto ele estiver aberto.
  if (evento.key === "Tab") {
    const lista = focaveis();
    if (!lista.length) return;
    const primeiro = lista[0];
    const ultimo = lista[lista.length - 1];
    if (evento.shiftKey && document.activeElement === primeiro) {
      evento.preventDefault();
      ultimo.focus();
    } else if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault();
      primeiro.focus();
    }
  }
});

/* ── mostrar / esconder senha */

for (const botao of document.querySelectorAll("[data-ver-senha]")) {
  botao.addEventListener("click", () => {
    const campo = $(botao.dataset.verSenha);
    const escondida = campo.type === "password";
    campo.type = escondida ? "text" : "password";
    botao.setAttribute("aria-label", escondida ? "Ocultar senha" : "Mostrar senha");
    campo.focus();
  });
}

/* ══════════════════════════════════════════════ validação */

const RE_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function mostrarErro(idCampo, mensagem) {
  const campo = $(idCampo);
  const alvo = document.querySelector(`[data-erro-de="${idCampo}"]`);
  if (alvo) {
    alvo.textContent = mensagem;
    alvo.classList.toggle("hidden", !mensagem);
  }
  if (campo) {
    campo.setAttribute("aria-invalid", mensagem ? "true" : "false");
    campo.classList.toggle("border-perigo", Boolean(mensagem));
    campo.classList.toggle("border-linha", !mensagem);
  }
}

function limparAvisos() {
  for (const alvo of document.querySelectorAll(".erro")) {
    alvo.textContent = "";
    alvo.classList.add("hidden");
  }
  for (const campo of document.querySelectorAll("[aria-invalid='true']")) {
    campo.setAttribute("aria-invalid", "false");
    campo.classList.remove("border-perigo");
    campo.classList.add("border-linha");
  }
  for (const aviso of document.querySelectorAll(".aviso-form")) {
    aviso.classList.add("hidden");
  }
}

function avisarNoForm(form, texto) {
  const aviso = form.querySelector(".aviso-form");
  aviso.textContent = texto;
  aviso.classList.remove("hidden");
}

/* ── entrar */

paineis.entrar.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  limparAvisos();

  const email = $("entrar-email").value.trim();
  const senha = $("entrar-senha").value;
  let ok = true;

  if (!RE_EMAIL.test(email)) {
    mostrarErro("entrar-email", "Digite um e-mail válido.");
    ok = false;
  }
  if (!senha) {
    mostrarErro("entrar-senha", "Digite sua senha.");
    ok = false;
  }
  if (!ok) return;

  const botao = paineis.entrar.querySelector('button[type="submit"]');
  botao.disabled = true;
  botao.textContent = "Entrando…";

  try {
    const resp = await fetch("/api/auth/entrar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, senha }),
    });
    const corpo = await resp.json();

    if (resp.ok) {
      // Sessão criada em cookie HttpOnly pelo servidor — nada é guardado aqui.
      window.location.href = "/painel";
      return;
    }
    avisarNoForm(paineis.entrar, corpo.erro || corpo.detail || "Não foi possível entrar.");
  } catch (erro) {
    avisarNoForm(paineis.entrar, `Sem resposta do servidor: ${erro.message}`);
  } finally {
    botao.disabled = false;
    botao.textContent = "Entrar";
  }
});

/* ── cadastrar */

paineis.cadastrar.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  limparAvisos();

  const nome = $("cad-nome").value.trim();
  const email = $("cad-email").value.trim();
  const senha = $("cad-senha").value;
  const senha2 = $("cad-senha2").value;
  const termos = $("cad-termos").checked;
  let ok = true;

  if (nome.length < 3) {
    mostrarErro("cad-nome", "Digite seu nome completo.");
    ok = false;
  }
  if (!RE_EMAIL.test(email)) {
    mostrarErro("cad-email", "Digite um e-mail válido.");
    ok = false;
  }
  if (senha.length < 8) {
    mostrarErro("cad-senha", "A senha precisa de pelo menos 8 caracteres.");
    ok = false;
  }
  if (senha2 !== senha) {
    mostrarErro("cad-senha2", "As senhas não são iguais.");
    ok = false;
  }
  if (!termos) {
    mostrarErro("cad-termos", "É preciso aceitar os Termos de Uso para criar a conta.");
    ok = false;
  }
  if (!ok) return;

  const botao = paineis.cadastrar.querySelector('button[type="submit"]');
  botao.disabled = true;
  botao.textContent = "Criando conta…";

  try {
    const resp = await fetch("/api/auth/cadastrar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome, email, senha }),
    });
    const corpo = await resp.json();

    if (resp.status === 201) {
      window.location.href = "/painel";
      return;
    }
    if (resp.status === 409) {
      mostrarErro("cad-email", "Já existe uma conta com este e-mail.");
      return;
    }
    avisarNoForm(paineis.cadastrar, corpo.erro || corpo.detail || "Não foi possível criar a conta.");
  } catch (erro) {
    avisarNoForm(paineis.cadastrar, `Sem resposta do servidor: ${erro.message}`);
  } finally {
    botao.disabled = false;
    botao.textContent = "Criar conta";
  }
});

/* ── esqueci minha senha */

$("esqueci").addEventListener("click", async () => {
  limparAvisos();
  const email = $("entrar-email").value.trim();
  if (!RE_EMAIL.test(email)) {
    mostrarErro("entrar-email", "Digite seu e-mail acima para receber o link.");
    $("entrar-email").focus();
    return;
  }
  // A resposta é a mesma exista ou não a conta — dizer "não existe" entregaria
  // a lista de e-mails válidos a quem estiver testando.
  try {
    const resp = await fetch("/api/auth/recuperar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const corpo = await resp.json();
    avisarNoForm(paineis.entrar, corpo.mensagem || "Pedido registrado.");
  } catch (erro) {
    avisarNoForm(paineis.entrar, `Sem resposta do servidor: ${erro.message}`);
  }
});

/* ══════════════════════════════════════════════ assistente */

const chat = $("chat");
const botaoChat = $("abrir-chat");
const mensagens = $("chat-mensagens");
const sugestoes = $("chat-sugestoes");

const BOAS_VINDAS = "Olá! Como posso te ajudar a navegar por esta página hoje?";

// Respostas simuladas. Trocar pela API real — ver comentário em responder().
const RESPOSTAS = [
  {
    gatilho: ["cadastr", "criar conta", "conta nova", "registr"],
    rotulo: "Como me cadastrar?",
    texto:
      "Clique em Cadastrar-se, no topo ou no meio da página. Você preenche nome, " +
      "e-mail e senha, aceita os termos e recebe um link de confirmação por e-mail. " +
      "A conta fica ativa depois que você clica nesse link.",
  },
  {
    gatilho: ["esqueci", "senha", "recuperar", "redefinir"],
    rotulo: "Esqueci minha senha",
    texto:
      "Abra Entrar, digite seu e-mail no campo e clique em “Esqueci minha senha”. " +
      "Mandamos um link de redefinição para esse endereço. O link vale por 30 minutos " +
      "e só pode ser usado uma vez.",
  },
  {
    gatilho: ["como funciona", "plataforma", "o que é", "produto", "spectra faz"],
    rotulo: "Como funciona a plataforma?",
    texto:
      "Você cadastra o endereço da sua aplicação e o Spectra faz uma varredura. " +
      "Cada falha encontrada vira uma ficha com três coisas: a requisição que provou " +
      "o problema, o que ele custa em risco de negócio, e a correção pronta no seu " +
      "framework. Se você conectar o repositório, dá para abrir o pull request direto daqui.",
  },
  {
    gatilho: ["preço", "custo", "quanto custa", "plano", "grátis"],
    rotulo: "Quanto custa?",
    texto:
      "Ainda não tenho a tabela de planos para te passar. Assim que ela existir, " +
      "aparece aqui e na página. Enquanto isso, dá para criar conta e rodar a " +
      "primeira varredura.",
  },
];

const PADRAO =
  "Não sei responder isso ainda. Posso ajudar com cadastro, recuperação de senha " +
  "e como a plataforma funciona — ou você fala com o time pelo e-mail de suporte.";

function balao(texto, autor) {
  const linha = document.createElement("div");
  const bolha = document.createElement("div");

  bolha.textContent = texto;
  bolha.className =
    "max-w-[85%] rounded-lg px-3.5 py-2.5 text-sm leading-relaxed " +
    (autor === "bot"
      ? "self-start bg-sup-2 text-txt-2 rounded-bl-sm"
      : "self-end bg-marca text-base rounded-br-sm");

  linha.className = "flex flex-col";
  linha.append(bolha);
  mensagens.append(linha);
  mensagens.scrollTop = mensagens.scrollHeight;
  return bolha;
}

function digitando() {
  const bolha = balao("…", "bot");
  bolha.classList.add("text-txt-3");
  return bolha;
}

function responder(pergunta) {
  // ╔══════════════════════════════════════════════════════════════════╗
  // ║  INTEGRAR A API DO CHATBOT AQUI                                  ║
  // ║                                                                  ║
  // ║  const r = await fetch("/api/copilot", {                         ║
  // ║    method: "POST",                                               ║
  // ║    headers: { "Content-Type": "application/json" },              ║
  // ║    body: JSON.stringify({ mensagem: pergunta, contexto: "landing" })
  // ║  });                                                             ║
  // ║  const { resposta } = await r.json();                            ║
  // ║  return resposta;                                                ║
  // ║                                                                  ║
  // ║  Continue escrevendo a resposta com textContent (função balao):  ║
  // ║  conteúdo gerado por LLM não deve ser injetado como HTML.        ║
  // ╚══════════════════════════════════════════════════════════════════╝
  const alvo = pergunta.toLowerCase();
  const achada = RESPOSTAS.find((r) => r.gatilho.some((g) => alvo.includes(g)));
  return achada ? achada.texto : PADRAO;
}

function enviar(texto) {
  const pergunta = texto.trim();
  if (!pergunta) return;

  balao(pergunta, "eu");
  $("chat-campo").value = "";

  const espera = digitando();
  setTimeout(() => {
    espera.textContent = responder(pergunta);
    espera.classList.remove("text-txt-3");
    mensagens.scrollTop = mensagens.scrollHeight;
  }, 450);
}

function montarSugestoes() {
  sugestoes.replaceChildren();
  for (const item of RESPOSTAS.slice(0, 3)) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.textContent = item.rotulo;
    chip.className =
      "rounded-full border border-linha-forte px-3 py-1.5 text-xs text-txt-2 " +
      "transition hover:border-marca hover:text-marca-claro " +
      "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-marca-claro";
    chip.addEventListener("click", () => enviar(item.rotulo));
    sugestoes.append(chip);
  }
}

function alternarChat(abrir) {
  chat.hidden = !abrir;
  botaoChat.setAttribute("aria-expanded", String(abrir));
  if (abrir) {
    if (!mensagens.childElementCount) {
      balao(BOAS_VINDAS, "bot");
      montarSugestoes();
    }
    $("chat-campo").focus();
  } else {
    botaoChat.focus();
  }
}

botaoChat.addEventListener("click", () => alternarChat(chat.hidden));
$("fechar-chat").addEventListener("click", () => alternarChat(false));

$("chat-form").addEventListener("submit", (evento) => {
  evento.preventDefault();
  enviar($("chat-campo").value);
});

document.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape" && !chat.hidden) alternarChat(false);
});

/* ══════════════════════════════════════════════ estado vindo do servidor */

const MOTIVOS = {
  entre_primeiro: "Entre na sua conta para abrir o painel.",
  google_indisponivel: "O login com Google não está configurado neste servidor.",
  google_cancelado: "Login com Google cancelado.",
  google_estado: "A volta do Google não confere. Tente entrar de novo.",
  google_falhou: "Não foi possível concluir o login com Google.",
};

const motivo = new URLSearchParams(location.search).get("erro");
if (motivo && MOTIVOS[motivo]) {
  const faixa = $("faixa-erro");
  faixa.textContent = MOTIVOS[motivo];
  faixa.hidden = false;
  if (motivo === "entre_primeiro") abrirModal("entrar");
}

// O botão do Google só é oferecido se o servidor tiver as credenciais.
fetch("/api/auth/provedores")
  .then((r) => r.json())
  .then(({ google }) => {
    if (google) return;
    $("botao-google").hidden = true;
    $("google-indisponivel").hidden = false;
  })
  .catch(() => {});

// Quem já tem sessão não precisa ver a porta de entrada.
fetch("/api/auth/eu")
  .then((r) => r.json())
  .then(({ usuario }) => {
    if (!usuario) return;
    for (const botao of document.querySelectorAll("[data-abrir]")) {
      botao.textContent = "Abrir painel";
      botao.dataset.abrir = "";
      botao.addEventListener("click", () => { window.location.href = "/painel"; }, true);
    }
  })
  .catch(() => {});

/* ══════════════════════════════════════════════ caminhos e manchete
 *
 * A geração vive em caminhos.js, compartilhada com o painel.
 */

desenharCaminhosFlutuantes($("caminhos-a"), 1);
desenharCaminhosFlutuantes($("caminhos-b"), -1);

const manchete = $("manchete");
if (manchete) animarPorLetra(manchete, manchete.dataset.texto, { atrasoInicial: 0.12 });
