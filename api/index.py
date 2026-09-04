import re
from datetime import datetime, timezone, timedelta

from flask import Flask, request

from common import send_message, format_lessons, BOT_NAME, add_subscriber, get_all_subscribers, try_claim_reminder, track_member, get_members
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

    chat_type = chat.get("type", "private")
    from_user = message.get("from") or {}
    from_id = from_user.get("id")
    from_name = from_user.get("first_name")

    # Запоминаем участника группы для будущей команды /all
    if chat_type in ("group", "supergroup") and from_id and from_name:
        track_member(chat_id, from_id, from_name)

    if text.startswith("/all"):
        add_subscriber(chat_id)
        members = get_members(chat_id)
        if not members:
            send_message(
                chat_id,
                "Пока никого не запомнил 🤔 Попроси всех написать что-нибудь "
                "в группе (любое сообщение), потом попробуй /all снова.",
            )
            return {"ok": True}

        mentions = " ".join(
            f'<a href="tg://user?id={uid}">{name}</a>'
            for uid, name in members.items()
        )
        send_message(chat_id, mentions, html=True)
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
        text_out = "\n\n➖➖➖\n\n".join(blocks) if blocks else "На ближайшие 7 дней пар нет, красота 😎"
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


@app.route("/api/remind", methods=["GET"])
def remind():
    """Проверяет, не начинается ли какая-то пара в ближайшие 10-20 минут,
    и если да — шлёт напоминание всем подписчикам (один раз на пару)."""
    now = _moscow_now()
    today_str = now.strftime("%d.%m.%Y")
    lessons = get_schedule_by_date(today_str)

    reminders_sent = 0
    for i, l in enumerate(lessons):
        if i != 0:
            continue  # напоминаем только про первую пару дня

        hh, mm = map(int, l["time_start"].split(":"))
        lesson_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        diff_minutes = (lesson_dt - now).total_seconds() / 60

        if 10 <= diff_minutes <= 20:
            key = f"reminded:{today_str}:{l['time_start']}:{l['subject']}"
            if try_claim_reminder(key):
                room = f", ауд. {l['room']}" if l["room"] else ""
                text = (
                    f"🏃❗️ Скоро начинаются пары!\n\n"
                    f"📚 {l['subject']} ({l['type']}){room}\n"
                    f"Начало в {l['time_start']}"
                )
                for chat_id in get_all_subscribers():
                    send_message(chat_id, text)
                reminders_sent += 1

    return {"ok": True, "reminders_sent": reminders_sent}
