"""Modelos de dados do Spectra Link Guard.

ESCOPO DEFENSIVO E PASSIVO
--------------------------
As estruturas deste módulo descrevem apenas *observações* sobre uma URL:
o que a própria string revela, o que o servidor apresenta espontaneamente
no handshake TLS e o que listas públicas de reputação já publicaram.

Nada aqui modela invasão, exploração de vulnerabilidade, varredura de portas,
força bruta ou injeção — a ferramenta é de proteção ao consumidor e opera
dentro do que qualquer navegador comum faz ao abrir um link.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Severidade(str, Enum):
    """Gravidade de um achado isolado."""

    INFO = "info"
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


#: Quanto cada severidade contribui para o risco agregado (0-100).
PESO_SEVERIDADE: dict[Severidade, int] = {
    Severidade.INFO: 0,
    Severidade.BAIXA: 6,
    Severidade.MEDIA: 16,
    Severidade.ALTA: 30,
    Severidade.CRITICA: 55,
}


class NivelRisco(str, Enum):
    """Veredito final, pensado para ser exibido ao usuário leigo."""

    SEGURO = "seguro"
    BAIXO = "baixo"
    ATENCAO = "atencao"
    ALTO = "alto"
    CRITICO = "critico"


class StatusReputacao(str, Enum):
    """Resultado da consulta a uma lista pública de reputação."""

    MALICIOSO = "malicioso"          # a lista marca a URL/domínio como nocivo
    LIMPO = "limpo"                  # consultado e sem marcação
    DESCONHECIDO = "desconhecido"    # a lista não conhece esta URL
    NAO_CONFIGURADO = "nao_configurado"  # falta chave de API
    ERRO = "erro"                    # falha de rede, cota, timeout


@dataclass(frozen=True)
class Achado:
    """Um sinal de risco observado, com explicação didática para o usuário."""

    codigo: str
    titulo: str
    severidade: Severidade
    detalhe: str
    recomendacao: str
    evidencia: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severidade"] = self.severidade.value
        return d


@dataclass(frozen=True)
class CriterioChecklist:
    """Uma linha da checklist heurística exibida na tela de resultado.

    Independe de achado: cobre também os critérios que *passaram*, o que
    ``Achado`` não representa (achado só existe quando algo está errado).
    """

    codigo: str
    rotulo: str
    passou: bool
    motivo: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CertificadoTLS:
    """Dados públicos que o servidor apresenta no handshake TLS.

    São exatamente as informações que o cadeado do navegador mostra: nenhuma
    requisição HTTP é feita, nenhum conteúdo do site é baixado.
    """

    disponivel: bool = False
    cadeia_valida: bool | None = None
    versao_tls: str | None = None
    cifra: str | None = None
    emitido_para: str | None = None
    emissor: str | None = None
    valido_de: str | None = None
    valido_ate: str | None = None
    dias_para_expirar: int | None = None
    nomes_alternativos: list[str] = field(default_factory=list)
    host_confere: bool | None = None
    erro: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResultadoReputacao:
    """Resposta de um provedor público de blacklist."""

    provedor: str
    status: StatusReputacao
    categorias: list[str] = field(default_factory=list)
    positivos: int | None = None
    total_motores: int | None = None
    mensagem: str | None = None
    referencia: str | None = None

    @property
    def malicioso(self) -> bool:
        return self.status is StatusReputacao.MALICIOSO

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class AnaliseLink:
    """Relatório completo e serializável de uma análise passiva."""

    url_original: str
    url_normalizada: str | None = None
    host: str | None = None
    dominio_registravel: str | None = None
    achados: list[Achado] = field(default_factory=list)
    checklist: list[CriterioChecklist] = field(default_factory=list)
    tls: CertificadoTLS | None = None
    reputacao: list[ResultadoReputacao] = field(default_factory=list)
    registro: Any | None = None       # RegistroDominio (RDAP), ver rede.py
    hospedagem: Any | None = None     # Hospedagem (DNS + RDAP do IP)
    dns: Any | None = None            # DNS (MX, SPF, DMARC, CAA, NS)
    risco: int = 0
    nivel: NivelRisco = NivelRisco.SEGURO
    resumo: str = ""
    analisado_em: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        """Formato pronto para virar resposta JSON de uma API."""
        return {
            "url_original": self.url_original,
            "url_normalizada": self.url_normalizada,
            "host": self.host,
            "dominio_registravel": self.dominio_registravel,
            "risco": self.risco,
            "nivel": self.nivel.value,
            "resumo": self.resumo,
            "achados": [a.to_dict() for a in self.achados],
            "checklist": [c.to_dict() for c in self.checklist],
            "tls": self.tls.to_dict() if self.tls else None,
            "reputacao": [r.to_dict() for r in self.reputacao],
            "registro": self.registro.to_dict() if self.registro else None,
            "hospedagem": self.hospedagem.to_dict() if self.hospedagem else None,
            "dns": self.dns.to_dict() if self.dns else None,
            "analisado_em": self.analisado_em,
        }
