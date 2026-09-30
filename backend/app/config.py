from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _odbc_value(value: str) -> str:
    """Brace-quote a connection-string value so ';', '=' or '}' in it can't break the string."""
    return "{" + value.replace("}", "}}") + "}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8-sig",  # tolerate the BOM Windows editors / PowerShell add
        env_ignore_empty=True,
        extra="ignore",
    )

    db_server: str = "PRITI_LAPTOP"
    db_port: int | None = None
    db_name: str = "HR_QA_DB"
    db_user: str
    db_password: str
    db_driver: str = "ODBC Driver 17 for SQL Server"
    db_encrypt: bool = False
    db_trust_server_certificate: bool = True
    db_timeout_seconds: int = 5

    @property
    def connection_string(self) -> str:
        server = f"{self.db_server},{self.db_port}" if self.db_port else self.db_server
        parts = {
            "DRIVER": _odbc_value(self.db_driver),
            "SERVER": _odbc_value(server),
            "DATABASE": _odbc_value(self.db_name),
            "UID": _odbc_value(self.db_user),
            "PWD": _odbc_value(self.db_password),
            "Encrypt": "yes" if self.db_encrypt else "no",
            "TrustServerCertificate": "yes" if self.db_trust_server_certificate else "no",
            "APP": "pain-data-api",
        }
        return ";".join(f"{key}={value}" for key, value in parts.items())


@lru_cache
def get_settings() -> Settings:
    return Settings()
