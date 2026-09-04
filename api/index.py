import re
from datetime import datetime, timezone, timedelta

from flask import Flask, request

from common import send_message, format_lessons, BOT_NAME, add_subscriber, get_all_subscribers
from schedule_data import get_schedule_by_date

app = Flask(__name__)

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")

# Москва — всегда UTC+3, без перехода на летнее/зимнее время
MOSCOW_OFFSET = timedelta(hours=3)


def _moscow_now():
    return datetime.now(timezone.utc) + MOSCOW_OFFSET


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
            "Ты уже подписан(а) на рассылку — каждый день в 7:30 по Москве "
            "я буду сам присылать сюда расписание на сегодня.\n\n"
            "Хочешь узнать расписание заранее? Вот как:\n"
            "• напиши /tomorrow — покажу расписание на завтра\n"
            "• напиши /week — покажу расписание на ближайшие 7 дней\n"
            "• напиши любую дату в формате ДД.ММ.ГГГГ (например 02.09.2026) "
            "— покажу расписание именно на этот день"
        )
        return {"ok": True}

    if text == "/stop":
        send_message(
            chat_id,
            "Пока отписаться от рассылки можно только вручную — напиши "
            "об этом создателю бота.",
        )
        return {"ok": True}

    if text == "/tomorrow":
        add_subscriber(chat_id)
        tomorrow = _moscow_now() + timedelta(days=1)
        tomorrow_str = tomorrow.strftime("%d.%m.%Y")
        lessons = get_schedule_by_date(tomorrow_str)
        send_message(chat_id, f"📅 Расписание на завтра ({tomorrow_str}):\n\n{format_lessons(lessons)}")
        return {"ok": True}

    if text == "/week":
        add_subscriber(chat_id)
        today = _moscow_now()
        blocks = []
        for i in range(7):
            day = today + timedelta(days=i)
            day_str = day.strftime("%d.%m.%Y")
            lessons = get_schedule_by_date(day_str)
            if lessons:
                blocks.append(f"📅 {day_str} ({lessons[0]['weekday']}):\n\n{format_lessons(lessons)}")
        text_out = "\n\n➖➖➖\n\n".join(blocks) if blocks else "На ближайшие 7 дней занятий не найдено 🎉"
        send_message(chat_id, text_out)
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
    today_str = _moscow_now().strftime("%d.%m.%Y")

    lessons = get_schedule_by_date(today_str)
    text = f"☀️ Доброе утро! Расписание на сегодня:\n\n{format_lessons(lessons)}"

    subscribers = get_all_subscribers()
    sent = 0
    for chat_id in subscribers:
        send_message(chat_id, text)
        sent += 1

    return {"ok": True, "date": today_str, "sent_to": sent}
