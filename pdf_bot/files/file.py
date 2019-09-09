from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import *
from pdf_bot.utils import cancel_with_async, cancel_without_async
from pdf_bot.language import set_lang
from pdf_bot.files.crop import ask_crop_type, ask_crop_value, check_crop_percent, \
    check_crop_size
from pdf_bot.files.crypto import ask_decrypt_pw, ask_encrypt_pw, decrypt_pdf, encrypt_pdf
from pdf_bot.files.rename import ask_pdf_new_name, rename_pdf
from pdf_bot.files.rotate import ask_rotate_degree, check_rotate_degree
from pdf_bot.files.scale import ask_scale_type, ask_scale_value, check_scale_percent, \
    check_scale_dimension
from pdf_bot.files.split import ask_split_range, split_pdf
from pdf_bot.files.photo import get_pdf_preview, get_pdf_photos, pdf_to_photos, \
    ask_photo_results_type, process_photo_task, ask_photo_task
from pdf_bot.files.document import ask_doc_task


def file_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.document, check_doc),
            MessageHandler(Filters.photo, check_photo)],
        states={
            WAIT_DOC_TASK: [MessageHandler(Filters.text, check_doc_task)],
            WAIT_PHOTO_TASK: [MessageHandler(Filters.text, check_photo_task)],

            WAIT_CROP_TYPE: [MessageHandler(Filters.text, check_crop_task)],
            WAIT_CROP_PERCENT: [MessageHandler(Filters.text, check_crop_percent)],
            WAIT_CROP_OFFSET: [MessageHandler(Filters.text, check_crop_size)],

            WAIT_DECRYPT_PW: [MessageHandler(Filters.text, decrypt_pdf)],
            WAIT_ENCRYPT_PW: [MessageHandler(Filters.text, encrypt_pdf)],

            WAIT_FILE_NAME: [MessageHandler(Filters.text, rename_pdf)],
            WAIT_ROTATE_DEGREE: [MessageHandler(Filters.text, check_rotate_degree)],
            WAIT_SPLIT_RANGE: [MessageHandler(Filters.text, split_pdf)],

            WAIT_SCALE_TYPE: [MessageHandler(Filters.text, check_scale_task)],
            WAIT_SCALE_PERCENT: [MessageHandler(Filters.text, check_scale_percent)],
            WAIT_SCALE_DIMENSION: [MessageHandler(Filters.text, check_scale_dimension)],

            WAIT_EXTRACT_PHOTO_TYPE: [MessageHandler(Filters.text, check_get_photos_task)],
            WAIT_TO_PHOTO_TYPE: [MessageHandler(Filters.text, check_to_photos_task)]
        },
        fallbacks=[CommandHandler('cancel', cancel_with_async)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def check_doc(update, context):
    doc = update.effective_message.document
    if doc.mime_type.startswith('image'):
        return ask_photo_task(update, context, doc)
    elif not doc.mime_type.endswith('pdf'):
        return ConversationHandler.END
    elif doc.file_size >= MAX_FILESIZE_DOWNLOAD:
        _ = set_lang(update, context)
        update.effective_message.reply_text(_(
            'Your PDF file is too large for me to download. I can\'t perform any tasks on it'))

        return ConversationHandler.END

    context.user_data[PDF_INFO] = doc.file_id, doc.file_name

    return ask_doc_task(update, context)


@run_async
def check_photo(update, context):
    return ask_photo_task(update, context, update.effective_message.photo[-1])


@run_async
def check_doc_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text == _(CROP):
        return ask_crop_type(update, context)
    elif text == _(DECRYPT):
        return ask_decrypt_pw(update, context)
    elif text == _(ENCRYPT):
        return ask_encrypt_pw(update, context)
    elif text in [_(EXTRACT_PHOTO), _(TO_PHOTO)]:
        return ask_photo_results_type(update, context)
    elif text == _(PREVIEW):
        return get_pdf_preview(update, context)
    elif text == _(RENAME):
        return ask_pdf_new_name(update, context)
    elif text == _(ROTATE):
        return ask_rotate_degree(update, context)
    elif text in [_(SCALE)]:
        return ask_scale_type(update, context)
    elif text == _(SPLIT):
        return ask_split_range(update, context)
    elif text == _(CANCEL):
        return cancel_without_async(update, context)


@run_async
def check_photo_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(BEAUTIFY), _(TO_PDF)]:
        return process_photo_task(update, context)
    elif text == _(CANCEL):
        return cancel_without_async(update, context)


@run_async
def check_crop_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(BY_PERCENT), _(BY_SIZE)]:
        return ask_crop_value(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)


@run_async
def check_scale_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(BY_PERCENT), _(TO_DIMENSIONS)]:
        return ask_scale_value(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)


@run_async
def check_get_photos_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(PHOTOS), _(COMPRESSED)]:
        return get_pdf_photos(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)


@run_async
def check_to_photos_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(PHOTOS), _(COMPRESSED)]:
        return pdf_to_photos(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)
