# config.py — APP SETTINGS.
# Reads values from the backend/.env file (copy .env.example to .env to create it).
# This way each teammate can use their own database without changing code.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Where the PostgreSQL database is. Used by database.py.
    database_url: str = "postgresql+psycopg://gradtrack:gradtrack@localhost:5432/gradtrack"
    # Where the React app runs. Used by main.py for CORS.
    frontend_origin: str = "http://localhost:5173"

    # --- Login settings (used by security.py) ---
    # Secret key used to SIGN login tokens. Anyone who knows it can create fake tokens,
    # so in .env set it to a long random value and never share it.
    # Make one with:  python -c "import secrets; print(secrets.token_hex(32))"
    jwt_secret: str = "dev-only-secret-change-me"
    # How long a login lasts before the user must log in again.
    jwt_expire_minutes: int = 60

    # Values in .env override the defaults above.
    model_config = SettingsConfigDict(env_file=".env")


# Import this anywhere you need a setting:  from app.core.config import settings
settings = Settings()
