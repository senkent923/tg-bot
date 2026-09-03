import os
import requests

BOT_NAME = "Расписание Э-2511"

BOT_TOKEN = os.environ.get("BOT_TOKEN")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

REDIS_URL = os.environ.get("REDIS_URL")

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None and REDIS_URL:
        import redis
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def add_subscriber(chat_id):
    client = _get_redis()
    if client:
        client.sadd("subscribers", chat_id)


def get_all_subscribers() -> list:
    client = _get_redis()
    if not client:
        return []
    return list(client.smembers("subscribers"))


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
