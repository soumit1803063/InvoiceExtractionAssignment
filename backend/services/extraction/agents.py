from agno.agent import Agent
from agno.guardrails import PromptInjectionGuardrail
from agno.models.google import Gemini
from agno.models.openrouter import OpenRouter
from agno.skills import LocalSkills, Skills

from ...core import AiInvoice
from ...settings import Settings


class Agents:

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._instructions = settings.structure_prompt
        self._skills = Skills(loaders=[LocalSkills(str(settings.skills_directory))])

    def openrouter(self) -> Agent:
        return Agent(
            model=OpenRouter(
                id=self._settings.structuring_model,
                api_key=self._settings.openrouter_api_key,
                timeout=self._settings.model_timeout_seconds,
            ),
            instructions=self._instructions,
            skills=self._skills,
            output_schema=AiInvoice,
            pre_hooks=[PromptInjectionGuardrail()],
            markdown=False,
            telemetry=False,
        )

    def gemini(self) -> Agent:
        return Agent(
            model=Gemini(
                id=self._settings.gemini_model,
                api_key=self._settings.gemini_api_key,
                timeout=self._settings.model_timeout_seconds,
            ),
            instructions=self._instructions,
            skills=self._skills,
            output_schema=AiInvoice,
            pre_hooks=[PromptInjectionGuardrail()],
            markdown=False,
            telemetry=False,
        )
