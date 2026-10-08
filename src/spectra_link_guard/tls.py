"""Etapa 2 — Checagem de protocolo e do certificado TLS.

ESCOPO: esta etapa faz **um único handshake TLS** com o host, na porta que a
própria URL indica, e lê os dados que o servidor apresenta publicamente — os
mesmos que o cadeado do navegador mostra a qualquer visitante.

O que ela **não** faz, por decisão de projeto:
  * não envia requisição HTTP, não baixa conteúdo, não segue redirecionamentos;
  * não varre portas (só a porta do link, 443 por padrão);
  * não testa cifras fracas, renegociação, Heartbleed nem qualquer outra
    condição que exija sondagem repetida do servidor;
  * não envia credenciais nem dados do usuário.

É o mesmo tráfego que abrir o link no navegador geraria — na verdade, menos.
Ainda assim, o handshake pode ser desativado por completo
(``ConfiguracaoLinkGuard(verificar_tls=False)``) para uma análise 100% offline.
"""

from __future__ import annotations

import asyncio
import socket
import ssl
from datetime import datetime, timezone

from .models import Achado, CertificadoTLS, Severidade
from .sintaxe import ContextoURL

try:  # opcional: permite ler o certificado mesmo quando a cadeia não valida
    from cryptography import x509
except ImportError:  # pragma: no cover - caminho de fallback
    x509 = None


_FORMATO_DATA_OPENSSL = "%b %d %H:%M:%S %Y %Z"

#: Versões de TLS consideradas obsoletas pela IETF (RFC 8996).
_TLS_OBSOLETO = {"SSLv2", "SSLv3", "TLSv1", "TLSv1.1"}


def _texto_do_nome(pares) -> str:
    """Achata a estrutura de nome do ``ssl`` (tuplas aninhadas) em texto."""
    partes: list[str] = []
    for rdn in pares or ():
        for chave, valor in rdn:
            if chave in ("commonName", "organizationName"):
                partes.append(valor)
    return ", ".join(dict.fromkeys(partes)) or None  # type: ignore[return-value]


def _data_openssl(valor: str | None) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.strptime(valor, _FORMATO_DATA_OPENSSL).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _handshake(host: str, porta: int, timeout: float, verificar: bool) -> tuple[dict | None, bytes | None, str | None, str | None]:
    """Executa o handshake e devolve (cert_dict, cert_der, versao_tls, cifra).

    Bloqueante de propósito — é chamado dentro de ``asyncio.to_thread``.
    """
    contexto = ssl.create_default_context()
    if not verificar:
        contexto.check_hostname = False
        contexto.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, porta), timeout=timeout) as bruto:
        with contexto.wrap_socket(bruto, server_hostname=host) as tls:
            cert_dict = tls.getpeercert() or None
            cert_der = tls.getpeercert(binary_form=True)
            cifra = tls.cipher()
            return cert_dict, cert_der, tls.version(), (cifra[0] if cifra else None)


def _preencher_com_cryptography(info: CertificadoTLS, der: bytes | None) -> None:
    """Extrai os campos do certificado quando o ``ssl`` não devolve o dict.

    Acontece quando a cadeia não valida: o Python só entrega o dict decodificado
    em conexões verificadas, então relemos o DER (dado público já recebido).
    """
    if not der or x509 is None:
        return
    try:
        cert = x509.load_der_x509_certificate(der)
    except Exception:  # pragma: no cover - certificado ilegível
        return
    info.emitido_para = cert.subject.rfc4514_string()
    info.emissor = cert.issuer.rfc4514_string()
    inicio = cert.not_valid_before_utc
    fim = cert.not_valid_after_utc
    info.valido_de = inicio.isoformat()
    info.valido_ate = fim.isoformat()
    info.dias_para_expirar = (fim - datetime.now(timezone.utc)).days
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        info.nomes_alternativos = san.value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        info.nomes_alternativos = []


async def inspecionar_tls(ctx: ContextoURL, timeout: float = 6.0) -> CertificadoTLS:
    """Lê os dados públicos do certificado apresentado pelo host da URL."""
    info = CertificadoTLS()
    if not ctx.host_ascii or ctx.esquema == "http":
        info.erro = "Conexão não criptografada — não há certificado a inspecionar."
        return info

    porta = ctx.porta or 443
    host = ctx.host_ascii

    try:
        cert_dict, der, versao, cifra = await asyncio.to_thread(
            _handshake, host, porta, timeout, True
        )
        info.cadeia_valida = True
    except ssl.SSLCertVerificationError as exc:
        # Cadeia inválida: refazemos sem verificação apenas para *ler* o
        # certificado que o servidor já nos entregou e explicar o problema.
        info.cadeia_valida = False
        info.erro = str(exc.verify_message or exc)
        try:
            cert_dict, der, versao, cifra = await asyncio.to_thread(
                _handshake, host, porta, timeout, False
            )
        except (OSError, ssl.SSLError) as exc2:
            info.erro = f"{info.erro} / {exc2}"
            return info
    except (socket.gaierror, socket.timeout, TimeoutError) as exc:
        info.erro = f"Host inacessível ou inexistente: {exc}"
        return info
    except (OSError, ssl.SSLError) as exc:
        info.erro = f"Falha no handshake TLS: {exc}"
        return info

    info.disponivel = True
    info.versao_tls = versao
    info.cifra = cifra

    if cert_dict:
        info.emitido_para = _texto_do_nome(cert_dict.get("subject"))
        info.emissor = _texto_do_nome(cert_dict.get("issuer"))
        inicio = _data_openssl(cert_dict.get("notBefore"))
        fim = _data_openssl(cert_dict.get("notAfter"))
        info.valido_de = inicio.isoformat() if inicio else None
        info.valido_ate = fim.isoformat() if fim else None
        if fim:
            info.dias_para_expirar = (fim - datetime.now(timezone.utc)).days
        info.nomes_alternativos = [
            valor for tipo, valor in cert_dict.get("subjectAltName", ()) if tipo == "DNS"
        ]
    else:
        _preencher_com_cryptography(info, der)

    if info.nomes_alternativos:
        info.host_confere = _host_casa_com_certificado(ctx.host_ascii, info.nomes_alternativos)
    return info


def _host_casa_com_certificado(host: str, nomes: list[str]) -> bool:
    """Compara o host com os nomes do certificado, incluindo curinga simples."""
    for nome in nomes:
        nome = nome.lower().strip(".")
        if nome == host:
            return True
        if nome.startswith("*.") and host.endswith(nome[1:]) and host.count(".") == nome.count("."):
            return True
    return False


def achados_de_tls(ctx: ContextoURL, info: CertificadoTLS) -> list[Achado]:
    """Traduz os dados do certificado em sinais de risco explicáveis."""
    achados: list[Achado] = []

    if ctx.esquema == "http":
        achados.append(
            Achado(
                codigo="sem_https",
                titulo="Conexão sem criptografia (HTTP)",
                severidade=Severidade.ALTA,
                detalhe=(
                    "Tudo que for digitado nessa página trafega em texto puro e pode ser "
                    "lido por quem estiver na mesma rede."
                ),
                recomendacao="Nunca informe senha, CPF ou cartão em páginas sem cadeado.",
                evidencia={"esquema": "http"},
            )
        )
        return achados

    if not info.disponivel:
        achados.append(
            Achado(
                codigo="tls_indisponivel",
                titulo="Não foi possível estabelecer conexão segura",
                severidade=Severidade.MEDIA,
                detalhe=info.erro or "O servidor não respondeu ao handshake TLS.",
                recomendacao=(
                    "Pode ser um site fora do ar ou já derrubado. Não insista pelo link."
                ),
                evidencia={"erro": info.erro},
            )
        )
        return achados

    if info.cadeia_valida is False:
        autoassinado = bool(info.emissor and info.emissor == info.emitido_para)
        achados.append(
            Achado(
                codigo="certificado_autoassinado" if autoassinado else "certificado_invalido",
                titulo=(
                    "Certificado autoassinado (não confiável)"
                    if autoassinado
                    else "Certificado não confiável"
                ),
                severidade=Severidade.ALTA,
                detalhe=(
                    "O certificado apresentado não é reconhecido pelas autoridades em que "
                    f"o seu sistema confia. Motivo: {info.erro}"
                ),
                recomendacao="É o aviso de 'conexão não é particular'. Não prossiga.",
                evidencia={"emissor": info.emissor, "motivo": info.erro},
            )
        )

    if info.host_confere is False:
        achados.append(
            Achado(
                codigo="certificado_host_divergente",
                titulo="O certificado foi emitido para outro endereço",
                severidade=Severidade.ALTA,
                detalhe=(
                    f"O host '{ctx.host}' não está entre os nomes do certificado "
                    f"({', '.join(info.nomes_alternativos[:5])})."
                ),
                recomendacao="Indica reaproveitamento de certificado ou site clonado.",
                evidencia={"host": ctx.host, "nomes": info.nomes_alternativos[:10]},
            )
        )

    if info.dias_para_expirar is not None:
        if info.dias_para_expirar < 0:
            achados.append(
                Achado(
                    codigo="certificado_expirado",
                    titulo="Certificado vencido",
                    severidade=Severidade.ALTA,
                    detalhe=f"Venceu há {abs(info.dias_para_expirar)} dia(s), em {info.valido_ate}.",
                    recomendacao="Site abandonado ou mal mantido. Evite informar dados.",
                    evidencia={"valido_ate": info.valido_ate},
                )
            )
        elif info.dias_para_expirar <= 15:
            achados.append(
                Achado(
                    codigo="certificado_perto_do_vencimento",
                    titulo="Certificado perto de vencer",
                    severidade=Severidade.BAIXA,
                    detalhe=f"Vence em {info.dias_para_expirar} dia(s).",
                    recomendacao="Sinal fraco de manutenção precária.",
                    evidencia={"valido_ate": info.valido_ate},
                )
            )

    emitido_em = _idade_em_dias(info.valido_de)
    if emitido_em is not None and emitido_em <= 7:
        achados.append(
            Achado(
                codigo="certificado_recem_emitido",
                titulo="Certificado emitido há poucos dias",
                severidade=Severidade.BAIXA,
                detalhe=(
                    f"Emitido há {emitido_em} dia(s). Páginas de phishing costumam usar "
                    "certificados gratuitos criados na véspera da campanha."
                ),
                recomendacao="Sozinho não condena o site — pese junto com os demais sinais.",
                evidencia={"valido_de": info.valido_de},
            )
        )

    if info.versao_tls in _TLS_OBSOLETO:
        achados.append(
            Achado(
                codigo="tls_obsoleto",
                titulo=f"Protocolo obsoleto ({info.versao_tls})",
                severidade=Severidade.MEDIA,
                detalhe="Versão descontinuada pela IETF (RFC 8996) por fragilidades conhecidas.",
                recomendacao="Servidor desatualizado; trate os dados dessa página como expostos.",
                evidencia={"versao_tls": info.versao_tls},
            )
        )

    return achados


def _idade_em_dias(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        emitido = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if emitido.tzinfo is None:
        emitido = emitido.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - emitido).days
