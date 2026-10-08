/* Glossário de termos técnicos — fonte única para dois lugares:
 *   1) a tela /painel/aprender, que lista todos os termos;
 *   2) os botões "?" ao lado de termos técnicos no laudo (/painel),
 *      que abrem só a definição daquele termo.
 *
 * Manter num só lugar evita que as duas telas expliquem o mesmo termo de
 * jeitos diferentes.
 */

const GLOSSARIO = {
  https: {
    titulo: "HTTPS",
    texto: "Versão do protocolo HTTP com criptografia. Sem ele, tudo que você digita numa página trafega em texto puro e pode ser lido por quem estiver na mesma rede.",
  },
  tls: {
    titulo: "Certificado TLS",
    texto: "O documento digital que prova, criptograficamente, que a conexão com aquele servidor está protegida. É o que o cadeado do navegador representa — não prova que o site é honesto, só que a conexão é privada.",
  },
  rdap: {
    titulo: "RDAP",
    texto: "Registration Data Access Protocol — sucessor do WHOIS. Mostra quando um domínio foi registrado, quando vence e o status dele no registro.",
  },
  dns: {
    titulo: "DNS",
    texto: "O sistema que traduz um nome de domínio (como exemplo.com) para o endereço IP do servidor que hospeda o site.",
  },
  spf: {
    titulo: "SPF",
    texto: "Sender Policy Framework — registro DNS que lista quem tem permissão para enviar e-mail em nome de um domínio. Sem ele, é mais fácil falsificar remetente.",
  },
  dmarc: {
    titulo: "DMARC",
    texto: "Diz ao provedor de e-mail (Gmail, Outlook...) o que fazer quando alguém tenta enviar e-mail falsificando o seu domínio: nada, quarentena ou rejeitar.",
  },
  caa: {
    titulo: "CAA",
    texto: "Certification Authority Authorization — registro DNS que limita quais autoridades certificadoras podem emitir certificado para aquele domínio.",
  },
  tld: {
    titulo: "TLD",
    texto: "Top-Level Domain — a última parte de um domínio (.com, .br, .xyz). Algumas extensões são muito baratas ou gratuitas e por isso concentram mais golpes.",
  },
  punycode: {
    titulo: "Punycode",
    texto: "Forma de escrever letras acentuadas ou de outros alfabetos (como cirílico) dentro de um domínio, que só aceita caracteres ASCII. Aparece como 'xn--...' e pode ser usado para criar domínios visualmente idênticos a um real.",
  },
  typosquatting: {
    titulo: "Typosquatting",
    texto: "Registrar um domínio quase igual a um real, apostando em erro de digitação de quem digita o endereço (ex.: 'gogle.com' em vez de 'google.com').",
  },
  phishing: {
    titulo: "Phishing",
    texto: "Golpe que finge ser uma empresa ou pessoa confiável para roubar senha, dados de cartão ou outras informações, geralmente por link ou mensagem.",
  },
  homoglifo: {
    titulo: "Homóglifo",
    texto: "Caractere de outro alfabeto que se parece com uma letra latina (como o 'а' cirílico, idêntico ao 'a'). Usado para criar domínios visualmente idênticos a um real.",
  },
  encurtador: {
    titulo: "Encurtador de link",
    texto: "Serviço que transforma uma URL longa numa curta (bit.ly, tinyurl...). Não é malicioso por si só, mas esconde para onde o link realmente vai.",
  },
};

/** Cria o botão "?" que abre a definição de um termo, ancorado ao lado dele. */
function botaoTermo(chave) {
  const termo = GLOSSARIO[chave];
  const botao = document.createElement("button");
  botao.type = "button";
  botao.className = "termo-ajuda";
  botao.setAttribute("aria-expanded", "false");
  botao.setAttribute("aria-label", termo ? `O que é ${termo.titulo}?` : "O que é isso?");
  botao.textContent = "?";
  botao.addEventListener("click", () => alternarBalaoTermo(botao, chave));
  return botao;
}

function alternarBalaoTermo(botao, chave) {
  const aberto = botao.getAttribute("aria-expanded") === "true";
  document.querySelectorAll(".termo-balao").forEach((b) => b.remove());
  document.querySelectorAll('.termo-ajuda[aria-expanded="true"]').forEach((b) => b.setAttribute("aria-expanded", "false"));
  if (aberto) return;

  const termo = GLOSSARIO[chave];
  if (!termo) return;
  const balao = document.createElement("span");
  balao.className = "termo-balao";
  balao.setAttribute("role", "tooltip");
  const titulo = document.createElement("strong");
  titulo.textContent = termo.titulo;
  const texto = document.createElement("span");
  texto.textContent = termo.texto;
  balao.append(titulo, texto);
  botao.after(balao);
  botao.setAttribute("aria-expanded", "true");

  const fechar = (evento) => {
    if (evento.key === "Escape" || (!balao.contains(evento.target) && evento.target !== botao)) {
      balao.remove();
      botao.setAttribute("aria-expanded", "false");
      document.removeEventListener("click", fechar);
      document.removeEventListener("keydown", fechar);
    }
  };
  setTimeout(() => {
    document.addEventListener("click", fechar);
    document.addEventListener("keydown", fechar);
  }, 0);
}

/** Substitui todo [data-termo="chave"] pelo próprio texto + botão de ajuda. */
function montarTermosDeAjuda() {
  document.querySelectorAll("[data-termo]").forEach((el) => {
    const chave = el.dataset.termo;
    if (!GLOSSARIO[chave] || el.querySelector(".termo-ajuda")) return;
    el.append(" ", botaoTermo(chave));
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", montarTermosDeAjuda);
} else {
  montarTermosDeAjuda();
}

window.GLOSSARIO = GLOSSARIO;
window.montarTermosDeAjuda = montarTermosDeAjuda;
