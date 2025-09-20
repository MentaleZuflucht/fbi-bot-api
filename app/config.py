import logging
import logging.config
import yaml
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    app_name: str = "FBI Bot API"
    app_version: str = "1.0.0"
    debug: bool = False

    auth_database_url: str
    discord_database_url: str

    api_key_secret: str

    default_rate_limit_per_hour: int = 300
    default_rate_limit_per_day: int = 5000

    allowed_origins: str = "http://localhost:3000"

    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def allowed_origins_list(self) -> list[str]:
        """Convert comma-separated origins to list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


class CustomFormatter(logging.Formatter):
    """
    Custom formatter to add colors to log messages.
    """
    COLORS = {
        'DEBUG': '\033[37m',       # White
        'INFO': '\033[32m',        # Green
        'WARNING': '\033[33m',     # Yellow
        'ERROR': '\033[31m',       # Red
        'CRITICAL': '\033[1;31m',  # Bold Red
        'NAME': '\033[36m'         # Cyan
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        name_color = self.COLORS['NAME']
        record.levelname = f"{log_color}{record.levelname:<8}{self.RESET}"
        record.name = f"{name_color}{record.name}{self.RESET}"
        record.msg = f"{log_color}{record.msg}{self.RESET}"
        return super().format(record)


def setup_logging():
    """
    Sets up the logging configuration for the FBI Bot API.

    Reads the logging configuration from a YAML file and applies it.
    Creates necessary log directories and updates file paths.
    """
    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        config_file = Path("logging_config.yaml")
        if config_file.exists():
            with open(config_file, 'r') as file:
                config = yaml.safe_load(file.read())

            config['handlers']['rotating_file']['filename'] = str(log_dir / 'api.log')
            config['handlers']['error_file']['filename'] = str(log_dir / 'errors.log')

            logging.config.dictConfig(config)

    except yaml.YAMLError as e:
        logging.error(f"Error parsing logging YAML file: {e}")
    except Exception as e:
        logging.error(f"Unexpected error in logging configuration: {e}")


settings = Settings()

setup_logging()
