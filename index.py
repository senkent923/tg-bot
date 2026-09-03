import re
from datetime import datetime, timezone, timedelta

from flask import Flask, request

from common import send_message, format_lessons, BOT_NAME, CHAT_ID
from schedule_data import get_schedule_by_date

app = Flask(__name__)

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")

# Москва — всегда UTC+3, без перехода на летнее/зимнее время
MOSCOW_OFFSET = timedelta(hours=3)


@app.route("/api/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if chat_id is None:
        return {"ok": True}

    if text == "/start":
        send_message(chat_id, "🤖 Этот бот — личная разработка правительства Э-2511")
        send_message(
            chat_id,
            f"Привет! Я {BOT_NAME}.\n\n"
            f"Твой chat_id: {chat_id}\n"
            "Скопируй это число и впиши в переменную окружения CHAT_ID в "
            "настройках проекта на Vercel, потом сделай Redeploy — после "
            "этого я буду сам присылать сюда расписание каждый день в 8:00.\n\n"
            "А прямо сейчас можешь написать дату в формате ДД.ММ.ГГГГ, "
            "например 02.09.2026 — пришлю расписание на этот день."
        )
        return {"ok": True}

    if text == "/stop":
        send_message(
            chat_id,
            "Чтобы остановить ежедневную рассылку — удали переменную "
            "CHAT_ID в настройках проекта на Vercel и сделай Redeploy.",
        )
        return {"ok": True}

    if DATE_RE.match(text):
        lessons = get_schedule_by_date(text)
        send_message(chat_id, f"📅 Расписание на {text}:\n\n{format_lessons(lessons)}")
        return {"ok": True}

    send_message(
        chat_id,
        "Не понял 🤔 Напиши дату в формате ДД.ММ.ГГГГ, например 02.09.2026, "
        "или используй /start",
    )
    return {"ok": True}


@app.route("/api/daily", methods=["GET"])
def daily():
    if not CHAT_ID:
        return {"ok": False, "error": "Переменная CHAT_ID ещё не задана в настройках Vercel"}

    now_moscow = datetime.now(timezone.utc) + MOSCOW_OFFSET
    today_str = now_moscow.strftime("%d.%m.%Y")

    lessons = get_schedule_by_date(today_str)
    text = f"☀️ Доброе утро! Расписание на сегодня:\n\n{format_lessons(lessons)}"

    send_message(CHAT_ID, text)
    return {"ok": True, "date": today_str}
