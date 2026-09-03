import re
from datetime import datetime, timezone, timedelta

from flask import Flask, request

from common import send_message, format_lessons, BOT_NAME, add_subscriber, get_all_subscribers
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
        add_subscriber(chat_id)
        send_message(
            chat_id,
            "🏛 Правительство Э-2511\n"
            "Официальное сообщение №1\n\n"
            "Настоящим уведомляем: данный бот является официальной "
            "государственной разработкой Правительства группы Э-2511. "
            "Все функции бота сертифицированы и одобрены на самом "
            "высоком уровне 🖋️",
        )
        send_message(
            chat_id,
            f"Привет! Я {BOT_NAME}.\n\n"
            "Ты уже подписан(а) на рассылку — каждый день в 8:00 по Москве "
            "я буду сам присылать сюда расписание на сегодня.\n\n"
            "А прямо сейчас можешь написать любую дату в формате ДД.ММ.ГГГГ, "
            "например 02.09.2026 — пришлю расписание на этот день."
        )
        return {"ok": True}

    if text == "/stop":
        send_message(
            chat_id,
            "Пока отписаться от рассылки можно только вручную — напиши "
            "об этом создателю бота.",
        )
        return {"ok": True}

    if DATE_RE.match(text):
        add_subscriber(chat_id)
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
    now_moscow = datetime.now(timezone.utc) + MOSCOW_OFFSET
    today_str = now_moscow.strftime("%d.%m.%Y")

    lessons = get_schedule_by_date(today_str)
    text = f"☀️ Доброе утро! Расписание на сегодня:\n\n{format_lessons(lessons)}"

    subscribers = get_all_subscribers()
    sent = 0
    for chat_id in subscribers:
        send_message(chat_id, text)
        sent += 1

    return {"ok": True, "date": today_str, "sent_to": sent}
