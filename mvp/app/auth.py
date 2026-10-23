import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl

from dotenv import load_dotenv
from fastapi import Header, HTTPException
from . import crud

load_dotenv()

MAX_AGE = 24*60*60

def validate_init_data(init_data: str, bot_token: str, max_age: int =
MAX_AGE) -> dict:
    # Проверяет подпись и срок действия Telegram Mini App initData.
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("Нет подписи")

    # строка для проверки key=value с переносом строки
    check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))

    # сравниваем ожидаемый и фактический хеш
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("Подпись не совпала")

    auth_date = int(pairs.get("auth_date", "0"))
    if time.time() - auth_date > max_age:
        raise ValueError("Данные устарели")

    if "user" not in pairs:
        raise ValueError("Нет данных о пользователе")

    return json.loads(pairs["user"])

def get_current_user(authorization: str = Header(default="")) -> dict:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise HTTPException(status_code=500, detail="На сервере не задан BOT_TOKEN")

    scheme, _, init_data = authorization.partition(" ")
    if scheme.lower()!="tma" or not init_data:
        raise HTTPException(status_code=401,
                            detail="Нужен заголовок Authorization: tma <initData>")
    try:
        tg_user = validate_init_data(init_data, bot_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Данные Telegram не прошли проверку")

    user = crud.get_user_by_telegram_id(tg_user["id"])
    if user is None:
        name = tg_user.get("first_name") or "Нет имени"
        user_id = crud.create_user(tg_user["id"], name)
        user = crud.get_user(user_id)

    return user
