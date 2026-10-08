"""Agregação dos achados em uma nota de risco explicável.

A pontuação é deliberadamente simples e auditável: soma dos pesos de cada
severidade, saturada em 100. Não há modelo estatístico opaco — o usuário
(e o professor avaliador) consegue reconstruir o número à mão a partir da
lista de achados, o que é essencial numa ferramenta que faz acusações
sobre sites de terceiros.
"""

from __future__ import annotations

from .models import PESO_SEVERIDADE, Achado, NivelRisco, Severidade

#: Limiar inferior de cada nível (risco 0 = nenhum sinal encontrado).
_FAIXAS: tuple[tuple[int, NivelRisco], ...] = (
    (80, NivelRisco.CRITICO),
    (55, NivelRisco.ALTO),
    (30, NivelRisco.ATENCAO),
    (10, NivelRisco.BAIXO),
    (0, NivelRisco.SEGURO),
)

_MENSAGENS: dict[NivelRisco, str] = {
    NivelRisco.CRITICO: (
        "Não abra este link. Foram encontrados sinais fortes de fraude ou de "
        "conteúdo já denunciado publicamente."
    ),
    NivelRisco.ALTO: (
        "Link com risco alto. Evite abrir e, em nenhuma hipótese, informe senha, "
        "CPF ou dados de cartão."
    ),
    NivelRisco.ATENCAO: (
        "Há sinais que merecem atenção. Confirme o endereço com a empresa por um "
        "canal oficial antes de continuar."
    ),
    NivelRisco.BAIXO: (
        "Poucos sinais de risco. Ainda assim, digite o endereço oficial em vez de "
        "usar links recebidos por mensagem."
    ),
    NivelRisco.SEGURO: (
        "Nenhum sinal de risco na análise passiva. Isso não é um atestado de "
        "idoneidade: um site novo e ainda não denunciado passa por aqui."
    ),
}


def nivel_de(risco: int) -> NivelRisco:
    """Converte a nota numérica no rótulo exibido ao usuário."""
    for limiar, nivel in _FAIXAS:
        if risco >= limiar:
            return nivel
    return NivelRisco.SEGURO  # pragma: no cover - inalcançável


def calcular(achados: list[Achado]) -> tuple[int, NivelRisco, str]:
    """Devolve ``(risco 0-100, nível, resumo em linguagem simples)``.

    Achados repetidos (mesmo código) contam uma única vez, para que uma regra
    barulhenta não domine a nota.
    """
    unicos: dict[str, Achado] = {}
    for achado in achados:
        anterior = unicos.get(achado.codigo)
        if anterior is None or PESO_SEVERIDADE[achado.severidade] > PESO_SEVERIDADE[anterior.severidade]:
            unicos[achado.codigo] = achado

    risco = min(100, sum(PESO_SEVERIDADE[a.severidade] for a in unicos.values()))

    # Um único achado crítico já basta para o topo da escala: são regras que,
    # sozinhas, caracterizam fraude (domínio sósia, URL em blacklist pública).
    if any(a.severidade is Severidade.CRITICA for a in unicos.values()):
        risco = max(risco, 80)

    nivel = nivel_de(risco)
    principais = [
        a.titulo
        for a in sorted(
            unicos.values(), key=lambda a: PESO_SEVERIDADE[a.severidade], reverse=True
        )
        if a.severidade is not Severidade.INFO
    ][:3]

    resumo = _MENSAGENS[nivel]
    if principais:
        resumo += " Principais pontos: " + "; ".join(principais) + "."
    return risco, nivel, resumo
