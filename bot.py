import io
import logging
import os

import pytesseract
from PIL import Image, ImageOps
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("sabong24")

MAX_IMAGE_BYTES = 10 * 1024 * 1024


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Welcome to SABONG24!\n\n"
        "Send me an image and I’ll extract the text from it.\n\n"
        "Commands:\n"
        "/start — Start the bot\n"
        "/help — How to use SABONG24"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📸 How to use SABONG24\n\n"
        "1. Send a clear image containing text.\n"
        "2. Wait a moment while I process it.\n"
        "3. I’ll send back the extracted, copyable text.\n\n"
        "Tip: clearer, well-lit images usually produce better results."
    )


async def image_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    photo = message.photo[-1] if message.photo else None
    document = message.document if message.document and message.document.mime_type and message.document.mime_type.startswith("image/") else None

    if not photo and not document:
        return

    file_size = (photo.file_size if photo else document.file_size) or 0
    if file_size > MAX_IMAGE_BYTES:
        await message.reply_text("❌ That image is too large. Please send an image under 10 MB.")
        return

    await message.chat.send_action(ChatAction.TYPING)

    try:
        telegram_file = await context.bot.get_file(photo.file_id if photo else document.file_id)
        image_bytes = io.BytesIO()
        await telegram_file.download_to_memory(out=image_bytes)
        image_bytes.seek(0)

        image = Image.open(image_bytes)
        image = ImageOps.exif_transpose(image).convert("RGB")

        # Upscale smaller images to help Tesseract recognize text.
        if image.width < 1600:
            scale = 1600 / image.width
            image = image.resize((int(image.width * scale), int(image.height * scale)))

        text = pytesseract.image_to_string(image).strip()

        if not text:
            await message.reply_text(
                "I couldn't detect any text in that image. Try a clearer image with larger, well-lit text."
            )
            return

        # Telegram messages have a practical length limit, so split long OCR output.
        chunks = [text[i : i + 3900] for i in range(0, len(text), 3900)]
        await message.reply_text("📝 Extracted text:\n\n" + chunks[0])
        for chunk in chunks[1:]:
            await message.reply_text(chunk)

    except Exception:
        logger.exception("OCR processing failed")
        await message.reply_text(
            "⚠️ I couldn't process that image right now. Please try another image."
        )


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("📸 Send me an image and I’ll extract the text from it.")


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required.")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, image_to_text))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    logger.info("SABONG24 is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
