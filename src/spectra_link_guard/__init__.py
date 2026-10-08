"""Spectra Link Guard — análise passiva de risco de links.

Ferramenta defensiva de proteção ao consumidor: recebe uma URL e devolve um
laudo explicando, em linguagem simples, por que aquele endereço é ou não
confiável.

Todas as verificações são passivas e baseadas em informação pública:

  1. :mod:`~spectra_link_guard.sintaxe`   — análise da string, 100% offline;
  2. :mod:`~spectra_link_guard.tls`       — um handshake TLS, lendo o certificado
     público que o servidor apresenta (o mesmo dado do cadeado do navegador);
  3. :mod:`~spectra_link_guard.reputacao` — leitura de listas públicas de ameaças.

A ferramenta **não** realiza varredura de portas, exploração de falhas, injeção
de código, força bruta, enumeração de diretórios ou qualquer outra atividade que
o Art. 154-A do Código Penal (Lei 12.737/2012) descreve como invasão de
dispositivo informático. O tráfego gerado é menor do que o de abrir o link no
navegador, e é opcional (``verificar_tls=False`` deixa a análise 100% offline).
"""

from .analisador import ConfiguracaoLinkGuard, LinkGuard, analisar_url
from .models import (
    Achado,
    AnaliseLink,
    CertificadoTLS,
    NivelRisco,
    ResultadoReputacao,
    Severidade,
    StatusReputacao,
)

__version__ = "0.1.0"

__all__ = [
    "Achado",
    "AnaliseLink",
    "CertificadoTLS",
    "ConfiguracaoLinkGuard",
    "LinkGuard",
    "NivelRisco",
    "ResultadoReputacao",
    "Severidade",
    "StatusReputacao",
    "analisar_url",
    "__version__",
]
