import hashlib
import hmac
import json
import sys
import time
from urllib.parse import urlencode


def read_env(name):
    for line in open(".env", encoding="utf-8"):
        line = line.strip()
        if line.startswith(name + "="):
            return line.split("=", 1)[1]


token = read_env("BOT_TOKEN")
user_id = int(sys.argv[1]) if len(sys.argv) > 1 else 777
name = sys.argv[2] if len(sys.argv) > 2 else "Тест"

fields = {
    "auth_date": str(int(time.time())),
    "query_id": "AAA",
    "user": json.dumps({"id": user_id, "first_name": name}, ensure_ascii=False),
}
check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
fields["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()

print("tma " + urlencode(fields))