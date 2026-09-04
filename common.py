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


def send_message(chat_id, text: str, html: bool = False):
    if not BOT_TOKEN:
        return
    payload = {"chat_id": chat_id, "text": text}
    if html:
        payload["parse_mode"] = "HTML"
        payload["disable_web_page_preview"] = True
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json=payload,
        timeout=10,
    )


def track_member(chat_id, user_id, first_name):
    client = _get_redis()
    if client and user_id and first_name:
        client.hset(f"members:{chat_id}", str(user_id), first_name)


def get_members(chat_id) -> dict:
    client = _get_redis()
    if not client:
        return {}
    return client.hgetall(f"members:{chat_id}") or {}


def format_lessons(lessons: list[dict]) -> str:
    if not lessons:
        return "Сегодня пар нет, чилим 😎"

    lines = []
    for l in lessons:
        room = f", ауд. {l['room']}" if l["room"] else ""
        teacher = f"\n👤 {l['teacher']}" if l["teacher"] else ""
        lines.append(
            f"🕒 {l['time_start']}–{l['time_end']}\n"
            f"📚 {l['subject']} ({l['type']}){room}{teacher}"
        )
    return "\n\n".join(lines)


def try_claim_reminder(key: str) -> bool:
    """Возвращает True только один раз для данного ключа (защита от дублей)."""
    client = _get_redis()
    if not client:
        return True
    return bool(client.set(key, "1", ex=3600, nx=True))
