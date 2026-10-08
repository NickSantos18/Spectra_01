"""Etapa 1 — Validação sintática da URL (100% offline).

Trabalha apenas sobre a *string* recebida: nenhuma conexão de rede, nenhuma
resolução de DNS, nenhum acesso ao site. É a parte mais barata e mais segura da
análise, e sozinha já pega a maioria dos golpes de phishing por link.

Procura por:
  * typosquatting (domínio a 1-2 caracteres de uma marca real);
  * homóglifos / IDN spoofing (domínio visualmente idêntico ao real);
  * impersonação por subdomínio (marca no subdomínio, dono do domínio é outro);
  * ofuscação do destino (userinfo "@", IP literal, URL embutida, encurtador);
  * subdomínios em excesso, TLD de risco, palavras-isca, anexo executável.
"""

from __future__ import annotations

import ipaddress
import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit

from .dados import (
    CONFUSAVEIS,
    DIGRAFOS_CONFUSAVEIS,
    ENCURTADORES,
    ESQUEMAS_PERIGOSOS,
    EXTENSOES_EXECUTAVEIS,
    ISCAS,
    MARCAS_OFICIAIS,
    SUFIXOS_COMPOSTOS,
    TLDS_DE_RISCO,
)
from .models import Achado, CriterioChecklist, Severidade

try:  # opcional: Public Suffix List completa
    import tldextract as _tldextract
except ImportError:  # pragma: no cover - caminho de fallback
    _tldextract = None


# --------------------------------------------------------------------------- #
# Utilitários públicos (testáveis isoladamente)
# --------------------------------------------------------------------------- #


def dominio_registravel(host: str) -> str:
    """Devolve o domínio que alguém de fato registrou (o "dono" da página).

    ``www.loja.itau.com.br`` -> ``itau.com.br``. Usa a Public Suffix List quando
    ``tldextract`` está instalado; caso contrário, uma tabela embutida de
    sufixos de dois níveis (suficiente para .br e os TLDs mais comuns).
    """
    host = host.strip(".").lower()
    if not host:
        return ""
    if _tldextract is not None:  # pragma: no cover - depende do extra instalado
        ext = _tldextract.extract(host)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}"
        return host
    partes = host.split(".")
    if len(partes) <= 2:
        return host
    if ".".join(partes[-2:]) in SUFIXOS_COMPOSTOS:
        return ".".join(partes[-3:])
    return ".".join(partes[-2:])


def distancia_damerau_levenshtein(a: str, b: str, limite: int = 3) -> int:
    """Distância de edição (com transposição), saturada em ``limite``.

    Mede "quantos caracteres separam" um domínio suspeito do domínio real — a
    base da detecção de typosquatting (``bradosco`` vs ``bradesco``).
    """
    if a == b:
        return 0
    if abs(len(a) - len(b)) > limite:
        return limite + 1
    anterior_anterior: list[int] = []
    anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        atual = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            custo = 0 if ca == cb else 1
            atual[j] = min(
                anterior[j] + 1,          # remoção
                atual[j - 1] + 1,         # inserção
                anterior[j - 1] + custo,  # substituição
            )
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                atual[j] = min(atual[j], anterior_anterior[j - 2] + 1)  # transposição
        if min(atual) > limite:
            return limite + 1
        anterior_anterior, anterior = anterior, atual
    return min(anterior[-1], limite + 1)


def esqueleto_visual(texto: str) -> str:
    """Reduz uma string à sua "forma vista" pelo olho humano.

    Remove acentos, troca homóglifos (cirílico/grego/dígitos) por latinos e
    colapsa dígrafos confusáveis. Um "nubank" com "а" cirílico, ``nub4nk`` e
    ``nubank`` produzem todos o mesmo esqueleto.
    """
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = "".join(CONFUSAVEIS.get(c, c) for c in texto)
    for par, letra in DIGRAFOS_CONFUSAVEIS:
        texto = texto.replace(par, letra)
    return texto.replace("-", "")


def _decodificar_idna(host: str) -> tuple[str, bool]:
    """Converte rótulos punycode (``xn--...``) para Unicode, para exibição."""
    tem_punycode = False
    rotulos: list[str] = []
    for rotulo in host.split("."):
        if rotulo.startswith("xn--"):
            tem_punycode = True
            try:
                rotulos.append(rotulo.encode("ascii").decode("idna"))
            except (UnicodeError, ValueError):
                rotulos.append(rotulo)
        else:
            rotulos.append(rotulo)
    return ".".join(rotulos), tem_punycode


def _e_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def _dominio_legitimo_da_marca(host: str, oficiais: tuple[str, ...]) -> bool:
    return any(host == d or host.endswith("." + d) for d in oficiais)


# --------------------------------------------------------------------------- #
# Contexto
# --------------------------------------------------------------------------- #


@dataclass
class ContextoURL:
    """Decomposição da URL, reaproveitada pelas etapas seguintes."""

    url_original: str
    url_normalizada: str = ""
    valida: bool = False
    erro: str | None = None
    esquema: str | None = None
    usuario: str | None = None
    host: str = ""            # forma Unicode, para exibir
    host_ascii: str = ""      # forma punycode/ASCII, para conectar
    porta: int | None = None
    caminho: str = ""
    query: str = ""
    fragmento: str = ""
    dominio_registravel: str = ""
    subdominios: list[str] = field(default_factory=list)
    e_ip: bool = False


_RE_URL_EMBUTIDA = re.compile(r"https?://", re.IGNORECASE)


def normalizar(url: str) -> ContextoURL:
    """Faz o parse tolerante da URL, sem tocar na rede."""
    bruta = (url or "").strip()
    ctx = ContextoURL(url_original=bruta)
    if not bruta:
        ctx.erro = "URL vazia."
        return ctx

    # Aceita "itau.com.br/login" (sem esquema) tratando-a como relativa a protocolo.
    tem_esquema = ":" in bruta.split("/", 1)[0]
    candidata = bruta if tem_esquema else "//" + bruta
    try:
        p = urlsplit(candidata)
        porta = p.port
    except ValueError as exc:
        ctx.erro = f"URL malformada: {exc}"
        return ctx

    ctx.esquema = p.scheme.lower() or None
    ctx.usuario = p.username
    ctx.porta = porta
    ctx.caminho = p.path
    ctx.query = p.query
    ctx.fragmento = p.fragment

    host_bruto = (p.hostname or "").lower()
    if not host_bruto and ctx.esquema not in ESQUEMAS_PERIGOSOS:
        ctx.erro = "Não foi possível identificar o domínio da URL."
        return ctx

    ctx.host_ascii = host_bruto
    ctx.host, _ = _decodificar_idna(host_bruto)
    ctx.e_ip = _e_ip(host_bruto)
    if host_bruto and not ctx.e_ip:
        ctx.dominio_registravel = dominio_registravel(ctx.host)
        resto = ctx.host[: len(ctx.host) - len(ctx.dominio_registravel)].strip(".")
        ctx.subdominios = [r for r in resto.split(".") if r]
    ctx.url_normalizada = p.geturl()
    ctx.valida = True
    return ctx


# --------------------------------------------------------------------------- #
# Regras
# --------------------------------------------------------------------------- #


def _checar_esquema(ctx: ContextoURL) -> list[Achado]:
    if ctx.esquema in ESQUEMAS_PERIGOSOS:
        return [
            Achado(
                codigo="esquema_perigoso",
                titulo="O link não aponta para um site, e sim para código",
                severidade=Severidade.CRITICA,
                detalhe=(
                    f"O endereço começa com '{ctx.esquema}:', que não abre uma página "
                    "e sim executa conteúdo dentro do seu navegador."
                ),
                recomendacao="Não abra. Links legítimos começam com https://.",
                evidencia={"esquema": ctx.esquema},
            )
        ]
    if ctx.esquema is None:
        return [
            Achado(
                codigo="esquema_ausente",
                titulo="Endereço sem http:// ou https://",
                severidade=Severidade.INFO,
                detalhe="O link foi informado sem protocolo; a análise assumiu HTTPS.",
                recomendacao="Ao digitar endereços, prefira sempre https://.",
            )
        ]
    return []


def _checar_ofuscacao(ctx: ContextoURL) -> list[Achado]:
    """Técnicas que escondem do usuário para onde o link realmente leva."""
    achados: list[Achado] = []
    if ctx.usuario:
        achados.append(
            Achado(
                codigo="userinfo_no_host",
                titulo="O endereço esconde o site real antes do '@'",
                severidade=Severidade.ALTA,
                detalhe=(
                    f"Tudo que aparece antes de '@' é ignorado pelo navegador. O site "
                    f"realmente acessado é '{ctx.host}', não '{ctx.usuario}'."
                ),
                recomendacao="Desconfie: é uma técnica clássica de disfarce de link.",
                evidencia={"antes_do_arroba": ctx.usuario, "host_real": ctx.host},
            )
        )
    if ctx.e_ip:
        achados.append(
            Achado(
                codigo="host_ip_literal",
                titulo="O link aponta para um número de IP, não para um domínio",
                severidade=Severidade.ALTA,
                detalhe=(
                    "Empresas sérias publicam seus serviços em domínios com nome. IP cru "
                    "é comum em servidores descartáveis usados em golpes."
                ),
                recomendacao="Não informe dados pessoais em páginas abertas por IP.",
                evidencia={"ip": ctx.host_ascii},
            )
        )
    if ctx.porta is not None and ctx.porta not in (80, 443):
        achados.append(
            Achado(
                codigo="porta_incomum",
                titulo="O link usa uma porta fora do padrão da web",
                severidade=Severidade.MEDIA,
                detalhe=f"Sites comuns usam 80 ou 443; este usa a porta {ctx.porta}.",
                recomendacao="Confirme a origem do link antes de abrir.",
                evidencia={"porta": ctx.porta},
            )
        )
    if ctx.dominio_registravel in ENCURTADORES:
        achados.append(
            Achado(
                codigo="encurtador",
                titulo="Link encurtado: o destino real está oculto",
                severidade=Severidade.MEDIA,
                detalhe=(
                    f"'{ctx.dominio_registravel}' é um encurtador. Não é malicioso por si "
                    "só, mas impede que você veja para onde está indo."
                ),
                recomendacao="Peça o link completo a quem enviou antes de clicar.",
                evidencia={"encurtador": ctx.dominio_registravel},
            )
        )
    alvo = unquote(f"{ctx.caminho}?{ctx.query}")
    if _RE_URL_EMBUTIDA.search(alvo):
        achados.append(
            Achado(
                codigo="url_embutida",
                titulo="Há um segundo endereço escondido dentro do link",
                severidade=Severidade.MEDIA,
                detalhe=(
                    "O link carrega outra URL nos parâmetros — padrão de redirecionamento "
                    "usado para tomar emprestada a credibilidade de um domínio conhecido."
                ),
                recomendacao="Verifique para qual endereço você será realmente levado.",
                evidencia={"trecho": alvo[:200]},
            )
        )
    return achados


def _checar_estrutura_do_dominio(ctx: ContextoURL) -> list[Achado]:
    achados: list[Achado] = []
    if ctx.e_ip or not ctx.host:
        return achados

    n = len(ctx.subdominios)
    if n >= 3:
        achados.append(
            Achado(
                codigo="subdominios_excessivos",
                titulo="Domínio com muitos níveis antes do nome principal",
                severidade=Severidade.ALTA if n >= 5 else Severidade.MEDIA,
                detalhe=(
                    f"O endereço tem {n} subdomínios. Golpes empilham subdomínios para "
                    f"empurrar o domínio real ('{ctx.dominio_registravel}') para fora da "
                    "tela do celular."
                ),
                recomendacao="Leia sempre da direita para a esquerda, até a primeira '/'.",
                evidencia={"subdominios": ctx.subdominios},
            )
        )

    sufixo = ctx.dominio_registravel.rsplit(".", 1)[-1] if ctx.dominio_registravel else ""
    if sufixo in TLDS_DE_RISCO:
        achados.append(
            Achado(
                codigo="tld_de_risco",
                titulo=f"Extensão de domínio '.{sufixo}' com histórico de abuso",
                severidade=Severidade.MEDIA,
                detalhe="Registro gratuito ou muito barato, recorrente em campanhas de phishing.",
                recomendacao="Sinal fraco isolado — some-o aos demais antes de concluir.",
                evidencia={"tld": sufixo},
            )
        )

    sld = ctx.dominio_registravel.split(".", 1)[0] if ctx.dominio_registravel else ""
    if sld.count("-") >= 3:
        achados.append(
            Achado(
                codigo="hifens_em_excesso",
                titulo="Nome de domínio com muitos hífens",
                severidade=Severidade.BAIXA,
                detalhe=f"'{sld}' concatena palavras com hífen, padrão de domínio descartável.",
                recomendacao="Compare com o endereço oficial da empresa.",
                evidencia={"dominio": ctx.dominio_registravel},
            )
        )

    if len(ctx.url_original) > 120:
        achados.append(
            Achado(
                codigo="url_muito_longa",
                titulo="Endereço muito longo",
                severidade=Severidade.BAIXA,
                detalhe=f"{len(ctx.url_original)} caracteres — dificulta a leitura do domínio real.",
                recomendacao="Confira o trecho até a primeira barra.",
                evidencia={"tamanho": len(ctx.url_original)},
            )
        )
    return achados


def _checar_unicode(ctx: ContextoURL) -> list[Achado]:
    achados: list[Achado] = []
    if not ctx.host_ascii or ctx.e_ip:
        return achados
    _, tem_punycode = _decodificar_idna(ctx.host_ascii)
    letras = [c for c in ctx.host if c.isalpha()]
    tem_nao_ascii = any(ord(c) > 127 for c in letras)
    tem_ascii = any(ord(c) < 128 for c in letras)
    if tem_nao_ascii and tem_ascii:
        achados.append(
            Achado(
                codigo="alfabetos_misturados",
                titulo="O domínio mistura alfabetos diferentes",
                severidade=Severidade.ALTA,
                detalhe=(
                    "Há letras não latinas no meio de letras latinas. É assim que se cria "
                    "um endereço visualmente idêntico ao de uma marca real."
                ),
                recomendacao="Digite o endereço da empresa manualmente, não use o link.",
                evidencia={"host_unicode": ctx.host, "host_ascii": ctx.host_ascii},
            )
        )
    elif tem_punycode:
        achados.append(
            Achado(
                codigo="dominio_punycode",
                titulo="Domínio com caracteres internacionais (punycode)",
                severidade=Severidade.MEDIA,
                detalhe=f"'{ctx.host_ascii}' é exibido como '{ctx.host}'.",
                recomendacao="Legítimo em muitos casos; confira se é mesmo o site esperado.",
                evidencia={"host_unicode": ctx.host, "host_ascii": ctx.host_ascii},
            )
        )
    return achados


def _checar_marcas(ctx: ContextoURL) -> list[Achado]:
    """Typosquatting, homóglifos e impersonação por subdomínio."""
    achados: list[Achado] = []
    if ctx.e_ip or not ctx.dominio_registravel:
        return achados

    registravel = ctx.dominio_registravel
    esqueleto_reg = esqueleto_visual(registravel)

    # 0) É o domínio real de alguma marca conhecida? Então não há o que apontar.
    for oficiais in MARCAS_OFICIAIS.values():
        if _dominio_legitimo_da_marca(ctx.host, oficiais):
            return []

    for marca, oficiais in MARCAS_OFICIAIS.items():
        for oficial in oficiais:
            if len(oficial) < 7:
                continue
            # (a) visualmente idêntico, mas escrito com outros caracteres
            if registravel != oficial and esqueleto_reg == esqueleto_visual(oficial):
                achados.append(
                    Achado(
                        codigo="dominio_sosia",
                        titulo=f"Domínio visualmente idêntico ao de '{marca}'",
                        severidade=Severidade.CRITICA,
                        detalhe=(
                            f"'{registravel}' é escrito de forma diferente de '{oficial}', "
                            "mas na tela parece o mesmo endereço."
                        ),
                        recomendacao=f"O endereço oficial é '{oficial}'. Não use este link.",
                        evidencia={"suspeito": registravel, "oficial": oficial},
                    )
                )
                return achados
            # (b) a um ou dois caracteres do domínio real
            d = distancia_damerau_levenshtein(registravel, oficial, limite=2)
            if 0 < d <= 2:
                achados.append(
                    Achado(
                        codigo="typosquatting",
                        titulo=f"Domínio quase igual ao de '{marca}'",
                        severidade=Severidade.CRITICA if d == 1 else Severidade.ALTA,
                        detalhe=(
                            f"'{registravel}' difere de '{oficial}' em apenas {d} "
                            "caractere(s) — erro de digitação explorado por golpistas."
                        ),
                        recomendacao=f"O endereço oficial é '{oficial}'.",
                        evidencia={"suspeito": registravel, "oficial": oficial, "distancia": d},
                    )
                )
                return achados

    # (c) marca citada no subdomínio ou no caminho, mas o domínio é de terceiro
    contexto_texto = esqueleto_visual(".".join(ctx.subdominios) + " " + ctx.caminho)
    for marca, oficiais in MARCAS_OFICIAIS.items():
        if marca in contexto_texto:
            achados.append(
                Achado(
                    codigo="marca_em_subdominio",
                    titulo=f"Usa o nome '{marca}' num domínio que não é da empresa",
                    severidade=Severidade.ALTA,
                    detalhe=(
                        f"O nome aparece no endereço, mas quem controla a página é "
                        f"'{registravel}'. Só o que vem antes da primeira barra importa."
                    ),
                    recomendacao=f"Endereço(s) oficial(is): {', '.join(oficiais)}.",
                    evidencia={"marca": marca, "dominio_real": registravel},
                )
            )
            break
    return achados


def _checar_iscas(ctx: ContextoURL) -> list[Achado]:
    achados: list[Achado] = []
    alvo = unquote(f"{ctx.host} {ctx.caminho} {ctx.query}").lower()
    encontradas = sorted({p for p in ISCAS if p in alvo})
    if len(encontradas) >= 2:
        achados.append(
            Achado(
                codigo="palavras_isca",
                titulo="O endereço usa palavras típicas de golpe",
                severidade=Severidade.MEDIA if len(encontradas) >= 3 else Severidade.BAIXA,
                detalhe=(
                    "Termos como "
                    + ", ".join(f"'{p}'" for p in encontradas[:5])
                    + " são usados para criar urgência e pedir dados."
                ),
                recomendacao="Bancos e órgãos públicos não pedem senha ou CPF por link.",
                evidencia={"termos": encontradas},
            )
        )
    caminho = ctx.caminho.lower()
    for ext in EXTENSOES_EXECUTAVEIS:
        if caminho.endswith(ext):
            achados.append(
                Achado(
                    codigo="download_executavel",
                    titulo=f"O link baixa um arquivo executável ({ext})",
                    severidade=Severidade.ALTA,
                    detalhe="Abrir esse arquivo instala um programa no seu aparelho.",
                    recomendacao="Não execute arquivos recebidos por link não solicitado.",
                    evidencia={"extensao": ext},
                )
            )
            break
    return achados


# --------------------------------------------------------------------------- #
# Checklist heurística — item 7/8 da tela de resultado
#
# Reaproveita o mesmo contexto e os mesmos achados da etapa 1: nenhuma regra
# nova é criada aqui, isto é só uma VISÃO em formato de checklist (passou /
# falhou / motivo) sobre o que a etapa 1 já apurou — inclusive os critérios
# que passaram, que `Achado` não representa (achado só existe para o que deu
# errado). É por isso que a nota de risco continua sendo a de `pontuacao.py`:
# esta checklist é só uma explicação didática, não um segundo placar.
# --------------------------------------------------------------------------- #


def checklist_heuristico(ctx: ContextoURL, achados: list[Achado]) -> list[CriterioChecklist]:
    """Monta a tabela de critérios (passou/falhou + motivo) do laudo.

    Só roda para URLs válidas com host (a mesma condição que libera as etapas
    de rede em ``analisador.py``) — para URL inválida ou esquema perigoso não
    há o que preencher na tabela.
    """
    if not ctx.valida or not ctx.host_ascii:
        return []

    codigos = {a.codigo for a in achados}
    linhas: list[CriterioChecklist] = []

    # 1) IP no lugar do domínio
    linhas.append(
        CriterioChecklist(
            codigo="ip_no_lugar_do_dominio",
            rotulo="Domínio, não IP",
            passou=not ctx.e_ip,
            motivo=(
                f"O endereço aponta direto para o IP '{ctx.host_ascii}', sem nome de domínio."
                if ctx.e_ip
                else "O endereço usa um domínio com nome, não um IP cru."
            ),
        )
    )

    # 2) "@" na URL (esconde o destino real antes do arroba)
    linhas.append(
        CriterioChecklist(
            codigo="arroba_na_url",
            rotulo="Sem '@' escondendo o destino",
            passou=not ctx.usuario,
            motivo=(
                f"Tudo antes de '@' é ignorado pelo navegador — o destino real é '{ctx.host}'."
                if ctx.usuario
                else "Não há '@' antes do domínio."
            ),
        )
    )

    # 3) Excesso de subdomínios
    n_sub = len(ctx.subdominios)
    linhas.append(
        CriterioChecklist(
            codigo="excesso_de_subdominios",
            rotulo="Poucos níveis de subdomínio",
            passou=n_sub < 3,
            motivo=(
                f"{n_sub} subdomínios empilhados antes do domínio real."
                if n_sub >= 3
                else f"{n_sub} subdomínio(s) — dentro do esperado."
            ),
        )
    )

    # 4) Excesso de hífens no domínio
    sld = ctx.dominio_registravel.split(".", 1)[0] if ctx.dominio_registravel else ""
    hifens = sld.count("-")
    linhas.append(
        CriterioChecklist(
            codigo="excesso_de_hifens",
            rotulo="Poucos hífens no domínio",
            passou=hifens < 3,
            motivo=(
                f"'{sld}' concatena palavras com {hifens} hífens — padrão de domínio descartável."
                if hifens >= 3
                else "Nome de domínio sem excesso de hífens."
            ),
        )
    )

    # 5) URL muito longa
    tamanho = len(ctx.url_original)
    linhas.append(
        CriterioChecklist(
            codigo="url_muito_longa",
            rotulo="Tamanho da URL",
            passou=tamanho <= 120,
            motivo=(
                f"{tamanho} caracteres — URLs muito longas dificultam ver o domínio real."
                if tamanho > 120
                else f"{tamanho} caracteres — tamanho normal."
            ),
        )
    )

    # 6) Ausência de HTTPS
    tem_https = ctx.esquema == "https"
    linhas.append(
        CriterioChecklist(
            codigo="ausencia_de_https",
            rotulo="Usa HTTPS",
            passou=tem_https,
            motivo=(
                "A conexão é criptografada (https://)."
                if tem_https
                else "O endereço não declara https:// — dado pode trafegar sem criptografia."
            ),
        )
    )

    # 7) TLD suspeito
    sufixo = ctx.dominio_registravel.rsplit(".", 1)[-1] if ctx.dominio_registravel else ""
    tld_suspeito = sufixo in TLDS_DE_RISCO
    linhas.append(
        CriterioChecklist(
            codigo="tld_suspeito",
            rotulo="Extensão de domínio comum",
            passou=not tld_suspeito,
            motivo=(
                f"'.{sufixo}' tem histórico desproporcional de abuso em phishing."
                if tld_suspeito
                else f"'.{sufixo}' não está na lista de extensões de risco."
            ),
        )
    )

    # 8) Palavras de phishing no endereço (qualquer ocorrência, mais sensível
    #    que o achado `palavras_isca`, que só dispara a partir de 2 termos).
    alvo_iscas = unquote(f"{ctx.host} {ctx.caminho} {ctx.query}").lower()
    termos = sorted({p for p in ISCAS if p in alvo_iscas})
    linhas.append(
        CriterioChecklist(
            codigo="palavras_de_phishing",
            rotulo="Sem palavras típicas de golpe",
            passou=not termos,
            motivo=(
                "Usa " + ", ".join(f"'{t}'" for t in termos[:5]) + " — termos comuns em phishing."
                if termos
                else "Nenhuma palavra-isca encontrada no endereço."
            ),
        )
    )

    # 9) Imitação de marca conhecida (typosquatting, sósia visual ou marca no subdomínio)
    imita_marca = bool(codigos & {"dominio_sosia", "typosquatting", "marca_em_subdominio"})
    linhas.append(
        CriterioChecklist(
            codigo="imitacao_de_marca",
            rotulo="Sem imitação de marca conhecida",
            passou=not imita_marca,
            motivo=(
                "O domínio imita ou cita uma marca conhecida que não é a dona da página."
                if imita_marca
                else "Nenhuma semelhança com marcas conhecidas foi encontrada."
            ),
        )
    )

    # 10) Punycode (xn--)
    tem_punycode = "xn--" in ctx.host_ascii
    linhas.append(
        CriterioChecklist(
            codigo="punycode",
            rotulo="Sem punycode",
            passou=not tem_punycode,
            motivo=(
                f"'{ctx.host_ascii}' usa codificação punycode, exibida como '{ctx.host}'."
                if tem_punycode
                else "O domínio não usa codificação punycode (xn--)."
            ),
        )
    )

    # 11) Encurtador de link
    encurtado = ctx.dominio_registravel in ENCURTADORES
    linhas.append(
        CriterioChecklist(
            codigo="encurtador_de_link",
            rotulo="Não é um encurtador",
            passou=not encurtado,
            motivo=(
                f"'{ctx.dominio_registravel}' é um encurtador — o destino real fica oculto."
                if encurtado
                else "O domínio não é um encurtador conhecido."
            ),
        )
    )

    return linhas


def analisar_sintaxe(url: str) -> tuple[ContextoURL, list[Achado]]:
    """Roda todas as regras offline sobre a URL.

    Retorna o contexto (reaproveitado pelas etapas de TLS e reputação) e a lista
    de achados. Não realiza nenhuma conexão.
    """
    ctx = normalizar(url)
    if not ctx.valida:
        return ctx, [
            Achado(
                codigo="url_invalida",
                titulo="Endereço inválido",
                severidade=Severidade.CRITICA,
                detalhe=ctx.erro or "Não foi possível interpretar a URL.",
                recomendacao="Confira se o link foi copiado por inteiro.",
                evidencia={"url": ctx.url_original[:200]},
            )
        ]

    achados: list[Achado] = []
    achados += _checar_esquema(ctx)
    if ctx.esquema in ESQUEMAS_PERIGOSOS:
        return ctx, achados  # não há host para analisar
    achados += _checar_ofuscacao(ctx)
    achados += _checar_estrutura_do_dominio(ctx)
    achados += _checar_unicode(ctx)
    achados += _checar_marcas(ctx)
    achados += _checar_iscas(ctx)
    return ctx, achados
