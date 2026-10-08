"""Interface de linha de comando — útil para demonstração e testes manuais.

    python -m spectra_link_guard "https://itau.seguranca-cliente.top/login"
    python -m spectra_link_guard --offline --json "http://192.168.0.1/boleto.exe"
"""

from __future__ import annotations

import argparse
import json
import sys

from .analisador import ConfiguracaoLinkGuard, analisar_url
from .models import AnaliseLink, NivelRisco, Severidade

_CORES = {
    NivelRisco.SEGURO: "\033[32m",
    NivelRisco.BAIXO: "\033[32m",
    NivelRisco.ATENCAO: "\033[33m",
    NivelRisco.ALTO: "\033[31m",
    NivelRisco.CRITICO: "\033[1;31m",
}
_RESET = "\033[0m"

_MARCADOR = {
    Severidade.INFO: "·",
    Severidade.BAIXA: "-",
    Severidade.MEDIA: "!",
    Severidade.ALTA: "!!",
    Severidade.CRITICA: "!!!",
}


def _imprimir(relatorio: AnaliseLink, colorido: bool) -> None:
    cor = _CORES.get(relatorio.nivel, "") if colorido else ""
    fim = _RESET if colorido else ""
    print(f"\nURL......: {relatorio.url_original}")
    print(f"Domínio..: {relatorio.dominio_registravel or '—'}")
    print(f"Risco....: {cor}{relatorio.risco}/100 · {relatorio.nivel.value.upper()}{fim}")
    print(f"\n{relatorio.resumo}\n")

    if relatorio.achados:
        print("Achados:")
        for a in relatorio.achados:
            print(f"  [{_MARCADOR[a.severidade]:>3}] {a.titulo}")
            print(f"        {a.detalhe}")
            print(f"        → {a.recomendacao}")

    if relatorio.tls and relatorio.tls.disponivel:
        t = relatorio.tls
        print("\nCertificado (dados públicos apresentados pelo servidor):")
        print(f"  emitido para : {t.emitido_para}")
        print(f"  emissor      : {t.emissor}")
        print(f"  validade     : {t.valido_de} → {t.valido_ate} ({t.dias_para_expirar} dias)")
        print(f"  protocolo    : {t.versao_tls} / {t.cifra}")
        print(f"  cadeia válida: {'sim' if t.cadeia_valida else 'NÃO'}")

    if relatorio.reputacao:
        print("\nListas públicas de ameaças:")
        for r in relatorio.reputacao:
            print(f"  {r.provedor:<24} {r.status.value:<16} {r.mensagem or ''}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spectra-link-guard",
        description=(
            "Análise passiva de risco de uma URL. Não realiza invasão, varredura "
            "de portas nem exploração de vulnerabilidades."
        ),
    )
    parser.add_argument("url", help="endereço a analisar")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="apenas análise sintática: não abre conexão nem consulta APIs",
    )
    parser.add_argument("--sem-tls", action="store_true", help="não inspeciona o certificado")
    parser.add_argument("--sem-reputacao", action="store_true", help="não consulta as blacklists")
    parser.add_argument("--json", action="store_true", help="saída em JSON")
    args = parser.parse_args(argv)

    config = ConfiguracaoLinkGuard.do_ambiente(
        verificar_tls=not (args.offline or args.sem_tls),
        verificar_reputacao=not (args.offline or args.sem_reputacao),
        verificar_registro=not args.offline,
    )
    relatorio = analisar_url(args.url, config)

    if args.json:
        print(json.dumps(relatorio.to_dict(), ensure_ascii=False, indent=2))
    else:
        _imprimir(relatorio, colorido=sys.stdout.isatty())

    # Código de saída ≥ 1 quando há risco relevante: facilita uso em scripts.
    return 0 if relatorio.nivel in (NivelRisco.SEGURO, NivelRisco.BAIXO) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
