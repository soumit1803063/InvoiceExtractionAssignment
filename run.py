import sys
from pathlib import Path

import uvicorn

from backend.core import ErrorCode, IntakeError, Utils
from backend.controllers.controller import create_app
from backend.services.accounting_service import HttpAccountingGateway
from backend.services.extraction import SUPPORTED_SUFFIXES
from backend.settings import Settings, SettingsLoader

PROJECT_ROOT = Path(__file__).resolve().parent
ACCOUNTING_API_SCRIPT = "accounting_api.py"
EXIT_SUCCESS = 0
EXIT_ACCOUNTING_API_UNREACHABLE = 1


class StartupReport:

    @staticmethod
    def accounting_api_instructions(base_url: str) -> None:
        print("")
        print("The accounting API is not answering at " + base_url)
        print("Start it yourself in a separate terminal, then run this command again:")
        print("")
        print("    python " + ACCOUNTING_API_SCRIPT)
        print("")
        print("It must keep running in that terminal. This command never starts or stops it,")
        print("because a second copy would fight the first one for the same port.")
        print("")

    @staticmethod
    def unauthorized_warning(base_url: str) -> None:
        print("")
        print("The accounting API at " + base_url + " rejected the configured API key.")
        print("Set ACCOUNTING_API_KEY in .env to the key the accounting system expects.")
        print("Invoices can still be read and reviewed, but none of them can be registered.")
        print("")

    @staticmethod
    def invoice_directory(invoice_directory: Path, invoice_count: int) -> None:
        if invoice_count > 0:
            print("Reading " + str(invoice_count) + " invoices from " + str(invoice_directory))
            return
        print("")
        print("No invoices were found in " + str(invoice_directory))
        print("Put the invoice files (.pdf, .jpg, .jpeg, .png) in that folder,")
        print("or point INVOICE_DIR in .env at the folder that holds them.")
        print("")

    @staticmethod
    def frontend_build_instructions(frontend_directory: Path) -> None:
        print("")
        print("No built frontend was found at " + str(frontend_directory))
        print("The REST API is still served. To get the review screen, build the frontend:")
        print("")
        print("    cd frontend")
        print("    npm install")
        print("    npm run build")
        print("")


class Application:

    @staticmethod
    def count_invoices(settings: Settings) -> int:
        return len(list(Utils.iter_files_with_suffixes(settings.invoice_directory, SUPPORTED_SUFFIXES)))

    @staticmethod
    def run() -> int:
        settings = SettingsLoader.load(PROJECT_ROOT)
        gateway = HttpAccountingGateway(
            settings.accounting_base_url,
            settings.accounting_api_key,
            settings.accounting_timeout_seconds,
        )
        if not gateway.is_reachable():
            StartupReport.accounting_api_instructions(settings.accounting_base_url)
            return EXIT_ACCOUNTING_API_UNREACHABLE
        try:
            gateway.fetch_partners()
        except IntakeError as error:
            if error.code == ErrorCode.UNAUTHORIZED:
                StartupReport.unauthorized_warning(settings.accounting_base_url)
        StartupReport.invoice_directory(settings.invoice_directory, Application.count_invoices(settings))
        if not settings.frontend_directory.is_dir():
            StartupReport.frontend_build_instructions(settings.frontend_directory)
        application = create_app(settings)
        print("")
        print("Invoice intake is starting on http://" + settings.host + ":" + str(settings.port))
        print("")
        uvicorn.run(application, host=settings.host, port=settings.port)
        return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(Application.run())
