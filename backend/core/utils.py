import io
import threading
import json
import re
import unicodedata
from collections.abc import Iterator, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from itertools import product
from pathlib import Path
from typing import Optional, Union

import pypdfium2

PDFIUM_LOCK = threading.RLock()
from PIL import Image
PathLike = Union[Path, str]


class Utils:


    WHITESPACE_RUN = re.compile("[ \t\u3000\u00a0]+")
    SURROGATE_CHARACTERS = re.compile("[\ud800-\udfff]")

    @staticmethod
    def normalize_full_width_to_ascii(text: object) -> str:
        if text is None:
            return ""
        return unicodedata.normalize("NFKC", str(text))

    @staticmethod
    def collapse_whitespace(text: Optional[str]) -> str:
        return Utils.WHITESPACE_RUN.sub(" ", text or "").strip()

    @staticmethod
    def remove_surrogate_characters(text: Optional[str]) -> Optional[str]:
        if text is None:
            return None
        return Utils.SURROGATE_CHARACTERS.sub("", str(text))

    @staticmethod
    def normalize_display_text(text: object) -> str:
        return Utils.collapse_whitespace(
            Utils.remove_surrogate_characters(Utils.normalize_full_width_to_ascii(text))
        )

    @staticmethod
    def remove_surrogates_from_payload(value: object) -> object:
        if isinstance(value, str):
            return Utils.remove_surrogate_characters(value)
        if isinstance(value, dict):
            return {
                key: Utils.remove_surrogates_from_payload(item) for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [Utils.remove_surrogates_from_payload(item) for item in value]
        return value

    @staticmethod
    def drop_none_values(
        mapping: dict[str, object], keys_allowing_none: Sequence[str] = ()
    ) -> dict[str, object]:
        return {
            key: value
            for key, value in mapping.items()
            if value is not None or key in keys_allowing_none
        }

    NEGATIVE_LEADING_MARKS = ("△", "▲", "−", "-")
    LEDGER_EVEN_SUFFIX = "-"
    CURRENCY_MARKS = ("¥", "￥", "円", "\\")
    GROUPED_INTEGER = re.compile(r"^\d{1,3}(?:,\d{3})+$")
    UNGROUPED_INTEGER = re.compile(r"^\d+$")
    ZERO_FRACTION = re.compile(r"\.0+$")
    PERCENT_VALUE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
    
    @staticmethod
    def _strip_negative_marker(text: str) -> tuple[str, bool]:
        for mark in Utils.NEGATIVE_LEADING_MARKS:
            if text.startswith(mark):
                return text[len(mark) :].strip(), True
        if text.startswith("(") and text.endswith(")"):
            return text[1:-1].strip(), True
        return text, False

    @staticmethod
    def _parse_integral_digits(text: str) -> Optional[int]:
        without_fraction = Utils.ZERO_FRACTION.sub("", text) if "." in text else text
        if not Utils.GROUPED_INTEGER.match(without_fraction) and not Utils.UNGROUPED_INTEGER.match(
            without_fraction
        ):
            return None
        try:
            return int(Decimal(without_fraction.replace(",", "")))
        except InvalidOperation:
            return None

    @staticmethod
    def parse_amount(value: object) -> Optional[int]:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value) if float(value).is_integer() else None
        text = Utils.normalize_full_width_to_ascii(value).strip()
        for mark in Utils.CURRENCY_MARKS:
            text = text.replace(mark, "")
        text = text.strip()
        if not text:
            return None
        text, is_negative = Utils._strip_negative_marker(text)
        if text.endswith(Utils.LEDGER_EVEN_SUFFIX):
            text = text[: -len(Utils.LEDGER_EVEN_SUFFIX)].strip()
        text = text.replace(" ", "")
        magnitude = Utils._parse_integral_digits(text)
        if magnitude is None:
            return None
        return -magnitude if is_negative else magnitude

    @staticmethod
    def parse_percent_value(text: object) -> Optional[int]:
        found = Utils.PERCENT_VALUE.search(Utils.normalize_full_width_to_ascii(text))
        if not found:
            return None
        try:
            percent = Decimal(found.group(1))
        except InvalidOperation:
            return None
        return int(percent) if percent == percent.to_integral_value() else None

    ERA_BASE_YEARS = {
        "令和": 2018,
        "平成": 1988,
        "昭和": 1925,
        "大正": 1911,
        "明治": 1867,
    }
    FIRST_YEAR_OF_ERA_CHARACTER = "元"
    _ERA_NAMES = "|".join(ERA_BASE_YEARS)
    ERA_KANJI_DATE = re.compile(
        rf"({_ERA_NAMES})\s*({FIRST_YEAR_OF_ERA_CHARACTER}|\d{{1,2}})\s*年\s*(\d{{1,2}})"
        r"\s*月\s*(\d{1,2})\s*日"
    )
    ERA_NUMERIC_DATE = re.compile(
        rf"({_ERA_NAMES})\s*({FIRST_YEAR_OF_ERA_CHARACTER}|\d{{1,2}})\s*[/.\-]\s*(\d{{1,2}})"
        r"\s*[/.\-]\s*(\d{1,2})"
    )
    GREGORIAN_KANJI_DATE = re.compile(
        r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
    )
    GREGORIAN_NUMERIC_DATE = re.compile(r"(\d{4})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{1,2})")
    ERA_PATTERNS = (ERA_KANJI_DATE, ERA_NUMERIC_DATE)
    GREGORIAN_PATTERNS = (GREGORIAN_KANJI_DATE, GREGORIAN_NUMERIC_DATE)

    @staticmethod
    def _to_iso_date(year: int, month: int, day: int) -> Optional[str]:
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None

    @staticmethod
    def _gregorian_year_of_era(era_name: str, era_year_text: str) -> int:
        era_year = (
            1 if era_year_text == Utils.FIRST_YEAR_OF_ERA_CHARACTER else int(era_year_text)
        )
        return Utils.ERA_BASE_YEARS[era_name] + era_year

    @staticmethod
    def parse_iso_date(value: Optional[str]) -> Optional[date]:
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def parse_japanese_date(value: object) -> Optional[str]:
        if value is None:
            return None
        text = Utils.normalize_full_width_to_ascii(value)
        if not text.strip():
            return None
        for pattern in Utils.ERA_PATTERNS:
            found = pattern.search(text)
            if found:
                return Utils._to_iso_date(
                    Utils._gregorian_year_of_era(found.group(1), found.group(2)),
                    int(found.group(3)),
                    int(found.group(4)),
                )
        for pattern in Utils.GREGORIAN_PATTERNS:
            found = pattern.search(text)
            if found:
                return Utils._to_iso_date(
                    int(found.group(1)), int(found.group(2)), int(found.group(3))
                )
        return None


    CODE_FENCE = re.compile(r"^```[A-Za-z]*\s*|\s*```$")

    @staticmethod
    def parse_first_json_object(text: str) -> Optional[object]:
        candidate = Utils.CODE_FENCE.sub("", text.strip())
        for start, character in enumerate(candidate):
            if character != "{":
                continue
            depth = 0
            inside_text = False
            escaped = False
            for index in range(start, len(candidate)):
                current = candidate[index]
                if inside_text:
                    if escaped:
                        escaped = False
                    elif current == "\\":
                        escaped = True
                    elif current == '"':
                        inside_text = False
                    continue
                if current == '"':
                    inside_text = True
                elif current == "{":
                    depth += 1
                elif current == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(candidate[start : index + 1])
                        except json.JSONDecodeError:
                            break
        return None

    @staticmethod
    def dump_json(value: object) -> str:
        return json.dumps(value, ensure_ascii=False)


    FILE_CHUNK_BYTES = 1 << 20
    MEDIA_TYPE_BY_SUFFIX = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }
    FALLBACK_MEDIA_TYPE = "application/octet-stream"
    TEXT_ENCODING = "utf-8"

    @staticmethod
    def media_type_for_path(path: PathLike) -> str:
        return Utils.MEDIA_TYPE_BY_SUFFIX.get(
            Path(path).suffix.lower(), Utils.FALLBACK_MEDIA_TYPE
        )

    PATH_SEPARATORS = ("/", "\\")
    UNSAFE_NAME_CHARACTERS = re.compile('[<>:"|?*]')
    FALLBACK_FILE_NAME = "upload"
    NAME_COLLISION_TEMPLATE = "{stem}-{index}{suffix}"
    MAX_NAME_COLLISIONS = 1000

    @staticmethod
    def safe_file_name(name: str) -> str:
        candidate = str(name or "")
        for separator in Utils.PATH_SEPARATORS:
            candidate = candidate.rsplit(separator, 1)[-1]
        candidate = "".join(character for character in candidate if character.isprintable())
        candidate = Utils.UNSAFE_NAME_CHARACTERS.sub("", candidate).strip(" .")
        return candidate or Utils.FALLBACK_FILE_NAME

    @staticmethod
    def unique_path(directory: PathLike, name: str) -> Path:
        root = Path(directory)
        candidate = root / Utils.safe_file_name(name)
        if not candidate.exists():
            return candidate
        for index in range(1, Utils.MAX_NAME_COLLISIONS):
            attempt = root / Utils.NAME_COLLISION_TEMPLATE.format(
                stem=candidate.stem, index=index, suffix=candidate.suffix
            )
            if not attempt.exists():
                return attempt
        return candidate

    @staticmethod
    def suffix_for_media_type(media_type: str) -> str:
        for suffix, known in Utils.MEDIA_TYPE_BY_SUFFIX.items():
            if known == media_type:
                return suffix
        return ""

    @staticmethod
    def iter_files_with_suffixes(directory: PathLike, suffixes: Sequence[str]) -> Iterator[Path]:
        root = Path(directory)
        if not root.is_dir():
            return
        for entry in sorted(root.iterdir()):
            if entry.is_file() and entry.suffix.lower() in suffixes:
                yield entry


    JPEG_MEDIA_TYPE = "image/jpeg"
    PNG_MEDIA_TYPE = "image/png"
    PDF_MEDIA_TYPE = "application/pdf"
    PNG_FORMAT = "PNG"
    PDF_POINTS_PER_INCH = 72
    DEFAULT_RENDER_DPI = 600
    PNG_COMPRESS_LEVEL = 1

    @staticmethod
    def read_bytes(path: PathLike) -> bytes:
        with open(path, "rb") as stream:
            return stream.read()

    @staticmethod
    def encode_frame_as_png(frame: Image.Image) -> bytes:
        buffer = io.BytesIO()
        frame.save(buffer, format=Utils.PNG_FORMAT, compress_level=Utils.PNG_COMPRESS_LEVEL)
        return buffer.getvalue()

    @staticmethod
    def iter_pdf_page_pngs(
        path: PathLike, dpi: int = DEFAULT_RENDER_DPI
    ) -> Sequence[bytes]:
        pages = []
        with PDFIUM_LOCK:
            document = pypdfium2.PdfDocument(str(path))
            try:
                for page_index in range(len(document)):
                    page = document[page_index]
                    bitmap = page.render(scale=dpi / Utils.PDF_POINTS_PER_INCH)
                    frame = bitmap.to_pil()
                    try:
                        pages.append(Utils.encode_frame_as_png(frame))
                    finally:
                        frame.close()
                        bitmap.close()
                        page.close()
            finally:
                document.close()
        return tuple(pages)

    MAX_EXHAUSTIVE_ITEMS = 12
    MAX_EXHAUSTIVE_GROUPS = 3

    @staticmethod
    def _sums_by_group(
        group_keys: Sequence[str], amounts: Sequence[int]
    ) -> list[tuple[str, int]]:
        codes = []
        totals = []
        for key, amount in zip(group_keys, amounts):
            if key in codes:
                totals[codes.index(key)] += amount
                continue
            codes.append(key)
            totals.append(amount)
        return sorted(zip(codes, totals))

    @staticmethod
    def find_unique_partition_matching_targets(
        amounts: Sequence[int], codes: Sequence[str], totals: Sequence[int]
    ) -> Optional[list[str]]:
        if not amounts or not codes:
            return None
        if len(amounts) > Utils.MAX_EXHAUSTIVE_ITEMS or len(codes) > Utils.MAX_EXHAUSTIVE_GROUPS:
            return None
        if sum(amounts) != sum(totals):
            return None
        target = sorted(zip(codes, totals))
        matches = []
        for candidate in product(codes, repeat=len(amounts)):
            if Utils._sums_by_group(candidate, amounts) == target:
                matches.append(candidate)
                if len(matches) > 1:
                    return None
        return list(matches[0]) if matches else None
