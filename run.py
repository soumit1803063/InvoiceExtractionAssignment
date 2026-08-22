import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import venv
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
VENV_DIRECTORY = PROJECT_ROOT / ".venv"
ACCOUNTING_API_SCRIPT = PROJECT_ROOT / "accounting_api.py"
ENVIRONMENT_FILE = PROJECT_ROOT / ".env"

BOOTSTRAP_MARKER = "INVOICE_INTAKE_BOOTSTRAPPED"
REQUIRED_PACKAGES = ("fastapi", "uvicorn", "pydantic_settings", "sqlmodel")
MINIMUM_PYTHON = (3, 10)

HEALTH_PATH = "/health"
HEALTH_TIMEOUT_SECONDS = 30
HEALTH_POLL_SECONDS = 0.5
SHUTDOWN_GRACE_SECONDS = 5

EXIT_SUCCESS = 0
EXIT_UNSUPPORTED_PYTHON = 1
EXIT_INSTALL_FAILED = 2


class Console:

    @staticmethod
    def section(message: str) -> None:
        print("", flush=True)
        print(message, flush=True)

    @staticmethod
    def line(message: str) -> None:
        print("  " + message, flush=True)


class Environment:

    @staticmethod
    def venv_python() -> Path:
        if os.name == "nt":
            return VENV_DIRECTORY / "Scripts" / "python.exe"
        return VENV_DIRECTORY / "bin" / "python"

    @staticmethod
    def packages_importable() -> bool:
        from importlib.util import find_spec

        return all(find_spec(package) is not None for package in REQUIRED_PACKAGES)

    @staticmethod
    def create_virtual_environment() -> None:
        if Environment.venv_python().is_file():
            Console.line("Reusing the virtual environment in .venv")
            return
        Console.line("Creating a virtual environment in .venv")
        venv.EnvBuilder(with_pip=True, upgrade_deps=False).create(VENV_DIRECTORY)

    @staticmethod
    def install_requirements() -> bool:
        Console.line("Installing dependencies from requirements.txt (this takes a few minutes)")
        completed = subprocess.run(
            [
                str(Environment.venv_python()),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--quiet",
                "-r",
                str(REQUIREMENTS_FILE),
            ],
            check=False,
        )
        return completed.returncode == 0

    @staticmethod
    def relaunch_inside_virtual_environment() -> None:
        Console.line("Starting the application inside .venv")
        environment = dict(os.environ, **{BOOTSTRAP_MARKER: "1"})
        python = str(Environment.venv_python())
        if os.name == "nt":
            raise SystemExit(
                subprocess.run([python, str(Path(__file__).resolve())], env=environment).returncode
            )
        os.execve(python, [python, str(Path(__file__).resolve())], environment)

    @staticmethod
    def prepare() -> None:
        if Environment.packages_importable():
            return
        if os.environ.get(BOOTSTRAP_MARKER):
            Console.section("Dependencies are still missing after installing them.")
            Console.line("Install them manually with: pip install -r requirements.txt")
            raise SystemExit(EXIT_INSTALL_FAILED)
        Console.section("First run: setting up everything this project needs.")
        Environment.create_virtual_environment()
        if not Environment.install_requirements():
            Console.section("The dependencies could not be installed.")
            Console.line("Install them manually with: pip install -r requirements.txt")
            raise SystemExit(EXIT_INSTALL_FAILED)
        Environment.relaunch_inside_virtual_environment()


class AccountingApi:

    @staticmethod
    def is_answering(base_url: str) -> bool:
        try:
            with urllib.request.urlopen(base_url + HEALTH_PATH, timeout=2) as response:
                return response.status == 200
        except (urllib.error.URLError, OSError):
            return False

    @staticmethod
    def start(base_url: str) -> "subprocess.Popen[bytes]":
        port = urlparse(base_url).port
        Console.line(f"Starting the accounting system API on port {port}")
        return subprocess.Popen(
            [sys.executable, str(ACCOUNTING_API_SCRIPT)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @staticmethod
    def wait_until_answering(base_url: str) -> bool:
        deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if AccountingApi.is_answering(base_url):
                return True
            time.sleep(HEALTH_POLL_SECONDS)
        return False

    @staticmethod
    def stop(process: "subprocess.Popen[bytes]") -> None:
        process.terminate()
        try:
            process.wait(timeout=SHUTDOWN_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()


class Application:

    @staticmethod
    def run() -> int:
        if sys.version_info < MINIMUM_PYTHON:
            Console.section(
                f"Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or newer is required, "
                f"but this is {sys.version_info.major}.{sys.version_info.minor}."
            )
            return EXIT_UNSUPPORTED_PYTHON

        Environment.prepare()

        import uvicorn

        from backend.app import create_app
        from backend.core import Utils
        from backend.services.extraction import SUPPORTED_SUFFIXES
        from backend.settings import load_settings

        settings = load_settings(PROJECT_ROOT)
        accounting_process = None
        if AccountingApi.is_answering(settings.accounting_base_url):
            Console.line("The accounting system API is already running; leaving it alone")
        else:
            accounting_process = AccountingApi.start(settings.accounting_base_url)
            if not AccountingApi.wait_until_answering(settings.accounting_base_url):
                Console.line("The accounting system API did not answer; registration is disabled")

        if not ENVIRONMENT_FILE.is_file():
            Console.line("No .env file found; add your OPENROUTER_API_KEY to read invoices")
        invoice_count = len(
            list(Utils.iter_files_with_suffixes(settings.invoice_directory, SUPPORTED_SUFFIXES))
        )
        Console.line(f"Reading {invoice_count} invoices from {settings.invoice_directory}")
        if not settings.frontend_directory.is_dir():
            Console.line("No built frontend found; the REST API is still served")

        Console.section(f"Open http://{settings.host}:{settings.port} in your browser")
        print("", flush=True)
        try:
            uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
        finally:
            if accounting_process is not None:
                AccountingApi.stop(accounting_process)
        return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(Application.run())
