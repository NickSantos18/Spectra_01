"""Isola o banco de cada execução de teste.

Sem isto, a suíte escreveria em `dados/spectra.db` de desenvolvimento e os
testes de cadastro passariam uma vez só — na segunda o e-mail já existiria.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def banco_temporario(tmp_path, monkeypatch):
    from spectra_link_guard.auth import bd

    monkeypatch.setattr(bd, "CAMINHO_BD", tmp_path / "teste.db")
    monkeypatch.setattr(bd, "_PRONTO", False)
    yield
