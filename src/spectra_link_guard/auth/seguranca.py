"""Argon2id para senhas novas; migração de scrypt no login; cookies com HMAC."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import binascii
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from base64 import urlsafe_b64decode, urlsafe_b64encode

#: Parâmetros antigos mantidos somente para compatibilidade de registros.
_N = 2 ** 14
_R = 8
_P = 1
_TAMANHO_CHAVE = 32
_TAMANHO_SAL = 16
_ARGON = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
_HASH_FICTICIO = _ARGON.hash(secrets.token_urlsafe(32))


def gerar_hash(senha: str) -> str:
    """Devolve um hash Argon2id com sal aleatório e parâmetros no registro.

    Guardar os parâmetros no próprio registro permite aumentar o custo depois
    sem invalidar as senhas já cadastradas.
    """
    return _ARGON.hash(senha)


def conferir_senha(senha: str, guardado: str | None) -> bool:
    """Confere a senha contra o hash. ``False`` para conta sem senha."""
    if not guardado:
        try: _ARGON.verify(_HASH_FICTICIO, senha)
        except VerificationError: pass
        return False
    if guardado.startswith('$argon2id$'):
        try: return _ARGON.verify(guardado,senha)
        except (VerificationError,InvalidHashError): return False
    try:
        algoritmo, n, r, p, sal_hex, chave_hex = guardado.split("$")
        if algoritmo != "scrypt":
            return False
        if (int(n),int(r),int(p)) not in {(16384,8,1),(16384,8,5),(32768,8,3),(65536,8,2),(131072,8,1)} or len(chave_hex)!=64 or len(sal_hex)!=32:
            return False
        chave = hashlib.scrypt(
            senha.encode("utf-8"),
            salt=bytes.fromhex(sal_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(chave_hex) // 2,
            maxmem=256*1024*1024,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(chave.hex(), chave_hex)


def precisa_atualizar(guardado):
    if not guardado or not guardado.startswith('$argon2id$'): return True
    return _ARGON.check_needs_rehash(guardado)


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
        if not isinstance(token,str) or len(token)>4096: return None
        parte, marca = token.split(".", 1)
        valor = _de_b64(parte).decode("utf-8")
        assinatura = _de_b64(marca)
        esperada = hmac.new(_segredo(), valor.encode("utf-8"), hashlib.sha256).digest()
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return None
    return valor if hmac.compare_digest(assinatura, esperada) else None


def token_aleatorio(bytes_: int = 24) -> str:
    """Para `state` do OAuth e afins."""
    return secrets.token_urlsafe(bytes_)
