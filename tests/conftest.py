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


@pytest.fixture(autouse=True)
def origem_do_navegador(monkeypatch):
    """O TestClient simula as requisições same-origin feitas pelo frontend.

    Testes de CSRF removem ou substituem esse cabeçalho explicitamente.
    """
    from fastapi.testclient import TestClient
    from urllib.parse import urlsplit
    inicializar = TestClient.__init__

    def com_origem(self, *args, **kwargs):
        base = urlsplit(kwargs.get('base_url', 'http://testserver'))
        headers = dict(kwargs.get('headers') or {})
        headers.setdefault('origin', f'{base.scheme}://{base.netloc}')
        kwargs['headers'] = headers
        inicializar(self, *args, **kwargs)

    monkeypatch.setattr(TestClient, '__init__', com_origem)
