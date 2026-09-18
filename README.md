# SABONG24

SABONG24 is a simple Telegram utility bot that extracts text from images.

## Features

- Send an image/photo to the bot
- OCR extracts the text
- Returns copyable text in Telegram
- Handles long OCR results
- Rejects images larger than 10 MB

## Run locally

### 1. Install Tesseract

On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Set the bot token

Create the bot with BotFather and set:

```bash
export TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
```

### 4. Start SABONG24

```python bot.py
```

## Docker

Build and run:

```bash
docker build -t sabong24 .
docker run --rm -e TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN" sabong24
```

## Privacy

SABONG24 processes images only to perform OCR and does not intentionally store uploaded images. For production deployment, review the hosting provider's logging/storage behavior and add a privacy policy before advertising the bot.
