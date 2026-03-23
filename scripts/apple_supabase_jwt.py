#!/usr/bin/env python3
"""
Generate Apple OAuth client secret (JWT) for Supabase "Secret Key" field.
Uses your .p8 from ~/Downloads/AuthKey_<KEYID>.p8 by default.

Usage:
  pip install PyJWT cryptography
  python3 scripts/apple_supabase_jwt.py

Or set the key path explicitly:
  APPLE_P8_PATH=/path/to/AuthKey_XXX.p8 python3 scripts/apple_supabase_jwt.py

Paste the printed line into Supabase → Auth → Apple → Secret Key (not the .p8 contents).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

try:
    import jwt
except ImportError:
    print("Install dependencies: pip install PyJWT cryptography", file=sys.stderr)
    sys.exit(1)

# From Apple Developer (Membership + Key + Services ID)
TEAM_ID = "ZL3QKV2M92"
KEY_ID = "AJ9TKP9V54"
CLIENT_ID = "global.tryon.web"


def main() -> None:
    env_path = os.environ.get("APPLE_P8_PATH")
    if env_path:
        key_path = Path(env_path).expanduser()
    else:
        key_path = Path.home() / "Downloads" / f"AuthKey_{KEY_ID}.p8"

    if not key_path.is_file():
        print(f"Cannot find key file: {key_path}", file=sys.stderr)
        print(
            "Put AuthKey_AJ9TKP9V54.p8 in ~/Downloads/ or run:\n"
            "  APPLE_P8_PATH=/full/path/to/AuthKey_XXX.p8 python3 scripts/apple_supabase_jwt.py",
            file=sys.stderr,
        )
        sys.exit(1)

    private_key = key_path.read_text()
    now = int(time.time())
    payload = {
        "iss": TEAM_ID,
        "iat": now,
        "exp": now + 86400 * 150,  # ~150 days; Apple allows up to ~6 months
        "aud": "https://appleid.apple.com",
        "sub": CLIENT_ID,
    }
    token = jwt.encode(
        payload,
        private_key,
        algorithm="ES256",
        headers={"kid": KEY_ID, "alg": "ES256"},
    )
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    print(token)


if __name__ == "__main__":
    main()
