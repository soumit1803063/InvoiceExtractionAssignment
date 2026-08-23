import io
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests
from PIL import Image, ImageOps

from ...core import MdPage, Utils
from ...settings import Settings

WINDOWS_TESSERACT_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)
POSIX_TESSERACT_PATHS = (
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
    "/opt/bin/tesseract",
    "/opt/homebrew/bin/tesseract",
)
TESSERACT_EXECUTABLE = "tesseract"

OSD_DATA_FILE = "osd.traineddata"
OSD_DATA_URL = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/osd.traineddata"
TESSDATA_DIRECTORY = "tessdata"
TESSDATA_PREFIX_VARIABLE = "TESSDATA_PREFIX"
POSIX_TESSDATA_PATHS = (
    Path("/usr/share/tesseract-ocr/5/tessdata"),
    Path("/usr/share/tesseract-ocr/4.00/tessdata"),
    Path("/usr/share/tessdata"),
)
TOOLS_RELATIVE_PATH = "data/tools"
DOWNLOAD_TIMEOUT_SECONDS = 30
MINIMUM_DATA_FILE_BYTES = 1024

OSD_ARGUMENTS = ("stdout", "--psm", "0")
OSD_TIMEOUT_SECONDS = 60
ROTATION_PATTERN = re.compile(r"Orientation in degrees:\s*(\d+)")
CONFIDENCE_PATTERN = re.compile(r"Orientation confidence:\s*([\d.]+)")

TRUSTED_CONFIDENCE = 3.0
UPRIGHT = 0
QUARTER_TURNS = {
    90: Image.Transpose.ROTATE_90,
    180: Image.Transpose.ROTATE_180,
    270: Image.Transpose.ROTATE_270,
}
ANALYSIS_MAX_EDGE = 2000
EXIF_ORIENTATION_TAG = 0x0112
UNSET_EXIF_ORIENTATIONS = (0, 1)


class OrientationCorrector:

    def __init__(self, settings: Settings) -> None:
        self._command = self._prepare(settings) if settings.orientation_enabled else ""

    def upright(self, page: MdPage) -> MdPage:
        try:
            return self._corrected(page)
        except Exception:
            return page

    def _corrected(self, page: MdPage) -> MdPage:
        with Image.open(io.BytesIO(page.content)) as opened:
            opened.load()
            exif_orientation = opened.getexif().get(EXIF_ORIENTATION_TAG, 1)
            needs_exif = exif_orientation not in UNSET_EXIF_ORIENTATIONS
            image = ImageOps.exif_transpose(opened) if needs_exif else opened
            degrees = self._detect(image) if self._command else UPRIGHT
            if not needs_exif and degrees == UPRIGHT:
                return page
            upright = image if degrees == UPRIGHT else image.transpose(QUARTER_TURNS[degrees])
            return page.model_copy(
                update={
                    "content": Utils.encode_frame_as_png(upright),
                    "media_type": Utils.PNG_MEDIA_TYPE,
                }
            )

    def _detect(self, image: Image.Image) -> int:
        analysis = self._analysis_copy(image)
        try:
            degrees, confidence = self._read_orientation(analysis)
            return degrees if confidence >= TRUSTED_CONFIDENCE else UPRIGHT
        finally:
            if analysis is not image:
                analysis.close()

    def _read_orientation(self, image: Image.Image) -> tuple[int, float]:
        with tempfile.TemporaryDirectory(prefix="orientation_") as directory:
            source = Path(directory) / "page.png"
            image.save(source, format=Utils.PNG_FORMAT, compress_level=Utils.PNG_COMPRESS_LEVEL)
            completed = subprocess.run(
                [self._command, str(source), *OSD_ARGUMENTS],
                capture_output=True,
                text=True,
                timeout=OSD_TIMEOUT_SECONDS,
                check=False,
            )
        return self._parse_rotation(completed.stdout), self._parse_confidence(completed.stdout)

    @staticmethod
    def _parse_rotation(output: str) -> int:
        found = ROTATION_PATTERN.search(output)
        degrees = int(found.group(1)) % 360 if found else UPRIGHT
        return degrees if degrees in QUARTER_TURNS else UPRIGHT

    @staticmethod
    def _parse_confidence(output: str) -> float:
        found = CONFIDENCE_PATTERN.search(output)
        return float(found.group(1)) if found else 0.0

    @staticmethod
    def _analysis_copy(image: Image.Image) -> Image.Image:
        longest_edge = max(image.width, image.height)
        if longest_edge <= ANALYSIS_MAX_EDGE:
            return image
        scale = ANALYSIS_MAX_EDGE / longest_edge
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        return image.resize(size, Image.Resampling.LANCZOS)

    def _prepare(self, settings: Settings) -> str:
        try:
            command = self._locate(settings.tesseract_path)
            if not command:
                return ""
            self._publish_on_path(command)
            return command if self._ensure_osd_data(settings, command) else ""
        except Exception:
            return ""

    @staticmethod
    def _locate(configured: str) -> str:
        if configured and Path(configured).is_file():
            return str(Path(configured))
        found = shutil.which(TESSERACT_EXECUTABLE)
        if found:
            return found
        candidates = WINDOWS_TESSERACT_PATHS if os.name == "nt" else POSIX_TESSERACT_PATHS
        return next((path for path in candidates if Path(path).is_file()), "")

    @staticmethod
    def _publish_on_path(command: str) -> None:
        directory = str(Path(command).parent)
        entries = os.environ.get("PATH", "").split(os.pathsep)
        if directory not in entries:
            os.environ["PATH"] = os.pathsep.join([directory, *entries])

    @staticmethod
    def _osd_data_is_installed(command: str) -> bool:
        binary = Path(command).parent
        configured = os.environ.get(TESSDATA_PREFIX_VARIABLE, "")
        candidates = [
            binary / TESSDATA_DIRECTORY,
            binary.parent / "share" / TESSDATA_DIRECTORY,
            binary.parent / "share" / "tesseract-ocr" / TESSDATA_DIRECTORY,
            *POSIX_TESSDATA_PATHS,
        ]
        if configured:
            candidates.insert(0, Path(configured))
        return any((Path(directory) / OSD_DATA_FILE).is_file() for directory in candidates)

    @staticmethod
    def _ensure_osd_data(settings: Settings, command: str) -> bool:
        if OrientationCorrector._osd_data_is_installed(command):
            return True
        target = Path(settings.project_root) / TOOLS_RELATIVE_PATH / TESSDATA_DIRECTORY
        destination = target / OSD_DATA_FILE
        if not destination.is_file():
            target.mkdir(parents=True, exist_ok=True)
            response = requests.get(OSD_DATA_URL, timeout=DOWNLOAD_TIMEOUT_SECONDS)
            response.raise_for_status()
            if len(response.content) < MINIMUM_DATA_FILE_BYTES:
                return False
            destination.write_bytes(response.content)
        os.environ[TESSDATA_PREFIX_VARIABLE] = str(target)
        return True
