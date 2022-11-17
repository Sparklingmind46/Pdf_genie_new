from dataclasses import dataclass
from unittest.mock import ANY, MagicMock, call, patch

import pytest
from telegram import ChatAction, File, InlineKeyboardMarkup
from telegram.constants import MAX_FILESIZE_DOWNLOAD, MAX_FILESIZE_UPLOAD
from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.io import IOService
from pdf_bot.language_new import LanguageService
from pdf_bot.models import FileData
from pdf_bot.telegram_internal import (
    TelegramFileMimeTypeError,
    TelegramFileTooLargeError,
    TelegramImageNotFoundError,
    TelegramService,
)
from pdf_bot.telegram_internal.exceptions import TelegramUserDataKeyError
from tests.telegram_internal.telegram_test_mixin import TelegramTestMixin


class TestTelegramRService(TelegramTestMixin):
    IMG_MIME_TYPE = "image"
    PDF_MIME_TYPE = "pdf"
    FILE_PATH = "file_path"
    USER_DATA_KEY = "user_data_key"
    USER_DATA_VALUE = "user_data_value"

    def setup_method(self) -> None:
        super().setup_method()
        self.io_service = MagicMock(spec=IOService)
        self.language_service = MagicMock(spec=LanguageService)
        self.sut = TelegramService(
            self.io_service, self.language_service, bot=self.telegram_bot
        )

    def test_check_file_size(self) -> None:
        self.telegram_document.file_size = MAX_FILESIZE_DOWNLOAD
        self.sut.check_file_size(self.telegram_document)

    def test_check_file_size_too_large(self) -> None:
        self.telegram_document.file_size = MAX_FILESIZE_DOWNLOAD + 1
        with pytest.raises(TelegramFileTooLargeError):
            self.sut.check_file_size(self.telegram_document)

    def test_check_file_upload_size(self) -> None:
        with patch("pdf_bot.telegram_internal.telegram_service.os") as os:
            os.path.getsize.return_value = MAX_FILESIZE_UPLOAD
            self.sut.check_file_upload_size(self.FILE_PATH)

    def test_check_file_upload_size_too_large(self) -> None:
        with patch("pdf_bot.telegram_internal.telegram_service.os") as os:
            os.path.getsize.return_value = MAX_FILESIZE_UPLOAD + 1
            with pytest.raises(TelegramFileTooLargeError):
                self.sut.check_file_upload_size(self.FILE_PATH)

    def test_check_image_document(self) -> None:
        self.telegram_document.mime_type = self.IMG_MIME_TYPE
        self.telegram_document.file_size = MAX_FILESIZE_DOWNLOAD
        self.telegram_message.document = self.telegram_document

        actual = self.sut.check_image(self.telegram_message)

        assert actual == self.telegram_document

    def test_check_image_document_invalid_mime_type(self) -> None:
        self.telegram_document.mime_type = "clearly_invalid"
        self.telegram_message.document = self.telegram_document

        with pytest.raises(TelegramFileMimeTypeError):
            self.sut.check_image(self.telegram_message)

    def test_check_image_document_too_large(self) -> None:
        self.telegram_document.mime_type = self.IMG_MIME_TYPE
        self.telegram_document.file_size = MAX_FILESIZE_DOWNLOAD + 1
        self.telegram_message.document = self.telegram_document

        with pytest.raises(TelegramFileTooLargeError):
            self.sut.check_image(self.telegram_message)

    def test_check_image(self) -> None:
        self.telegram_photo_size.file_size = MAX_FILESIZE_DOWNLOAD
        self.telegram_message.document = None
        self.telegram_message.photo = [self.telegram_photo_size]

        actual = self.sut.check_image(self.telegram_message)

        assert actual == self.telegram_photo_size

    def test_check_image_not_found(self) -> None:
        self.telegram_message.document = None
        self.telegram_message.photo = []

        with pytest.raises(TelegramImageNotFoundError):
            self.sut.check_image(self.telegram_message)

    def test_check_image_too_large(self) -> None:
        self.telegram_photo_size.file_size = MAX_FILESIZE_DOWNLOAD + 1
        self.telegram_message.document = None
        self.telegram_message.photo = [self.telegram_photo_size]

        with pytest.raises(TelegramFileTooLargeError):
            self.sut.check_image(self.telegram_message)

    def test_check_pdf_document(self) -> None:
        self.telegram_document.mime_type = self.PDF_MIME_TYPE
        self.telegram_document.file_size = MAX_FILESIZE_DOWNLOAD
        self.telegram_message.document = self.telegram_document

        actual = self.sut.check_pdf_document(self.telegram_message)

        assert actual == self.telegram_document

    def test_check_pdf_document_invalid_mime_type(self) -> None:
        self.telegram_document.mime_type = "clearly_invalid"
        self.telegram_message.document = self.telegram_document

        with pytest.raises(TelegramFileMimeTypeError):
            self.sut.check_pdf_document(self.telegram_message)

    def test_check_pdf_document_too_large(self) -> None:
        self.telegram_document.mime_type = self.PDF_MIME_TYPE
        self.telegram_document.file_size = MAX_FILESIZE_DOWNLOAD + 1
        self.telegram_message.document = self.telegram_document

        with pytest.raises(TelegramFileTooLargeError):
            self.sut.check_pdf_document(self.telegram_message)

    def test_download_pdf_file(self) -> None:
        self.io_service.create_temp_pdf_file.return_value.__enter__.return_value = (
            self.FILE_PATH
        )
        self.telegram_bot.get_file.return_value = self.telegram_file

        with self.sut.download_pdf_file(self.telegram_file_id) as actual:
            assert actual == self.FILE_PATH
            self.telegram_bot.get_file.assert_called_with(self.telegram_file_id)
            self.telegram_file.download.assert_called_once_with(
                custom_path=self.FILE_PATH
            )

    @pytest.mark.parametrize("num_files", [1, 2, 5])
    def test_download_files(self, num_files: int) -> None:
        @dataclass
        class FileAndPath:
            file: File
            path: str

        file_ids: list[str] = []
        file_paths: list[str] = []
        files: dict[str, FileAndPath] = {}

        for i in range(num_files):
            file_id = f"file_id_{i}"
            file_path = f"file_path_{i}"
            file_ids.append(file_id)
            file_paths.append(file_path)

            file = MagicMock(spec=File)
            files[file_id] = FileAndPath(file, file_path)

        self.io_service.create_temp_files.return_value.__enter__.return_value = (
            file_paths
        )
        self.telegram_bot.get_file.side_effect = lambda file_id: files[file_id].file

        with self.sut.download_files(file_ids) as actual:
            assert actual == file_paths

            get_file_calls = [call(file_id) for file_id in file_ids]
            self.telegram_bot.get_file.assert_has_calls(get_file_calls)

            for file_and_path in files.values():
                file_and_path.file.download.assert_called_once_with(
                    custom_path=file_and_path.path
                )

    def test_cancel_conversation(self) -> None:
        actual = self.sut.cancel_conversation(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.telegram_message.reply_text.assert_called_once()

    def test_get_support_markup(self) -> None:
        actual = self.sut.get_support_markup(
            self.telegram_update, self.telegram_context
        )
        assert isinstance(actual, InlineKeyboardMarkup)

    def test_get_user_data(self) -> None:
        self.telegram_context.user_data = {self.USER_DATA_KEY: self.USER_DATA_VALUE}

        actual = self.sut.get_user_data(self.telegram_context, self.USER_DATA_KEY)

        assert actual == self.USER_DATA_VALUE
        assert self.USER_DATA_KEY not in self.telegram_context.user_data

    def test_get_user_data_key_error(self) -> None:
        self.telegram_context.user_data = {}

        with pytest.raises(TelegramUserDataKeyError):
            self.sut.get_user_data(self.telegram_context, self.USER_DATA_KEY)

    def test_reply_with_back_markup(self) -> None:
        self.sut.reply_with_back_markup(
            self.telegram_update, self.telegram_context, self.telegram_text
        )
        self.telegram_message.reply_text.assert_called_once_with(
            self.telegram_text, reply_markup=ANY
        )

    def test_reply_with_file_document(self) -> None:
        file_path = f"{self.FILE_PATH}.pdf"
        with patch("pdf_bot.telegram_internal.telegram_service.os") as os, patch(
            "builtins.open"
        ) as _mock_open, patch(
            "pdf_bot.telegram_internal.telegram_service.send_event"
        ) as send_event:
            os.path.getsize.return_value = MAX_FILESIZE_UPLOAD

            self.sut.reply_with_file(
                self.telegram_update,
                self.telegram_context,
                file_path,
                TaskType.merge_pdf,
            )

            self.telegram_message.reply_chat_action.assert_called_once_with(
                ChatAction.UPLOAD_DOCUMENT
            )
            self.telegram_message.reply_document.assert_called_once()
            send_event.assert_called_once()

    def test_reply_with_file_image(self) -> None:
        file_path = f"{self.FILE_PATH}.png"
        with patch("pdf_bot.telegram_internal.telegram_service.os") as os, patch(
            "builtins.open"
        ) as _mock_open, patch(
            "pdf_bot.telegram_internal.telegram_service.send_event"
        ) as send_event:
            os.path.getsize.return_value = MAX_FILESIZE_UPLOAD

            self.sut.reply_with_file(
                self.telegram_update,
                self.telegram_context,
                file_path,
                TaskType.merge_pdf,
            )

            self.telegram_message.reply_chat_action.assert_called_once_with(
                ChatAction.UPLOAD_PHOTO
            )
            self.telegram_message.reply_photo.assert_called_once()
            send_event.assert_called_once()

    def test_reply_with_file_too_large(self) -> None:
        with patch("pdf_bot.telegram_internal.telegram_service.os") as os, patch(
            "builtins.open"
        ) as _mock_open, patch(
            "pdf_bot.telegram_internal.telegram_service.send_event"
        ) as send_event:
            os.path.getsize.return_value = MAX_FILESIZE_UPLOAD + 1

            self.sut.reply_with_file(
                self.telegram_update,
                self.telegram_context,
                self.FILE_PATH,
                TaskType.merge_pdf,
            )

            self.telegram_message.reply_chat_action.assert_not_called()
            self.telegram_message.reply_document.assert_not_called()
            self.telegram_message.reply_photo.assert_not_called()
            send_event.assert_not_called()

    def test_send_file_names(self) -> None:
        file_data_list = [FileData("a", "a"), FileData("b", "b")]

        self.sut.send_file_names(
            self.telegram_chat_id, self.telegram_text, file_data_list
        )

        self.telegram_bot.send_message.assert_called_once_with(
            self.telegram_chat_id, f"{self.telegram_text}1: a\n2: b\n"
        )