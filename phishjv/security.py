"""Tokens de tracking assinados com HMAC.

Cada e-mail enviado carrega um token que identifica (campanha, alvo, tipo de evento)
de forma não-forjável. Sem o segredo, ninguém consegue inflar métricas fabricando eventos.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json

from .config import settings


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _sign(payload: bytes) -> str:
    sig = hmac.new(settings.secret.encode(), payload, hashlib.sha256).digest()
    return _b64e(sig)


def make_token(campaign_id: int, target_id: int, kind: str) -> str:
    """Gera token opaco e assinado para um alvo numa campanha."""
    body = {"c": campaign_id, "t": target_id, "k": kind}
    payload = _b64e(json.dumps(body, separators=(",", ":")).encode())
    return f"{payload}.{_sign(payload.encode())}"


def read_token(token: str) -> dict | None:
    """Valida a assinatura e devolve {campaign_id, target_id, kind} ou None se inválido."""
    try:
        payload, sig = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sign(payload.encode())):
        return None
    try:
        body = json.loads(_b64d(payload))
        return {"campaign_id": int(body["c"]), "target_id": int(body["t"]), "kind": str(body["k"])}
    except (ValueError, KeyError, json.JSONDecodeError):
        return None
