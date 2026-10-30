"""Runtime configuration. All secrets come from the environment / a git-ignored .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_prefix="CADW_", extra="ignore")

    # Connection parts (CADW_DB_*). The password has no usable default on purpose.
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "cambodia_dw"
    db_user: str = "cadw"
    db_password: str = Field(default="", repr=False)

    raw_dir: Path = PROJECT_ROOT / "data" / "raw"
    processed_dir: Path = PROJECT_ROOT / "data" / "processed"

    country_iso3: str = "KHM"
    country_m49: str = "116"  # FAOSTAT "Area Code (M49)" for Cambodia

    # CHIRPS is read month by month; keep the window explicit and configurable.
    chirps_start_year: int = 2000
    chirps_end_year: int = 2024
    chirps_base_url: str = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/tifs"

    http_timeout_s: int = 120
    http_retries: int = 4

    worldbank_indicators: list[str] = [
        "AG.LND.AGRI.ZS",  # Agricultural land (% of land area)
        "AG.LND.ARBL.ZS",  # Arable land (% of land area)
        "AG.PRD.CROP.XD",  # Crop production index (2014-2016 = 100)
        "NV.AGR.TOTL.ZS",  # Agriculture, forestry, fishing, value added (% of GDP)
        "SL.AGR.EMPL.ZS",  # Employment in agriculture (% of total employment)
        "SP.POP.TOTL",  # Population, total
        "NY.GDP.MKTP.CD",  # GDP (current US$)
        "AG.CON.FERT.ZS",  # Fertilizer consumption (kg per hectare of arable land)
    ]

    @property
    def database_url(self) -> URL:
        """SQLAlchemy URL built from parts, so special characters in the password are safe."""
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


def get_settings() -> Settings:
    return Settings()
