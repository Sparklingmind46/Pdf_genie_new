from telegram import ReplyKeyboardMarkup
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import *
from pdf_bot.utils import cancel_with_async, cancel_without_async
from pdf_bot.language import set_lang
from pdf_bot.files.crop import ask_crop_type, ask_crop_value, receive_crop_percent, \
    receive_crop_size
from pdf_bot.files.crypto import ask_decrypt_pw, ask_encrypt_pw, decrypt_pdf, encrypt_pdf
from pdf_bot.files.rename import ask_pdf_new_name, rename_pdf
from pdf_bot.files.rotate import ask_rotate_degree, rotate_pdf
from pdf_bot.files.scale import ask_scale_x, ask_scale_by_y, ask_scale_to_y, pdf_scale_by, \
    pdf_scale_to
from pdf_bot.files.split import ask_split_range, split_pdf
from pdf_bot.photos import get_pdf_preview, get_pdf_photos, pdf_to_photos, ask_photo_results_type, \
    process_photo_task, ask_photo_task


def file_cov_handler():
    """
    Create the file conversation handler object
    Returns:
        The conversation handler object
    """
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.document, check_doc),
                      MessageHandler(Filters.photo, check_photo)],
        states={
            WAIT_DOC_TASK: [MessageHandler(Filters.text, check_doc_task)],
            WAIT_PHOTO_TASK: [MessageHandler(Filters.text, check_photo_task)],
            WAIT_DECRYPT_PW: [MessageHandler(Filters.text, decrypt_pdf)],
            WAIT_ENCRYPT_PW: [MessageHandler(Filters.text, encrypt_pdf)],
            WAIT_ROTATE_DEGREE: [MessageHandler(Filters.text, check_rotate_task)],
            WAIT_SCALE_BY_X: [MessageHandler(Filters.text, ask_scale_by_y)],
            WAIT_SCALE_BY_Y: [MessageHandler(Filters.text, pdf_scale_by)],
            WAIT_SCALE_TO_X: [MessageHandler(Filters.text, ask_scale_to_y)],
            WAIT_SCALE_TO_Y: [MessageHandler(Filters.text, pdf_scale_to)],
            WAIT_SPLIT_RANGE: [MessageHandler(Filters.text, split_pdf)],
            WAIT_FILE_NAME: [MessageHandler(Filters.text, rename_pdf)],
            WAIT_CROP_TYPE: [MessageHandler(Filters.text, check_crop_task)],
            WAIT_CROP_PERCENT: [MessageHandler(Filters.text, receive_crop_percent)],
            WAIT_CROP_OFFSET: [MessageHandler(Filters.text, receive_crop_size)],
            WAIT_EXTRACT_PHOTO_TYPE: [MessageHandler(Filters.text, check_get_photos_task)],
            WAIT_TO_PHOTO_TYPE: [MessageHandler(Filters.text, check_to_photos_task)]
        },
        fallbacks=[CommandHandler('cancel', cancel_with_async)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def check_doc(update, context):
    """
    Validate the document and wait for the next action
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the next action or the conversation has ended
    """
    doc = update.effective_message.document
    mime_type = doc.mime_type

    if mime_type.startswith('image'):
        return ask_photo_task(update, context, doc)
    elif not mime_type.endswith('pdf'):
        return ConversationHandler.END
    elif doc.file_size >= MAX_FILESIZE_DOWNLOAD:
        _ = set_lang(update, context)
        update.effective_message.reply_text(_(
            'Your PDF file you sent is too large for me to download. '
            'I can\'t perform any tasks on it'))

        return ConversationHandler.END

    context.user_data[PDF_INFO] = doc.file_id, doc.file_name

    return ask_doc_task(update, context)


def ask_doc_task(update, context):
    """
    Send the message of tasks that can be performed on the PDF file
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the next aciton
    """
    _ = set_lang(update, context)
    keywords = sorted([_(DECRYPT), _(ENCRYPT), _(ROTATE), _(SCALE_BY), _(SCALE_TO), _(SPLIT),
                       _(PREVIEW), _(TO_IMG), _(EXTRACT_IMG), _(RENAME), _(CROP)])
    keyboard_size = 3
    keyboard = [keywords[i:i + keyboard_size] for i in range(0, len(keywords), keyboard_size)]
    keyboard.append([CANCEL])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.effective_message.reply_text(_('Select the task that you\'ll like to perform'),
                                        reply_markup=reply_markup)

    return WAIT_DOC_TASK


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
    elif text in [_(EXTRACT_IMG), _(TO_IMG)]:
        return ask_photo_results_type(update, context)
    elif text == _(PREVIEW):
        return get_pdf_preview(update, context)
    elif text == _(RENAME):
        return ask_pdf_new_name(update, context)
    elif text == _(ROTATE):
        return ask_rotate_degree(update, context)
    elif text in [_(SCALE_BY), _(SCALE_TO)]:
        return ask_scale_x(update, context)
    elif text == _(SPLIT):
        return ask_split_range(update, context)
    elif text == _(CANCEL):
        return cancel_without_async(update, context)


@run_async
def check_photo_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(BEAUTIFY), _(CONVERT)]:
        return process_photo_task(update, context)
    elif text == _(CANCEL):
        return cancel_without_async(update, context)


@run_async
def check_crop_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(CROP_PERCENT), _(CROP_SIZE)]:
        return ask_crop_value(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)


@run_async
def check_rotate_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(ROTATE_90), _(ROTATE_180), _(ROTATE_270)]:
        return rotate_pdf(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)


@run_async
def check_get_photos_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(PHOTOS), _(ZIPPED)]:
        return get_pdf_photos(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)


@run_async
def check_to_photos_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(PHOTOS), _(ZIPPED)]:
        return pdf_to_photos(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)
