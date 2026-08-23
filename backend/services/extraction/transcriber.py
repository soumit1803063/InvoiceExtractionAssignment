from io import BytesIO
from typing import Optional

from markitdown import MarkItDown
from markitdown._stream_info import StreamInfo

from ...core import ErrorCode, ErrorMessage, IntakeError, MdPage, Utils


class MarkitdownTranscriber:

    def __init__(self) -> None:
        self._converter: Optional[MarkItDown] = None

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
