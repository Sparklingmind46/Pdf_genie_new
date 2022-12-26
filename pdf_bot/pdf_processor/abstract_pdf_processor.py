from typing import Type

from pdf_bot.file_processor import AbstractFileProcessor
from pdf_bot.file_task import FileTaskService
from pdf_bot.language import LanguageService
from pdf_bot.models import TaskData
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.telegram_internal import TelegramService


class AbstractPdfProcessor(AbstractFileProcessor):
    def __init__(
        self,
        file_task_service: FileTaskService,
        pdf_service: PdfService,
        telegram_service: TelegramService,
        language_service: LanguageService,
        bypass_init_check: bool = False,
    ) -> None:
        self.pdf_service = pdf_service
        super().__init__(
            file_task_service, telegram_service, language_service, bypass_init_check
        )

    @classmethod
    def get_task_data_list(cls) -> list[TaskData]:
        return []

    @property
    def generic_error_types(self) -> set[Type[Exception]]:
        return {PdfServiceError}
