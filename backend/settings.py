from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from pydantic import BeforeValidator, Field, StrictBool, StrictInt, StrictStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_INVOICE_DIRECTORY = "invoices"
DEFAULT_ACCOUNTING_BASE_URL = "http://127.0.0.1:8080"
IPV6_AMBIGUOUS_HOST = "//localhost"
IPV4_LOOPBACK_HOST = "//127.0.0.1"
DEFAULT_OPENROUTER_INKLING = "thinkingmachines/inkling:free"
DEFAULT_OPENROUTER_GEMMA = "google/gemma-4-31b-it:free"
DEFAULT_OPENROUTER_NEMOTRON_OMNI = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
DEFAULT_OPENROUTER_NEMOTRON_VL = "nvidia/nemotron-nano-12b-v2-vl:free"
DEFAULT_OPENROUTER_NEMOTRON_SUPER = "nvidia/nemotron-3-super-120b-a12b:free"
DEFAULT_OPENROUTER_GLM = "z-ai/glm-5.2:free"
DEFAULT_OPENROUTER_NEMOTRON_NANO = "nvidia/nemotron-nano-9b-v2:free"
DEFAULT_OPENROUTER_DOTS_NOTE = "dots-studio/dots-3-note-preview:free"
DEFAULT_RENDER_DPI = 600
DEFAULT_MODEL_TIMEOUT_SECONDS = 180
DEFAULT_ACCOUNTING_TIMEOUT_SECONDS = 10
DATABASE_RELATIVE_PATH = "data/documents.sqlite3"
FRONTEND_RELATIVE_PATH = "frontend/dist"
PROMPTS_RELATIVE_PATH = "backend/core/prompts"
SKILLS_RELATIVE_PATH = "backend/core/skills"
TRANSCRIBE_PROMPT_NAME = "transcribe.md"
STRUCTURE_PROMPT_NAME = "structure.md"
DEFAULT_GEMINI_MODEL = "gemini-3.7-flash"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_ORIENTATION_ENABLED = True
ENVIRONMENT_FILE_NAME = ".env"
TEXT_ENCODING = "utf-8"


def coerce_integer(value: object) -> object:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return value


def coerce_boolean(value: object) -> object:
    if isinstance(value, str):
        text = value.strip().lower()
        if not text:
            return None
        return text in ("1", "true", "yes", "on")
    return value


EnvInt = Annotated[StrictInt, BeforeValidator(coerce_integer)]
EnvBool = Annotated[StrictBool, BeforeValidator(coerce_boolean)]


class Settings(BaseSettings):

    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    project_root: Path = Path(".")
    invoice_directory: Path = Field(default=Path(DEFAULT_INVOICE_DIRECTORY), alias="INVOICE_DIR")
    database_path: Path = Field(default=Path(DATABASE_RELATIVE_PATH), alias="DATABASE_PATH")
    frontend_directory: Path = Field(default=Path(FRONTEND_RELATIVE_PATH), alias="FRONTEND_DIR")
    prompts_directory: Path = Field(default=Path(PROMPTS_RELATIVE_PATH), alias="PROMPTS_DIR")
    skills_directory: Path = Field(default=Path(SKILLS_RELATIVE_PATH), alias="SKILLS_DIR")
    host: StrictStr = Field(default=DEFAULT_HOST, alias="HOST")
    port: EnvInt = Field(default=DEFAULT_PORT, alias="PORT")
    accounting_base_url: StrictStr = Field(default=DEFAULT_ACCOUNTING_BASE_URL, alias="ACCOUNTING_API_BASE_URL")
    accounting_api_key: StrictStr = Field(default="", alias="ACCOUNTING_API_KEY")
    accounting_timeout_seconds: EnvInt = Field(
        default=DEFAULT_ACCOUNTING_TIMEOUT_SECONDS, alias="ACCOUNTING_API_TIMEOUT_SECONDS"
    )
    openrouter_api_key: StrictStr = Field(default="", alias="OPENROUTER_API_KEY")
    gemini_api_key: StrictStr = Field(default="", alias="GEMINI_API_KEY")
    openrouter_base_url: StrictStr = Field(
        default=DEFAULT_OPENROUTER_BASE_URL, alias="OPENROUTER_BASE_URL"
    )
    gemini_model: StrictStr = Field(default=DEFAULT_GEMINI_MODEL, alias="GEMINI_MODEL")
    openrouter_nemotron_super: StrictStr = Field(
        default=DEFAULT_OPENROUTER_NEMOTRON_SUPER, alias="OPENROUTER_NEMOTRON_SUPER"
    )
    openrouter_glm: StrictStr = Field(default=DEFAULT_OPENROUTER_GLM, alias="OPENROUTER_GLM")
    openrouter_nemotron_nano: StrictStr = Field(
        default=DEFAULT_OPENROUTER_NEMOTRON_NANO, alias="OPENROUTER_NEMOTRON_NANO"
    )
    openrouter_dots_note: StrictStr = Field(
        default=DEFAULT_OPENROUTER_DOTS_NOTE, alias="OPENROUTER_DOTS_NOTE"
    )
    openrouter_inkling: StrictStr = Field(
        default=DEFAULT_OPENROUTER_INKLING, alias="OPENROUTER_INKLING"
    )
    openrouter_gemma: StrictStr = Field(default=DEFAULT_OPENROUTER_GEMMA, alias="OPENROUTER_GEMMA")
    openrouter_nemotron_omni: StrictStr = Field(
        default=DEFAULT_OPENROUTER_NEMOTRON_OMNI, alias="OPENROUTER_NEMOTRON_OMNI"
    )
    openrouter_nemotron_vl: StrictStr = Field(
        default=DEFAULT_OPENROUTER_NEMOTRON_VL, alias="OPENROUTER_NEMOTRON_VL"
    )
    render_dpi: EnvInt = Field(default=DEFAULT_RENDER_DPI, alias="RENDER_DPI")
    model_timeout_seconds: EnvInt = Field(
        default=DEFAULT_MODEL_TIMEOUT_SECONDS, alias="MODEL_TIMEOUT_SECONDS"
    )
    orientation_enabled: EnvBool = Field(
        default=DEFAULT_ORIENTATION_ENABLED, alias="ORIENTATION_ENABLED"
    )
    tesseract_path: StrictStr = Field(default="", alias="TESSERACT_PATH")

    @property
    def transcribe_prompt(self) -> str:
        return (self.prompts_directory / TRANSCRIBE_PROMPT_NAME).read_text(encoding=TEXT_ENCODING)

    @property
    def structure_prompt(self) -> str:
        return (self.prompts_directory / STRUCTURE_PROMPT_NAME).read_text(encoding=TEXT_ENCODING)


class SettingsLoader:

    @staticmethod
    def resolve_against_root(root: Path, value: Path) -> Path:
        candidate = Path(value).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        return (root / candidate).resolve()

    @staticmethod
    def prefer_ipv4_loopback(url: str) -> str:
        return url.replace(IPV6_AMBIGUOUS_HOST, IPV4_LOOPBACK_HOST, 1)

    @staticmethod
    def load(project_root: Path) -> Settings:
        root = Path(project_root).resolve()
        load_dotenv(root / ENVIRONMENT_FILE_NAME, encoding=TEXT_ENCODING)
        settings = Settings()
        return settings.model_copy(
            update={
                "project_root": root,
                "invoice_directory": SettingsLoader.resolve_against_root(root, settings.invoice_directory),
                "database_path": SettingsLoader.resolve_against_root(root, settings.database_path),
                "frontend_directory": SettingsLoader.resolve_against_root(root, settings.frontend_directory),
                "prompts_directory": SettingsLoader.resolve_against_root(root, settings.prompts_directory),
                "skills_directory": SettingsLoader.resolve_against_root(root, settings.skills_directory),
                "accounting_base_url": SettingsLoader.prefer_ipv4_loopback(
                    settings.accounting_base_url.rstrip("/")
                ),
            }
        )