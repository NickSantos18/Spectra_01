"""Testes da agregação de risco."""

from __future__ import annotations

from spectra_link_guard.models import Achado, NivelRisco, Severidade
from spectra_link_guard.pontuacao import calcular, nivel_de


def _achado(codigo: str, severidade: Severidade) -> Achado:
    return Achado(
        codigo=codigo,
        titulo=f"titulo {codigo}",
        severidade=severidade,
        detalhe="detalhe",
        recomendacao="recomendacao",
    )


def test_sem_achados_e_seguro():
    risco, nivel, resumo = calcular([])
    assert risco == 0
    assert nivel is NivelRisco.SEGURO
    assert "não é um atestado" in resumo


def test_info_nao_pontua():
    risco, nivel, _ = calcular([_achado("x", Severidade.INFO)])
    assert risco == 0
    assert nivel is NivelRisco.SEGURO


def test_um_critico_leva_ao_topo_da_escala():
    risco, nivel, _ = calcular([_achado("x", Severidade.CRITICA)])
    assert risco >= 80
    assert nivel is NivelRisco.CRITICO


def test_achados_repetidos_contam_uma_vez():
    dois_iguais = [_achado("x", Severidade.MEDIA), _achado("x", Severidade.MEDIA)]
    um_so = [_achado("x", Severidade.MEDIA)]
    assert calcular(dois_iguais)[0] == calcular(um_so)[0]


def test_severidade_maior_prevalece_no_mesmo_codigo():
    risco, _, _ = calcular([_achado("x", Severidade.BAIXA), _achado("x", Severidade.ALTA)])
    assert risco == calcular([_achado("x", Severidade.ALTA)])[0]


def test_soma_de_medios_escala():
    risco, nivel, _ = calcular(
        [_achado("a", Severidade.MEDIA), _achado("b", Severidade.MEDIA)]
    )
    assert risco == 32
    assert nivel is NivelRisco.ATENCAO


def test_risco_nunca_passa_de_cem():
    muitos = [_achado(str(i), Severidade.ALTA) for i in range(10)]
    assert calcular(muitos)[0] == 100


def test_faixas():
    assert nivel_de(0) is NivelRisco.SEGURO
    assert nivel_de(9) is NivelRisco.SEGURO
    assert nivel_de(10) is NivelRisco.BAIXO
    assert nivel_de(30) is NivelRisco.ATENCAO
    assert nivel_de(55) is NivelRisco.ALTO
    assert nivel_de(100) is NivelRisco.CRITICO


def test_resumo_cita_os_principais_achados():
    _, _, resumo = calcular([_achado("a", Severidade.ALTA), _achado("b", Severidade.BAIXA)])
    assert "titulo a" in resumo
