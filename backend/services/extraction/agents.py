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

    def openrouter_nemotron_super(self) -> Agent:
        return Agent(
            model=OpenRouter(
                id=self._settings.openrouter_nemotron_super,
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

    def openrouter_glm(self) -> Agent:
        return Agent(
            model=OpenRouter(
                id=self._settings.openrouter_glm,
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

    def openrouter_nemotron_nano(self) -> Agent:
        return Agent(
            model=OpenRouter(
                id=self._settings.openrouter_nemotron_nano,
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

    def openrouter_dots_note(self) -> Agent:
        return Agent(
            model=OpenRouter(
                id=self._settings.openrouter_dots_note,
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

    def fallback_chain(self) -> tuple[Agent, ...]:
        agents = []
        if self._settings.openrouter_api_key:
            agents.append(self.openrouter_nemotron_super())
            agents.append(self.openrouter_glm())
            agents.append(self.openrouter_nemotron_nano())
            agents.append(self.openrouter_dots_note())
        if self._settings.gemini_api_key:
            agents.append(self.gemini())
        return tuple(agents)
