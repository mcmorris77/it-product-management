import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.auth import validate_init_data

TOKEN = "123456:TEST-TOKEN"
USER = {"id": 777, "first_name": "Аня"}

def make_init_data(token=TOKEN, auth_date=None, user=USER):
    fields = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "AAA",
        "user": json.dumps(user, ensure_ascii=False)
    }
    check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)

def test_valid_token():
    assert validate_init_data(make_init_data(), TOKEN)["id"] == 777

def test_wrong_token():
    with pytest.raises(ValueError):
        validate_init_data(make_init_data(token="999:OTHER"), TOKEN)


def test_tampered_data():
    data = make_init_data().replace("777", "111")
    with pytest.raises(ValueError):
        validate_init_data(data, TOKEN)


def test_expired_data():
    old = int(time.time()) - 3 * 24 * 60 * 60
    with pytest.raises(ValueError):
        validate_init_data(make_init_data(auth_date=old), TOKEN)