"""Camada web do Spectra: API JSON, acesso e paginas.

Nao reexportamos `app` aqui de proposito: o nome sombrearia o submodulo
`spectra_link_guard.web.app` e faria `web.app` resolver ora para o modulo,
ora para a instancia FastAPI. Importe sempre de `spectra_link_guard.web.app`.
"""
