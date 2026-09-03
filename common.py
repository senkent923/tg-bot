import os
import requests

BOT_NAME = "Расписание Э-2511"

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")  # заполняется после первого /start

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text: str):
    if not BOT_TOKEN:
        return
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )


def format_lessons(lessons: list[dict]) -> str:
    if not lessons:
        return "Занятий не найдено 🎉"

    lines = []
    for l in lessons:
        room = f", ауд. {l['room']}" if l["room"] else ""
        teacher = f"\n👤 {l['teacher']}" if l["teacher"] else ""
        lines.append(
            f"🕒 {l['time_start']}–{l['time_end']}\n"
            f"📚 {l['subject']} ({l['type']}){room}{teacher}"
        )
    return "\n\n".join(lines)
