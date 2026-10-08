"""Hash de senha e assinatura do cookie de sessão.

Sem dependência externa: `hashlib.scrypt` e `hmac` da biblioteca padrão dão
conta e evitam trazer bcrypt/argon2 só por isto. As duas decisões que importam:

* **scrypt, não SHA.** SHA-256 de senha é quebrado por força bruta em GPU. O
  scrypt é deliberadamente lento e caro em memória — os parâmetros abaixo
  levam ~100 ms por verificação, que é o ponto.
* **Comparação em tempo constante.** `compare_digest` em vez de `==`, para o
  tempo da resposta não revelar quantos bytes bateram.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode

#: Parâmetros do scrypt. N=2^14 é o piso recomendado para uso interativo.
_N = 2 ** 14
_R = 8
_P = 1
_TAMANHO_CHAVE = 32
_TAMANHO_SAL = 16


def gerar_hash(senha: str) -> str:
    """Devolve ``scrypt$N$r$p$sal_hex$chave_hex`` — os parâmetros junto.

    Guardar os parâmetros no próprio registro permite aumentar o custo depois
    sem invalidar as senhas já cadastradas.
    """
    sal = secrets.token_bytes(_TAMANHO_SAL)
    chave = hashlib.scrypt(
        senha.encode("utf-8"), salt=sal, n=_N, r=_R, p=_P, dklen=_TAMANHO_CHAVE
    )
    return f"scrypt${_N}${_R}${_P}${sal.hex()}${chave.hex()}"


def conferir_senha(senha: str, guardado: str | None) -> bool:
    """Confere a senha contra o hash. ``False`` para conta sem senha."""
    if not guardado:
        return False
    try:
        algoritmo, n, r, p, sal_hex, chave_hex = guardado.split("$")
        if algoritmo != "scrypt":
            return False
        chave = hashlib.scrypt(
            senha.encode("utf-8"),
            salt=bytes.fromhex(sal_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(chave_hex) // 2,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(chave.hex(), chave_hex)


# --------------------------------------------------------------------------- #
# Assinatura do cookie
# --------------------------------------------------------------------------- #


def _segredo() -> bytes:
    """Chave de assinatura do cookie.

    Em produção, defina ``SPECTRA_SEGREDO``. Sem ele, geramos uma chave nova a
    cada processo — o que é seguro, mas derruba todas as sessões a cada
    reinício (e não funciona com mais de uma réplica).
    """
    bruto = os.getenv("SPECTRA_SEGREDO")
    if bruto:
        return bruto.encode("utf-8")
    global _SEGREDO_EFEMERO
    if _SEGREDO_EFEMERO is None:
        _SEGREDO_EFEMERO = secrets.token_bytes(32)
    return _SEGREDO_EFEMERO


_SEGREDO_EFEMERO: bytes | None = None


def _b64(dado: bytes) -> str:
    return urlsafe_b64encode(dado).decode("ascii").rstrip("=")


def _de_b64(texto: str) -> bytes:
    return urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def assinar(valor: str) -> str:
    """``valor.assinatura`` — o valor não é secreto, só não pode ser forjado."""
    marca = hmac.new(_segredo(), valor.encode("utf-8"), hashlib.sha256).digest()
    return f"{_b64(valor.encode('utf-8'))}.{_b64(marca)}"


def abrir_assinado(token: str) -> str | None:
    """Devolve o valor se a assinatura confere, senão ``None``."""
    try:
        parte, marca = token.split(".", 1)
        valor = _de_b64(parte).decode("utf-8")
        esperada = hmac.new(_segredo(), valor.encode("utf-8"), hashlib.sha256).digest()
    except (ValueError, UnicodeDecodeError):
        return None
    return valor if hmac.compare_digest(_de_b64(marca), esperada) else None


def token_aleatorio(bytes_: int = 24) -> str:
    """Para `state` do OAuth e afins."""
    return secrets.token_urlsafe(bytes_)
