from typing import Callable, Type

from telegram import Update
from telegram.ext import CallbackContext

from pdf_bot.file_processor import AbstractFileProcessor
from pdf_bot.file_task import FileTaskService
from pdf_bot.language_new import LanguageService
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.telegram_internal import TelegramService

ErrorHandlerType = Callable[[Update, CallbackContext, Exception, str, str], str]


class AbstractPDFProcessor(AbstractFileProcessor):
    def __init__(
        self,
        file_task_service: FileTaskService,
        pdf_service: PdfService,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.pdf_service = pdf_service
        super().__init__(file_task_service, telegram_service, language_service)

    @property
    def generic_error_types(self) -> set[Type[Exception]]:
        return {PdfServiceError}