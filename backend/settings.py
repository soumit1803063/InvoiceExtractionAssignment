from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, StrictStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    project_root: Path = Path(".")
    invoice_directory: Path = Field(default=Path("public/storage"), alias="INVOICE_DIR")
    database_path: Path = Field(
        default=Path("public/database/documents.sqlite3"), alias="DATABASE_PATH"
    )
    frontend_directory: Path = Field(default=Path("frontend/dist"), alias="FRONTEND_DIR")
    prompts_directory: Path = Field(default=Path("backend/core/prompts"), alias="PROMPTS_DIR")
    skills_directory: Path = Field(default=Path("backend/core/skills"), alias="SKILLS_DIR")

    host: StrictStr = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    accounting_base_url: StrictStr = Field(
        default="http://127.0.0.1:8080", alias="ACCOUNTING_API_BASE_URL"
    )
    accounting_api_key: StrictStr = Field(default="", alias="ACCOUNTING_API_KEY")
    accounting_timeout_seconds: int = Field(default=10, alias="ACCOUNTING_API_TIMEOUT_SECONDS")

    openrouter_api_key: StrictStr = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: StrictStr = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )
    gemini_api_key: StrictStr = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: StrictStr = Field(default="gemini-3.7-flash", alias="GEMINI_MODEL")

    openrouter_inkling: StrictStr = Field(
        default="thinkingmachines/inkling:free", alias="OPENROUTER_INKLING"
    )
    openrouter_gemma: StrictStr = Field(
        default="google/gemma-4-31b-it:free", alias="OPENROUTER_GEMMA"
    )
    openrouter_nemotron_omni: StrictStr = Field(
        default="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        alias="OPENROUTER_NEMOTRON_OMNI",
    )
    openrouter_nemotron_vl: StrictStr = Field(
        default="nvidia/nemotron-nano-12b-v2-vl:free", alias="OPENROUTER_NEMOTRON_VL"
    )
    openrouter_nemotron_super: StrictStr = Field(
        default="nvidia/nemotron-3-super-120b-a12b:free", alias="OPENROUTER_NEMOTRON_SUPER"
    )
    openrouter_glm: StrictStr = Field(default="z-ai/glm-5.2:free", alias="OPENROUTER_GLM")
    openrouter_nemotron_nano: StrictStr = Field(
        default="nvidia/nemotron-nano-9b-v2:free", alias="OPENROUTER_NEMOTRON_NANO"
    )
    openrouter_dots_note: StrictStr = Field(
        default="dots-studio/dots-3-note-preview:free", alias="OPENROUTER_DOTS_NOTE"
    )

    render_dpi: int = Field(default=600, alias="RENDER_DPI")
    model_timeout_seconds: int = Field(default=180, alias="MODEL_TIMEOUT_SECONDS")
    orientation_enabled: bool = Field(default=True, alias="ORIENTATION_ENABLED")
    tesseract_path: StrictStr = Field(default="", alias="TESSERACT_PATH")

    @property
    def transcribe_prompt(self) -> str:
        return (self.prompts_directory / "transcribe.md").read_text(encoding="utf-8")

    @property
    def structure_prompt(self) -> str:
        return (self.prompts_directory / "structure.md").read_text(encoding="utf-8")


def _resolve_against_root(root: Path, value: Path) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (root / candidate).resolve()


def load_settings(project_root: Path) -> Settings:
    root = Path(project_root).resolve()
    load_dotenv(root / ".env", encoding="utf-8")
    settings = Settings()
    return settings.model_copy(
        update={
            "project_root": root,
            "invoice_directory": _resolve_against_root(root, settings.invoice_directory),
            "database_path": _resolve_against_root(root, settings.database_path),
            "frontend_directory": _resolve_against_root(root, settings.frontend_directory),
            "prompts_directory": _resolve_against_root(root, settings.prompts_directory),
            "skills_directory": _resolve_against_root(root, settings.skills_directory),
            "accounting_base_url": settings.accounting_base_url.rstrip("/").replace(
                "//localhost", "//127.0.0.1", 1
            ),
        }
    )
