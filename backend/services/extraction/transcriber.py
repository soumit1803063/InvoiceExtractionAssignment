import base64
from io import BytesIO
from typing import Optional

from markitdown import MarkItDown
from markitdown._stream_info import StreamInfo
from openai import OpenAI

from ...core import ErrorCode, ErrorMessage, IntakeError, MdPage, Utils
from ...settings import Settings


class MarkitdownTranscriber:

    def __init__(self) -> None:
        self._converter: Optional[MarkItDown] = None

    @property
    def model_id(self) -> str:
        return ""

    def to_markdown(self, page: MdPage) -> str:
        if self._converter is None:
            self._converter = MarkItDown()
        stream_info = StreamInfo(
            mimetype=page.media_type,
            extension=Utils.suffix_for_media_type(page.media_type),
        )
        try:
            result = self._converter.convert_stream(BytesIO(page.content), stream_info=stream_info)
        except Exception as error:
            raise IntakeError(ErrorCode.TRANSCRIPTION_FAILED, str(error)) from error
        markdown = (result.text_content or "").strip()
        if not markdown:
            raise IntakeError(ErrorCode.TRANSCRIPTION_FAILED, ErrorMessage.EMPTY_TRANSCRIPTION)
        return markdown


class VisionTranscriber:

    def __init__(self, settings: Settings, model_id: str) -> None:
        self._model_id = model_id
        self._api_key = settings.openrouter_api_key
        self._prompt = settings.transcribe_prompt
        self._client = OpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            timeout=settings.model_timeout_seconds,
        )

    @property
    def model_id(self) -> str:
        return self._model_id

    def to_markdown(self, page: MdPage) -> str:
        if not self._api_key:
            raise IntakeError(ErrorCode.TRANSCRIPTION_FAILED, ErrorMessage.NO_TRANSCRIBER)
        image = base64.b64encode(page.content).decode("ascii")
        try:
            answer = self._client.chat.completions.create(
                model=self._model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{page.media_type};base64,{image}"},
                            },
                        ],
                    }
                ],
            )
        except Exception as error:
            raise IntakeError(
                ErrorCode.TRANSCRIPTION_FAILED, Utils.mask_secrets(error, (self._api_key,))
            ) from error
        markdown = (answer.choices[0].message.content or "").strip()
        if not markdown:
            raise IntakeError(ErrorCode.TRANSCRIPTION_FAILED, ErrorMessage.EMPTY_TRANSCRIPTION)
        return markdown


class Transcribers:

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def openrouter_gemma_31b(self) -> VisionTranscriber:
        return VisionTranscriber(self._settings, self._settings.openrouter_gemma_31b)

    def openrouter_nemotron_omni(self) -> VisionTranscriber:
        return VisionTranscriber(self._settings, self._settings.openrouter_nemotron_omni)

    def openrouter_gemma_26b(self) -> VisionTranscriber:
        return VisionTranscriber(self._settings, self._settings.openrouter_gemma_26b)

    def openrouter_nemotron_vl(self) -> VisionTranscriber:
        return VisionTranscriber(self._settings, self._settings.openrouter_nemotron_vl)

    def plain(self) -> MarkitdownTranscriber:
        return MarkitdownTranscriber()

    def model_chain(self) -> tuple[VisionTranscriber, ...]:
        if not self._settings.openrouter_api_key:
            return ()
        return (
            self.openrouter_gemma_31b(),
            self.openrouter_nemotron_omni(),
            self.openrouter_gemma_26b(),
            self.openrouter_nemotron_vl(),
        )
