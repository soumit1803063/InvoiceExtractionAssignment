from io import BytesIO
from typing import Optional

from markitdown import MarkItDown
from markitdown._stream_info import StreamInfo
from openai import OpenAI

from ...core import ErrorCode, ErrorMessage, IntakeError, MdPageImage, Utils
from ...settings import Settings


class MarkitdownTranscriber:

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.openrouter_base_url
        self._api_key = settings.openrouter_api_key
        self._model_id = settings.transcription_model
        self._timeout_seconds = settings.model_timeout_seconds
        self._prompt = settings.transcribe_prompt
        self._converter: Optional[MarkItDown] = None

    def _reader(self) -> MarkItDown:
        if self._converter is None:
            self._converter = MarkItDown(
                llm_client=OpenAI(
                    base_url=self._base_url,
                    api_key=self._api_key,
                    timeout=self._timeout_seconds,
                ),
                llm_model=self._model_id,
                llm_prompt=self._prompt,
            )
        return self._converter

    def to_markdown(self, page: MdPageImage) -> str:
        if not self._api_key:
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
