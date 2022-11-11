from dataclasses import dataclass
from unittest.mock import MagicMock, call

import pytest
from telegram import File
from telegram.constants import MAX_FILESIZE_DOWNLOAD

from pdf_bot.io import IOService
from pdf_bot.models import FileData
from pdf_bot.telegram import (
    TelegramFileMimeTypeError,
    TelegramFileTooLargeError,
    TelegramImageNotFoundError,
    TelegramService,
)
from pdf_bot.telegram.exceptions import TelegramUserDataKeyError
from tests.telegram.telegram_test_mixin import TelegramTestMixin


class TestTelegramRService(TelegramTestMixin):
    @classmethod
    def setup_class(cls) -> None:
        super().setup_class()
        cls.img_mime_type = "image"
        cls.pdf_mime_type = "pdf"
        cls.file_path = "file_path"
        cls.user_data_key = "user_data_key"
        cls.user_data_value = "user_data_value"

    def setup_method(self) -> None:
        super().setup_method()
        self.io_service = MagicMock(spec=IOService)
        self.sut = TelegramService(self.io_service, bot=self.telegram_bot)

    def test_check_file_size(self) -> None:
        self.telegram_document.file_size = MAX_FILESIZE_DOWNLOAD
        self.sut.check_file_size(self.telegram_document)

    def test_check_file_size_too_large(self) -> None:
        self.telegram_document.file_size = MAX_FILESIZE_DOWNLOAD + 1
        with pytest.raises(TelegramFileTooLargeError):
            self.sut.check_file_size(self.telegram_document)

    def test_check_image_document(self) -> None:
        self.telegram_document.mime_type = self.img_mime_type
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
        self.telegram_document.mime_type = self.img_mime_type
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
        self.telegram_document.mime_type = self.pdf_mime_type
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
        self.telegram_document.mime_type = self.pdf_mime_type
        self.telegram_document.file_size = MAX_FILESIZE_DOWNLOAD + 1
        self.telegram_message.document = self.telegram_document

        with pytest.raises(TelegramFileTooLargeError):
            self.sut.check_pdf_document(self.telegram_message)

    def test_download_file(self) -> None:
        self.io_service.create_temp_file.return_value.__enter__.return_value = (
            self.file_path
        )
        self.telegram_bot.get_file.return_value = self.telegram_file

        with self.sut.download_file(self.telegram_file_id) as actual:
            assert actual == self.file_path
            self.telegram_bot.get_file.assert_called_with(self.telegram_file_id)
            self.telegram_file.download.assert_called_once_with(
                custom_path=self.file_path
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

    def test_get_user_data(self) -> None:
        self.telegram_context.user_data = {self.user_data_key: self.user_data_value}

        actual = self.sut.get_user_data(self.telegram_context, self.user_data_key)

        assert actual == self.user_data_value
        assert self.user_data_key not in self.telegram_context.user_data

    def test_get_user_data_key_error(self) -> None:
        self.telegram_context.user_data = {}

        with pytest.raises(TelegramUserDataKeyError):
            self.sut.get_user_data(self.telegram_context, self.user_data_key)

    def test_send_file_names(self) -> None:
        file_data_list = [FileData("a", "a"), FileData("b", "b")]

        self.sut.send_file_names(
            self.telegram_chat_id, self.telegram_text, file_data_list
        )

        self.telegram_bot.send_message.assert_called_once_with(
            self.telegram_chat_id, f"{self.telegram_text}1: a\n2: b\n"
        )
