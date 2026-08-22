from io import BytesIO
from typing import Optional

from markitdown import MarkItDown
from markitdown._stream_info import StreamInfo
from openai import OpenAI

from ...core import ErrorCode, ErrorMessage, IntakeError, MdPageImage, Utils
from ...settings import Settings


class MarkitdownTranscriber:

    def __init__(self, settings: Settings, model_id: str = "") -> None:
        self._base_url = settings.openrouter_base_url
        self._api_key = settings.openrouter_api_key
        self._model_id = model_id
        self._timeout_seconds = settings.model_timeout_seconds
        self._prompt = settings.transcribe_prompt
        self._converter: Optional[MarkItDown] = None

    @property
    def model_id(self) -> str:
        return self._model_id

    def to_markdown(self, page: MdPageImage) -> str:
        if self._model_id and not self._api_key:
            raise IntakeError(ErrorCode.TRANSCRIPTION_FAILED, ErrorMessage.NO_TRANSCRIBER)
        stream_info = StreamInfo(
            mimetype=page.media_type,
            extension=Utils.suffix_for_media_type(page.media_type),
        )
        try:
            result = self._reader().convert_stream(BytesIO(page.content), stream_info=stream_info)
        except Exception as error:
            raise IntakeError(
                ErrorCode.TRANSCRIPTION_FAILED, Utils.mask_secrets(error, (self._api_key,))
            ) from error
        markdown = (result.text_content or "").strip()
        if not markdown:
            raise IntakeError(ErrorCode.TRANSCRIPTION_FAILED, ErrorMessage.EMPTY_TRANSCRIPTION)
        return markdown

    def _reader(self) -> MarkItDown:
        if self._converter is None:
            self._converter = MarkItDown() if not self._model_id else MarkItDown(
                llm_client=OpenAI(
                    base_url=self._base_url,
                    api_key=self._api_key,
                    timeout=self._timeout_seconds,
                ),
                llm_model=self._model_id,
                llm_prompt=self._prompt,
            )
        return self._converter


class Transcribers:

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def openrouter_gemma_31b(self) -> MarkitdownTranscriber:
        return MarkitdownTranscriber(self._settings, self._settings.openrouter_gemma_31b)

    def openrouter_gemma_26b(self) -> MarkitdownTranscriber:
        return MarkitdownTranscriber(self._settings, self._settings.openrouter_gemma_26b)

    def openrouter_nemotron_omni(self) -> MarkitdownTranscriber:
        return MarkitdownTranscriber(self._settings, self._settings.openrouter_nemotron_omni)

    def openrouter_nemotron_vl(self) -> MarkitdownTranscriber:
        return MarkitdownTranscriber(self._settings, self._settings.openrouter_nemotron_vl)

    def plain(self) -> MarkitdownTranscriber:
        return MarkitdownTranscriber(self._settings)

    def model_chain(self) -> tuple[MarkitdownTranscriber, ...]:
        if not self._settings.openrouter_api_key:
            return ()
        return (
            self.openrouter_gemma_31b(),
            self.openrouter_nemotron_omni(),
            self.openrouter_gemma_26b(),
            self.openrouter_nemotron_vl(),
        )
