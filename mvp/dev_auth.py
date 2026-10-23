from urllib.parse import quote
from tests.test_auth import make_init_data

data = make_init_data()
print("Для Postman, заголовок Authorization:")
print("tma " + data)
print()
print("Для браузера, добавь к адресу:")
print("&auth="+quote(data, safe=""))