from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
_POOL: Any | None = None


class OracleConfigError(RuntimeError):
    """Raised when Oracle access cannot be configured."""


@dataclass(frozen=True)
class OracleSettings:
    dsn: str
    user: str
    password: str

    @property
    def is_complete(self) -> bool:
        return bool(self.dsn and self.user and self.password)


def load_env_file(path: Path | None = None) -> None:
    env_path = path or ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_oracle_settings() -> OracleSettings:
    load_env_file()
    return OracleSettings(
        dsn=os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"),
        user=os.environ.get("ORACLE_USER", ""),
        password=os.environ.get("ORACLE_PASSWORD", ""),
    )


@contextmanager
def oracle_connection() -> Iterator[object]:
    pool = oracle_pool()
    connection = pool.acquire()
    try:
        yield connection
    finally:
        pool.release(connection)


def oracle_pool() -> object:
    global _POOL
    if _POOL is not None:
        return _POOL

    settings = get_oracle_settings()
    if not settings.is_complete:
        raise OracleConfigError("Oracle connection unavailable. Missing Oracle credentials.")

    try:
        import oracledb
    except ModuleNotFoundError as exc:
        message = "Oracle connection unavailable. python-oracledb is not installed."
        raise OracleConfigError(message) from exc

    _POOL = oracledb.create_pool(
        user=settings.user,
        password=settings.password,
        dsn=settings.dsn,
        min=int(os.environ.get("ORACLE_POOL_MIN", "1")),
        max=int(os.environ.get("ORACLE_POOL_MAX", "12")),
        increment=int(os.environ.get("ORACLE_POOL_INCREMENT", "1")),
        timeout=int(os.environ.get("ORACLE_POOL_TIMEOUT", "60")),
        wait_timeout=int(os.environ.get("ORACLE_POOL_WAIT_TIMEOUT", "5000")),
    )
    return _POOL
