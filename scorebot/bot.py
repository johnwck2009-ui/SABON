import logging
import os
from datetime import datetime, timezone

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_SCOREBOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")
API_URL = "https://v3.football.api-sports.io"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def football_request(path: str, params: dict):
    if not API_KEY:
        raise RuntimeError("API_FOOTBALL_KEY is not configured.")
    headers = {"x-apisports-key": API_KEY}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{API_URL}{path}", headers=headers, params=params)
        response.raise_for_status()
        return response.json()


def format_match(item: dict) -> str:
    fixture = item.get("fixture", {})
    teams = item.get("teams", {})
    goals = item.get("goals", {})
    league = item.get("league", {})
    status = fixture.get("status", {})
    elapsed = status.get("elapsed")
    short = status.get("short", "")
    home = teams.get("home", {}).get("name", "Home")
    away = teams.get("away", {}).get("name", "Away")
    home_goals = goals.get("home")
    away_goals = goals.get("away")
    score = f"{home_goals if home_goals is not None else '-'} - {away_goals if away_goals is not None else '-'}"
    state = f"{elapsed}'" if elapsed is not None else short
    return f"⚽ {home} {score} {away}  |  {state}\n🏆 {league.get('name', 'Football')}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ Welcome to SABONG24 Football Scores!\n\n"
        "Use /live for matches currently in play.\n"
        "Use /today for today's fixtures and results.\n"
        "Use /help for commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/live — Live football scores\n"
        "/today — Today's fixtures and results\n"
        "/start — Start the bot"
    )


async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = await football_request("/fixtures", {"live": "all"})
        matches = data.get("response", [])
        if not matches:
            await update.message.reply_text("⚽ No live football matches right now.")
            return
        text = "🔴 LIVE FOOTBALL SCORES\n\n" + "\n\n".join(format_match(m) for m in matches[:20])
        await update.message.reply_text(text)
    except Exception:
        logging.exception("Live scores request failed")
        await update.message.reply_text("Sorry, live scores are temporarily unavailable. Please try again shortly.")


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today_utc = datetime.now(timezone.utc).date().isoformat()
    try:
        data = await football_request("/fixtures", {"date": today_utc})
        matches = data.get("response", [])
        if not matches:
            await update.message.reply_text("⚽ No fixtures or results were found for today.")
            return
        lines = ["📅 TODAY'S FOOTBALL", ""]
        for m in matches[:30]:
            lines.extend([format_match(m), ""])
        await update.message.reply_text("\n".join(lines).strip())
    except Exception:
        logging.exception("Today's fixtures request failed")
        await update.message.reply_text("Sorry, today's fixtures are temporarily unavailable. Please try again shortly.")


async def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_SCOREBOT_TOKEN or TELEGRAM_BOT_TOKEN is required.")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("today", today))
    logging.info("SABONG24 Football Scores bot starting")
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
