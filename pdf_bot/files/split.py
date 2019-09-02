import tempfile

from PyPDF2 import PdfFileMerger
from PyPDF2.pagerange import PageRange
from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async
from telegram.parsemode import ParseMode

from pdf_bot.constants import WAIT_SPLIT_RANGE, PDF_INFO
from pdf_bot.utils import open_pdf, write_send_pdf, get_lang


def ask_split_range(update, context):
    """
    Ask and wait for the split page range
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the split page range
    """
    _ = get_lang(update, context)
    update.effective_message.reply_text(_(
        'Send me the range of pages that you\'ll like to keep. '
        'Use ⚡ *INSTANT VIEW* from below for some range examples.'),
        parse_mode=ParseMode.MARKDOWN, reply_markup=ReplyKeyboardRemove())

    return WAIT_SPLIT_RANGE


@run_async
def split_pdf(update, context):
    """
    Split the PDF file with the given split page range
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the split page range or the conversation has ended
    """
    user_data = context.user_data
    if PDF_INFO not in user_data:
        return ConversationHandler.END

    _ = get_lang(update, context)
    message = update.effective_message
    split_range = message.text

    if not PageRange.valid(split_range):
        message.reply_text(_('The range is invalid. Try again.'))

        return WAIT_SPLIT_RANGE

    message.reply_text(_('Splitting your PDF file'))

    with tempfile.NamedTemporaryFile() as tf:
        # Download PDF file
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)
        pdf_reader = open_pdf(update, context, tf.name)

        if pdf_reader is not None:
            merger = PdfFileMerger()
            merger.append(pdf_reader, pages=PageRange(split_range))
            write_send_pdf(update, context, merger, file_name, 'split')

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END
