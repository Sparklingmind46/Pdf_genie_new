import os

import sentry_sdk
from dependency_injector.wiring import Provide, inject
from dotenv import load_dotenv
from loguru import logger
from telegram.ext import Application as TelegramApp

import pdf_bot.logging as pdf_bot_logging
from pdf_bot.containers import Application
from pdf_bot.telegram_dispatcher import TelegramDispatcher

load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SENTRY_DSN = os.environ.get("SENTRY_DSN")
APP_URL = os.environ.get("APP_URL")
PORT = int(os.environ.get("PORT", "8443"))

TIMEOUT = 45


@inject
def main(
    telegram_app: TelegramApp = Provide[
        Application.core.telegram_app  # pylint: disable=no-member
    ],
    telegram_dispatcher: TelegramDispatcher = Provide[
        Application.telegram_bot.dispatcher  # pylint: disable=no-member
    ],
) -> None:
    if TELEGRAM_TOKEN is None:
        raise RuntimeError("Telegram token not specified")

    pdf_bot_logging.setup_logging()
    if SENTRY_DSN is not None:
        sentry_sdk.init(SENTRY_DSN, traces_sample_rate=1.0)

    telegram_dispatcher.setup(telegram_app)
    if APP_URL is not None:
        telegram_app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{APP_URL}/{TELEGRAM_TOKEN}",
        )
        logger.info("Bot started webhook")
    else:
        telegram_app.run_polling()
        logger.info("Bot started polling")


if __name__ == "__main__":
    application = Application()
    application.wire(modules=[__name__])

    main()
