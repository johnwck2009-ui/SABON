import io
import logging
import os
import re

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("sabong24")

MAX_IMAGE_BYTES = 10 * 1024 * 1024

FOOTBALL_KEYWORDS = {
    "football",
    "soccer",
    "fixture",
    "fixtures",
    "match",
    "matches",
    "score",
    "scores",
    "halftime",
    "half-time",
    "fulltime",
    "full-time",
    "league",
    "premier",
    "champions",
    "cup",
    "fc",
    "united",
    "city",
    "real madrid",
    "barcelona",
    "liverpool",
    "chelsea",
    "arsenal",
    "tottenham",
    "manchester",
    "juventus",
    "inter",
    "milan",
    "bayern",
    "psg",
    "dortmund",
    "napoli",
    "roma",
    "ajax",
    "porto",
    "benfica",
}

SCORE_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*[-:]\s*(\d{1,2})(?!\d)")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "⚽ Welcome to SABONG24!\n\n"
        "Send me a football screenshot and I’ll turn the visible match, "
        "score, fixture or table information into clean, copyable text.\n\n"
        "Commands:\n"
        "/start — Start the bot\n"
        "/help — How to use SABONG24"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "⚽ Football Screenshot Utility\n\n"
        "1. Send a clear screenshot of a football match, fixture, score or table.\n"
        "2. I’ll read the text from the image.\n"
        "3. I’ll return clean, copyable text and highlight score patterns when detected.\n\n"
        "Tip: crop the screenshot around the football information and use a clear image "
        "for better results."
    )


def preprocess_image(image: Image.Image) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("L")

    # Upscale smaller screenshots to improve OCR accuracy.
    if image.width < 1800:
        scale = 1800 / image.width
        image = image.resize(
            (int(image.width * scale), int(image.height * scale))
        )

    image = ImageEnhance.Contrast(image).enhance(1.5)
    image = image.filter(ImageFilter.SHARPEN)
    return image


def looks_like_football_text(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in FOOTBALL_KEYWORDS)


def format_football_result(text: str) -> str:
    cleaned_lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = "\n".join(cleaned_lines)

    scores = SCORE_PATTERN.findall(cleaned)
    result = "⚽ Football information detected:\n\n" + cleaned

    if scores:
        unique_scores = []
        for home, away in scores:
            score = f"{home}-{away}"
            if score not in unique_scores:
                unique_scores.append(score)
        result += "\n\n📊 Score pattern(s): " + ", ".join(unique_scores)

    return result


async def image_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
        return

    photo = message.photo[-1] if message.photo else None
    document = (
        message.document
        if message.document
        and message.document.mime_type
        and message.document.mime_type.startswith("image/")
        else None
    )

    if not photo and not document:
        return

    file_size = (photo.file_size if photo else document.file_size) or 0
    if file_size > MAX_IMAGE_BYTES:
        await message.reply_text(
            "❌ That image is too large. Please send an image under 10 MB."
        )
        return

    await message.chat.send_action(ChatAction.TYPING)

    try:
        telegram_file = await context.bot.get_file(
            photo.file_id if photo else document.file_id
        )
        image_bytes = io.BytesIO()
        await telegram_file.download_to_memory(out=image_bytes)
        image_bytes.seek(0)

        image = Image.open(image_bytes)
        image = preprocess_image(image)

        text = pytesseract.image_to_string(
            image,
            config="--psm 6",
        ).strip()

        if not text:
            await message.reply_text(
                "❌ I couldn't read the screenshot. Try a clearer football screenshot "
                "with larger text."
            )
            return

        if looks_like_football_text(text):
            output = format_football_result(text)
        else:
            output = (
                "⚽ I couldn't confidently identify football information in this image.\n\n"
                "Here is the text I could read:\n\n"
                + text
                + "\n\n"
                "For best results, send a screenshot of a football score, fixture, "
                "match page or league table."
            )

        # Telegram messages have a practical length limit, so split long OCR output.
        chunks = [output[i : i + 3900] for i in range(0, len(output), 3900)]
        for chunk in chunks:
            await message.reply_text(chunk)

    except Exception:
        logger.exception("Football screenshot processing failed")
        await message.reply_text(
            "⚠️ I couldn't process that football screenshot right now. "
            "Please try another clear image."
        )


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "⚽ Send me a football screenshot — match result, fixture, score or table — "
            "and I’ll turn the visible information into copyable text."
        )


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required.")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, image_to_text)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message)
    )

    logger.info("SABONG24 football screenshot utility is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
