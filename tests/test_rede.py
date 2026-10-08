"""Testes do RDAP e do DNS, com transporte e resolvedor simulados (sem rede)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from spectra_link_guard import rede
from spectra_link_guard.models import Severidade
from spectra_link_guard.rede import (
    RegistroDominio,
    achados_de_registro,
    consultar_hospedagem,
    consultar_registro,
)


def rodar(coro):
    return asyncio.run(coro)


def cliente(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def rdap_dominio(dias_atras: int) -> dict:
    criado = datetime.now(timezone.utc) - timedelta(days=dias_atras)
    return {
        "events": [{"eventAction": "registration", "eventDate": criado.isoformat()}],
        "entities": [
            {
                "roles": ["registrar"],
                "vcardArray": ["vcard", [["fn", {}, "text", "Registro.br"]]],
            }
        ],
    }


async def _registro(handler, dominio="exemplo.com.br"):
    async with cliente(handler) as c:
        return await consultar_registro(c, dominio)


# --------------------------------------------------------------------------- #
# RDAP do domínio
# --------------------------------------------------------------------------- #


def test_le_data_de_registro_e_registrador():
    info = rodar(_registro(lambda req: httpx.Response(200, json=rdap_dominio(400))))
    assert info.consultado
    assert info.idade_dias == 400
    assert info.registrador == "Registro.br"


def test_dominio_fora_do_rdap():
    info = rodar(_registro(lambda req: httpx.Response(404)))
    assert not info.consultado
    assert "não consta" in (info.erro or "")


def test_rdap_indisponivel_nao_quebra_a_analise():
    info = rodar(_registro(lambda req: httpx.Response(503)))
    assert not info.consultado
    assert info.idade_dias is None


def test_registry_sem_data_de_registro():
    info = rodar(_registro(lambda req: httpx.Response(200, json={"events": []})))
    assert info.consultado
    assert info.idade_dias is None
    assert "não publica a data" in (info.erro or "")


# --------------------------------------------------------------------------- #
# Achados por idade
# --------------------------------------------------------------------------- #


def test_dominio_de_dias_e_achado_alto():
    achados = achados_de_registro(RegistroDominio(consultado=True, idade_dias=3))
    assert achados[0].codigo == "dominio_recem_registrado"
    assert achados[0].severidade is Severidade.ALTA


def test_dominio_de_semanas_e_achado_medio():
    achados = achados_de_registro(RegistroDominio(consultado=True, idade_dias=60))
    assert achados[0].codigo == "dominio_novo"
    assert achados[0].severidade is Severidade.MEDIA


def test_dominio_antigo_e_apenas_informativo():
    """Sinal favorável não pode somar risco: peso de INFO é zero."""
    achados = achados_de_registro(RegistroDominio(consultado=True, idade_dias=4000))
    assert achados[0].codigo == "dominio_estabelecido"
    assert achados[0].severidade is Severidade.INFO


def test_faixa_intermediaria_nao_gera_achado():
    assert achados_de_registro(RegistroDominio(consultado=True, idade_dias=365)) == []


def test_sem_consulta_nao_gera_achado():
    assert achados_de_registro(RegistroDominio()) == []


# --------------------------------------------------------------------------- #
# DNS + RDAP do IP
# --------------------------------------------------------------------------- #


def test_hospedagem_resolve_e_descreve_a_rede(monkeypatch):
    monkeypatch.setattr(rede, "_resolver", lambda host: (["203.0.113.10"], "srv.exemplo"))
    handler = lambda req: httpx.Response(200, json={"country": "BR", "name": "EXEMPLO-NET"})  # noqa: E731
    async def executar():
        async with cliente(handler) as c:
            return await consultar_hospedagem(c, "exemplo.com.br")

    info = rodar(executar())
    assert info.consultado
    assert info.ips == ["203.0.113.10"]
    assert info.pais == "BR"
    assert info.rede == "EXEMPLO-NET"
    assert info.reverso == "srv.exemplo"


def test_host_que_nao_resolve(monkeypatch):
    def estourar(host):
        raise OSError("getaddrinfo failed")

    monkeypatch.setattr(rede, "_resolver", estourar)

    async def executar():
        async with cliente(lambda req: httpx.Response(200, json={})) as c:
            return await consultar_hospedagem(c, "nao-existe.invalid")

    info = rodar(executar())
    assert not info.consultado
    assert "não resolve" in (info.erro or "")


def test_ip_resolve_mas_rdap_falha(monkeypatch):
    """Perder o dono da rede não invalida o IP que já foi resolvido."""
    monkeypatch.setattr(rede, "_resolver", lambda host: (["198.51.100.7"], None))

    async def executar():
        async with cliente(lambda req: httpx.Response(500)) as c:
            return await consultar_hospedagem(c, "exemplo.com")

    info = rodar(executar())
    assert info.consultado
    assert info.ips == ["198.51.100.7"]
    assert info.pais is None


# --------------------------------------------------------------------------- #
# DNS (MX, SPF, DMARC, CAA) e status do registro
# --------------------------------------------------------------------------- #


def doh(respostas: dict[tuple[str, str], list[str]]):
    """Transporte que responde a consultas DoH a partir de um dicionário."""

    def handler(req):
        nome = req.url.params.get("name")
        tipo = req.url.params.get("type")
        dados = respostas.get((nome, tipo), [])
        return httpx.Response(200, json={"Status": 0, "Answer": [{"data": d} for d in dados]})

    return handler


def test_le_mx_spf_dmarc_e_caa():
    from spectra_link_guard.rede import consultar_dns

    handler = doh({
        ("loja.com.br", "MX"): ["10 mx1.provedor.com.", "20 mx2.provedor.com."],
        ("loja.com.br", "NS"): ["ns1.provedor.com."],
        ("loja.com.br", "TXT"): ['"v=spf1 include:provedor.com ~all"', '"google-site-verification=x"'],
        ("loja.com.br", "CAA"): ['0 issue "letsencrypt.org"'],
        ("_dmarc.loja.com.br", "TXT"): ['"v=DMARC1; p=reject; rua=mailto:a@loja.com.br"'],
    })

    async def executar():
        async with cliente(handler) as c:
            return await consultar_dns(c, "loja.com.br")

    dns = rodar(executar())
    assert dns.consultado
    assert dns.mx == ["mx1.provedor.com", "mx2.provedor.com"]  # sem prioridade nem ponto final
    assert dns.spf.startswith("v=spf1")
    assert "p=reject" in dns.dmarc
    assert dns.caa == ['0 issue "letsencrypt.org"']


def test_dns_indisponivel_nao_quebra():
    from spectra_link_guard.rede import consultar_dns

    async def executar():
        async with cliente(lambda req: httpx.Response(500)) as c:
            return await consultar_dns(c, "loja.com.br")

    dns = rodar(executar())
    assert not dns.consultado
    assert "indisponível" in (dns.erro or "")


def _dns(**campos):
    from spectra_link_guard.rede import DNS

    base = {"consultado": True, "mx": ["mx.loja.com"], "spf": "v=spf1 -all",
            "dmarc": "v=DMARC1; p=reject", "caa": ['0 issue "le.org"']}
    base.update(campos)
    return DNS(**base)


def codigos_dns(dns, registro=None):
    from spectra_link_guard.rede import RegistroDominio, achados_de_dns

    return {a.codigo for a in achados_de_dns(dns, registro or RegistroDominio())}


def test_dominio_bem_configurado_nao_gera_achado():
    assert codigos_dns(_dns()) == set()


def test_falta_de_spf_dmarc_e_caa_e_apenas_informativo():
    """A decisão de calibração: isso é problema do dono, não risco do link.

    Se entrasse como MEDIA, todo site pequeno e honesto do Brasil ganharia
    risco por uma lacuna de configuração de e-mail.
    """
    from spectra_link_guard.rede import RegistroDominio, achados_de_dns

    achados = achados_de_dns(_dns(spf=None, dmarc=None, caa=[]), RegistroDominio())
    assert {a.codigo for a in achados} == {"sem_spf", "sem_dmarc", "sem_caa"}
    assert all(a.severidade is Severidade.INFO for a in achados)


def test_spf_so_e_cobrado_de_quem_tem_mx():
    """Domínio que não recebe e-mail não precisa de SPF."""
    assert "sem_spf" not in codigos_dns(_dns(mx=[], spf=None))


def test_dmarc_em_p_none_e_apontado():
    assert "dmarc_permissivo" in codigos_dns(_dns(dmarc="v=DMARC1; p=none"))


def test_dominio_suspenso_e_achado_alto():
    from spectra_link_guard.rede import RegistroDominio, achados_de_dns

    reg = RegistroDominio(consultado=True, status=["client hold"])
    achados = achados_de_dns(_dns(), reg)
    suspenso = next(a for a in achados if a.codigo == "dominio_suspenso")
    assert suspenso.severidade is Severidade.ALTA


def test_dominio_vencido_e_achado_medio():
    from spectra_link_guard.rede import RegistroDominio, achados_de_dns

    reg = RegistroDominio(consultado=True, dias_para_expirar=-5, expira_em="2020-01-01")
    vencido = next(a for a in achados_de_dns(_dns(), reg) if a.codigo == "dominio_expirado")
    assert vencido.severidade is Severidade.MEDIA


def test_dns_nao_consultado_ainda_avalia_o_registro():
    """Se o DoH falhar, status e vencimento do RDAP continuam valendo."""
    from spectra_link_guard.rede import DNS, RegistroDominio, achados_de_dns

    reg = RegistroDominio(consultado=True, status=["server hold"])
    assert "dominio_suspenso" in {a.codigo for a in achados_de_dns(DNS(), reg)}
