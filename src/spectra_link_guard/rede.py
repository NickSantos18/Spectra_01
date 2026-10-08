"""Etapa 4 — Registro do domínio e origem do servidor (consultas públicas).

ESCOPO: duas consultas a registros públicos, nenhuma delas ao site analisado.

  * **RDAP** (RFC 7483) — o sucessor padronizado do WHOIS. Devolve a data de
    registro do domínio e o registrador. É um banco público mantido pelos
    registries (Registro.br, Verisign, RIPE...), consultado pela porta 443 do
    *registry*, não do alvo.
  * **DNS** — resolve o nome para IP, exatamente como qualquer navegador faz
    antes de abrir qualquer link. Com o IP em mãos, um segundo RDAP diz a que
    rede e a que país aquele bloco pertence.

Nada aqui toca o servidor do site analisado: não há requisição HTTP ao alvo,
não há conteúdo baixado. A idade do domínio é um dos sinais mais fortes que
existem para phishing — campanhas de golpe usam domínios registrados dias antes.
"""

from __future__ import annotations

import asyncio
import socket
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from .models import Achado, Severidade

#: rdap.org é um "bootstrap": redireciona para o RDAP do registry correto.
#: Os redirecionamentos seguidos aqui são do próprio serviço de RDAP — nunca
#: do site analisado.
_RDAP_DOMINIO = "https://rdap.org/domain/{alvo}"
_RDAP_IP = "https://rdap.org/ip/{alvo}"

#: DNS sobre HTTPS. Consulta um resolvedor público — não o servidor do alvo.
#: Cloudflare em vez do Google porque o dns.google costuma ficar bloqueado em
#: rede corporativa e escolar.
_DOH = "https://cloudflare-dns.com/dns-query"

#: Códigos de status do RDAP que significam domínio fora de operação.
_STATUS_TRAVADO = {"client hold", "server hold", "pending delete", "inactive"}

#: Abaixo disso, o domínio é jovem demais para ter reputação.
_DIAS_MUITO_NOVO = 30
_DIAS_NOVO = 90
#: Acima disso, o domínio já sobreviveu tempo suficiente para ser conhecido.
_DIAS_ESTABELECIDO = 730


@dataclass
class RegistroDominio:
    """Dados públicos de registro do domínio (RDAP)."""

    consultado: bool = False
    criado_em: str | None = None
    idade_dias: int | None = None
    registrador: str | None = None
    expira_em: str | None = None
    dias_para_expirar: int | None = None
    status: list[str] = field(default_factory=list)
    dnssec: bool | None = None
    nameservers: list[str] = field(default_factory=list)
    erro: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DNS:
    """Registros públicos do DNS, além do A/AAAA que a resolução já traz.

    São os que dizem como o domínio se comporta fora da web: quem recebe
    e-mail por ele, se ele se protege contra falsificação de remetente e quem
    pode emitir certificado em nome dele.
    """

    consultado: bool = False
    mx: list[str] = field(default_factory=list)
    ns: list[str] = field(default_factory=list)
    spf: str | None = None
    dmarc: str | None = None
    caa: list[str] = field(default_factory=list)
    erro: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Hospedagem:
    """Onde o nome aponta: IPs, DNS reverso, rede e país do bloco."""

    consultado: bool = False
    ips: list[str] = field(default_factory=list)
    reverso: str | None = None
    pais: str | None = None
    rede: str | None = None
    erro: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# RDAP do domínio
# --------------------------------------------------------------------------- #


def _data_de_evento(eventos: list[dict], acao: str) -> datetime | None:
    for evento in eventos or ():
        if evento.get("eventAction") == acao:
            bruta = (evento.get("eventDate") or "").replace("Z", "+00:00")
            try:
                data = datetime.fromisoformat(bruta)
            except ValueError:
                continue
            return data if data.tzinfo else data.replace(tzinfo=timezone.utc)
    return None


def _nome_do_registrador(entidades: list[dict]) -> str | None:
    for entidade in entidades or ():
        if "registrar" not in (entidade.get("roles") or ()):
            continue
        # vCard: ["vcard", [["fn", {}, "text", "NOME DO REGISTRADOR"], ...]]
        for campo in (entidade.get("vcardArray") or [None, []])[1]:
            if campo and campo[0] == "fn":
                return str(campo[3])
        return entidade.get("handle")
    return None


async def consultar_registro(
    cliente: httpx.AsyncClient, dominio: str
) -> RegistroDominio:
    """Lê a data de criação do domínio no RDAP público do registry."""
    info = RegistroDominio()
    if not dominio:
        info.erro = "Sem domínio para consultar."
        return info
    try:
        resp = await cliente.get(_RDAP_DOMINIO.format(alvo=dominio))
        if resp.status_code == 404:
            info.erro = "Domínio não consta no RDAP do registry."
            return info
        resp.raise_for_status()
        dados = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        info.erro = f"Consulta RDAP indisponível: {exc}"
        return info

    eventos = dados.get("events") or []
    agora_utc = datetime.now(timezone.utc)

    info.consultado = True
    info.registrador = _nome_do_registrador(dados.get("entities") or [])
    # Normalizado em minúsculas: cada registry escreve "clientHold",
    # "client hold" ou "CLIENT HOLD" do seu jeito.
    info.status = [str(e).strip().lower() for e in (dados.get("status") or [])]
    info.dnssec = bool((dados.get("secureDNS") or {}).get("delegationSigned"))
    info.nameservers = [
        n.get("ldhName", "").lower() for n in (dados.get("nameservers") or []) if n.get("ldhName")
    ]

    criado = _data_de_evento(eventos, "registration")
    if criado:
        info.criado_em = criado.isoformat()
        info.idade_dias = (agora_utc - criado).days
    else:
        info.erro = "O registry não publica a data de registro deste domínio."

    expira = _data_de_evento(eventos, "expiration")
    if expira:
        info.expira_em = expira.isoformat()
        info.dias_para_expirar = (expira - agora_utc).days
    return info


# --------------------------------------------------------------------------- #
# DNS sobre HTTPS
# --------------------------------------------------------------------------- #


async def _perguntar(cliente: httpx.AsyncClient, nome: str, tipo: str) -> list[str]:
    """Uma consulta DoH. Devolve os dados das respostas, ou lista vazia."""
    resp = await cliente.get(
        _DOH,
        params={"name": nome, "type": tipo},
        headers={"accept": "application/dns-json"},
    )
    resp.raise_for_status()
    return [r.get("data", "") for r in (resp.json().get("Answer") or [])]


def _sem_aspas(txt: str) -> str:
    """O DoH devolve TXT entre aspas, e longos vêm em pedaços concatenados."""
    return txt.replace('""', "").strip('"')


async def consultar_dns(cliente: httpx.AsyncClient, dominio: str) -> DNS:
    """Lê MX, NS, SPF, DMARC e CAA num resolvedor público.

    Nenhuma destas consultas fala com o servidor do site — todas vão ao
    resolvedor, que é o mesmo caminho que qualquer navegador percorre.
    """
    info = DNS()
    if not dominio:
        info.erro = "Sem domínio para consultar."
        return info

    try:
        mx, ns, txt, caa, dmarc = await asyncio.gather(
            _perguntar(cliente, dominio, "MX"),
            _perguntar(cliente, dominio, "NS"),
            _perguntar(cliente, dominio, "TXT"),
            _perguntar(cliente, dominio, "CAA"),
            _perguntar(cliente, f"_dmarc.{dominio}", "TXT"),
        )
    except (httpx.HTTPError, ValueError) as exc:
        info.erro = f"Consulta DNS indisponível: {exc}"
        return info

    info.consultado = True
    # MX vem como "10 mx.provedor.com." — guardamos só o host.
    info.mx = [linha.split(" ")[-1].rstrip(".") for linha in mx if linha]
    info.ns = [linha.rstrip(".").lower() for linha in ns if linha]
    info.caa = [linha for linha in caa if linha]

    for linha in txt:
        limpo = _sem_aspas(linha)
        if limpo.lower().startswith("v=spf1"):
            info.spf = limpo
            break
    for linha in dmarc:
        limpo = _sem_aspas(linha)
        if limpo.lower().startswith("v=dmarc1"):
            info.dmarc = limpo
            break
    return info


# --------------------------------------------------------------------------- #
# DNS + RDAP do IP
# --------------------------------------------------------------------------- #


def _resolver(host: str) -> tuple[list[str], str | None]:
    """Resolução DNS bloqueante — roda em thread."""
    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    ips = list(dict.fromkeys(info[4][0] for info in infos))
    reverso = None
    if ips:
        try:
            reverso = socket.gethostbyaddr(ips[0])[0]
        except (OSError, socket.herror):
            reverso = None
    return ips, reverso


async def consultar_hospedagem(
    cliente: httpx.AsyncClient, host: str
) -> Hospedagem:
    """Resolve o host e descreve a rede pública dona do IP."""
    info = Hospedagem()
    if not host:
        info.erro = "Sem host para resolver."
        return info
    try:
        info.ips, info.reverso = await asyncio.to_thread(_resolver, host)
    except (OSError, socket.gaierror) as exc:
        info.erro = f"O nome não resolve em DNS: {exc}"
        return info

    info.consultado = True
    if not info.ips:
        info.erro = "Nenhum endereço IP retornado."
        return info

    try:
        resp = await cliente.get(_RDAP_IP.format(alvo=info.ips[0]))
        resp.raise_for_status()
        dados = resp.json()
        info.pais = dados.get("country")
        info.rede = dados.get("name")
    except (httpx.HTTPError, ValueError):
        # O IP resolveu; só não sabemos de quem é a rede. Não é erro fatal.
        pass
    return info


# --------------------------------------------------------------------------- #
# Achados
# --------------------------------------------------------------------------- #


def achados_de_registro(info: RegistroDominio) -> list[Achado]:
    """A idade do domínio é o sinal isolado mais forte contra phishing."""
    if not info.consultado or info.idade_dias is None:
        return []

    dias = info.idade_dias
    if dias <= _DIAS_MUITO_NOVO:
        return [
            Achado(
                codigo="dominio_recem_registrado",
                titulo=f"Domínio registrado há {dias} dia(s)",
                severidade=Severidade.ALTA,
                detalhe=(
                    "Campanhas de golpe registram o domínio poucos dias antes do "
                    "disparo das mensagens, justamente para não dar tempo de serem "
                    "denunciadas."
                ),
                recomendacao="Empresa de verdade não atende clientes num domínio recém-criado.",
                evidencia={"idade_dias": dias, "criado_em": info.criado_em},
            )
        ]
    if dias <= _DIAS_NOVO:
        return [
            Achado(
                codigo="dominio_novo",
                titulo=f"Domínio criado há {dias} dias",
                severidade=Severidade.MEDIA,
                detalhe="Ainda não teve tempo de acumular reputação nas listas públicas.",
                recomendacao="Confirme o endereço por um canal oficial da empresa.",
                evidencia={"idade_dias": dias, "criado_em": info.criado_em},
            )
        ]
    if dias >= _DIAS_ESTABELECIDO:
        return [
            Achado(
                codigo="dominio_estabelecido",
                titulo=f"Domínio ativo há {dias // 365} ano(s)",
                severidade=Severidade.INFO,
                detalhe="Domínios de golpe raramente sobrevivem tanto tempo.",
                recomendacao="Sinal favorável — mas confira os demais itens do laudo.",
                evidencia={"idade_dias": dias, "criado_em": info.criado_em},
            )
        ]
    return []


def achados_de_dns(dns: DNS, registro: RegistroDominio) -> list[Achado]:
    """Traduz DNS e status do registro em sinais.

    CALIBRAÇÃO — a decisão mais importante deste módulo: falta de SPF, DMARC ou
    CAA é problema do DONO do domínio, **não** indício de que o link seja
    perigoso para quem o recebeu. A maioria esmagadora dos sites pequenos e
    legítimos do Brasil não tem nenhum dos três. Se entrassem como MEDIA,
    todo site honesto ganharia +16 de risco e a ferramenta viraria alarme
    falso. Por isso entram como INFO (peso zero na nota) e aparecem com
    destaque no plano de melhorias, que é onde eles de fato importam.

    O que realmente muda o risco é o domínio estar suspenso ou vencido.
    """
    achados: list[Achado] = []

    travas = [e for e in registro.status if e in _STATUS_TRAVADO]
    if travas:
        achados.append(
            Achado(
                codigo="dominio_suspenso",
                titulo="O domínio está suspenso no registro",
                severidade=Severidade.ALTA,
                detalhe=(
                    f"O registry marcou este domínio como {', '.join(travas)}. "
                    "Isso costuma acontecer depois de denúncia de abuso ou falta de pagamento."
                ),
                recomendacao="Domínio suspenso não deveria estar recebendo visita. Não informe dados.",
                evidencia={"status": registro.status},
            )
        )

    if registro.dias_para_expirar is not None and registro.dias_para_expirar < 0:
        achados.append(
            Achado(
                codigo="dominio_expirado",
                titulo="O registro do domínio venceu",
                severidade=Severidade.MEDIA,
                detalhe=(
                    f"Venceu há {abs(registro.dias_para_expirar)} dia(s). Domínio vencido pode "
                    "ser registrado por outra pessoa e usado para se passar pelo dono anterior."
                ),
                recomendacao="Confirme por outro canal antes de confiar neste endereço.",
                evidencia={"expira_em": registro.expira_em},
            )
        )

    if not dns.consultado:
        return achados

    if dns.mx and not dns.spf:
        achados.append(
            Achado(
                codigo="sem_spf",
                titulo="O domínio envia e-mail sem SPF",
                severidade=Severidade.INFO,
                detalhe=(
                    "Sem SPF, qualquer servidor pode mandar e-mail se passando por este "
                    "domínio — é o que facilita golpe usando o nome da empresa."
                ),
                recomendacao="Publique um registro TXT com v=spf1 listando quem pode enviar.",
                evidencia={"mx": dns.mx[:3]},
            )
        )

    if not dns.dmarc:
        achados.append(
            Achado(
                codigo="sem_dmarc",
                titulo="O domínio não publica DMARC",
                severidade=Severidade.INFO,
                detalhe=(
                    "O DMARC diz aos provedores o que fazer com e-mail falsificado em nome "
                    "deste domínio. Sem ele, a falsificação passa sem ser barrada."
                ),
                recomendacao="Publique _dmarc com v=DMARC1; comece em p=none e evolua para p=reject.",
                evidencia={"dmarc": None},
            )
        )
    elif "p=none" in dns.dmarc.lower():
        achados.append(
            Achado(
                codigo="dmarc_permissivo",
                titulo="O DMARC existe mas não bloqueia nada",
                severidade=Severidade.INFO,
                detalhe="Está em p=none, que só observa. E-mail falsificado continua sendo entregue.",
                recomendacao="Depois de acompanhar os relatórios, suba para p=quarantine e então p=reject.",
                evidencia={"dmarc": dns.dmarc[:120]},
            )
        )

    if not dns.caa:
        achados.append(
            Achado(
                codigo="sem_caa",
                titulo="Qualquer autoridade pode emitir certificado para este domínio",
                severidade=Severidade.INFO,
                detalhe=(
                    "Sem registro CAA, nada impede que uma CA qualquer emita um certificado "
                    "válido em nome deste domínio."
                ),
                recomendacao="Publique CAA autorizando só as autoridades que você usa.",
                evidencia={"caa": []},
            )
        )

    return achados


async def consultar_rede(
    dominio_registravel: str,
    host: str,
    *,
    timeout: float = 8.0,
) -> tuple[RegistroDominio, Hospedagem, DNS]:
    """Roda as três consultas públicas em paralelo."""
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,  # rdap.org redireciona para o registry correto
        headers={"Accept": "application/rdap+json"},
    ) as cliente:
        return await asyncio.gather(  # type: ignore[return-value]
            consultar_registro(cliente, dominio_registravel),
            consultar_hospedagem(cliente, host),
            consultar_dns(cliente, dominio_registravel),
        )
