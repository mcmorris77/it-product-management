import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode, urlparse

import pytest
from fastapi.testclient import TestClient

from app import database


TEST_BOT_TOKEN = "123456:TEST-TOKEN"


def make_init_data(telegram_id: int, name: str) -> str:
    fields = {
        "auth_date": str(int(time.time())),
        "query_id": f"test-{telegram_id}",
        "user": json.dumps(
            {"id": telegram_id, "first_name": name},
            ensure_ascii=False,
        ),
    }

    check_string = "\n".join(
        f"{key}={fields[key]}" for key in sorted(fields)
    )
    secret_key = hmac.new(
        b"WebAppData",
        TEST_BOT_TOKEN.encode(),
        hashlib.sha256,
    ).digest()
    fields["hash"] = hmac.new(
        secret_key,
        check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    return urlencode(fields)


def auth_headers(telegram_id: int, name: str) -> dict[str, str]:
    return {
        "Authorization": f"tma {make_init_data(telegram_id, name)}"
    }


@pytest.fixture
def client(monkeypatch):
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if not test_database_url:
        pytest.fail(
            "Задай TEST_DATABASE_URL для отдельной тестовой базы, "
            "например split_bill_test."
        )

    parsed_url = urlparse(test_database_url)
    database_name = parsed_url.path.rsplit("/", 1)[-1]

    if not database_name.endswith("_test"):
        pytest.fail(
            "Тестовая база должна называться с окончанием _test, "
            "например split_bill_test."
        )

    if test_database_url == os.getenv("DATABASE_URL"):
        pytest.fail("TEST_DATABASE_URL не должен совпадать с DATABASE_URL.")

    monkeypatch.setattr(database, "DATABASE_URL", test_database_url)
    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)

    database.create_tables()

    conn = database.get_connections()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "TRUNCATE TABLE claims, items, checks, users "
                "RESTART IDENTITY CASCADE"
            )
        conn.commit()
    finally:
        conn.close()

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def create_check(
    client: TestClient,
    telegram_id: int,
    name: str,
    items: list[dict],
) -> dict:
    response = client.post(
        "/checks/",
        headers=auth_headers(telegram_id, name),
        json={
            "title": "Тестовый чек",
            "payment_info": "Тестовые реквизиты",
            "items": items,
        },
    )

    assert response.status_code == 200, response.text
    return response.json()


def test_health_and_missing_check(client):
    health = client.get("/health")
    missing_check = client.get("/checks/999999")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert missing_check.status_code == 404


def test_check_creation_requires_valid_telegram_auth(client):
    response = client.post(
        "/checks/",
        json={"title": "Чек", "items": []},
    )

    assert response.status_code == 401


def test_summary_returns_claimed_amount_and_unclaimed_items(client):
    check = create_check(
        client,
        10001,
        "Плательщик",
        [
            {"name": "Общее блюдо", "price": 101, "type": "shared"},
            {"name": "Десерт", "price": 250, "type": "single"},
        ],
    )
    item_id = check["items"][0]["id"]

    claim_response = client.post(
        f"/items/{item_id}/claim",
        headers=auth_headers(10002, "Участник"),
    )
    summary_response = client.get(f"/checks/{check['id']}/summary")

    assert claim_response.status_code == 200
    assert summary_response.status_code == 200

    summary = summary_response.json()
    assert summary["check_total"] == 351
    assert summary["totals"] == [
        {"user_id": 2, "name": "Участник", "amount": 101}
    ]
    assert [item["name"] for item in summary["unclaimed_items"]] == ["Десерт"]


def test_me_returns_current_users_amount(client):
    check = create_check(
        client,
        20001,
        "Участник",
        [
            {"name": "Общее блюдо", "price": 101, "type": "shared"},
            {"name": "Десерт", "price": 250, "type": "single"},
        ],
    )
    headers = auth_headers(20001, "Участник")

    for item in check["items"]:
        response = client.post(
            f"/items/{item['id']}/claim",
            headers=headers,
        )
        assert response.status_code == 200

    me_response = client.get(
        f"/checks/{check['id']}/me",
        headers=headers,
    )

    assert me_response.status_code == 200
    assert me_response.json() == {
        "amount": 351,
        "is_payer": True,
        "payment_info": "Тестовые реквизиты",
    }


def test_unclaim_removes_claim_from_summary(client):
    check = create_check(
        client,
        30001,
        "Плательщик",
        [{"name": "Общее блюдо", "price": 101, "type": "shared"}],
    )
    item_id = check["items"][0]["id"]
    headers = auth_headers(30002, "Участник")

    claim_response = client.post(
        f"/items/{item_id}/claim",
        headers=headers,
    )
    unclaim_response = client.delete(
        f"/items/{item_id}/claim",
        headers=headers,
    )
    summary_response = client.get(f"/checks/{check['id']}/summary")

    assert claim_response.status_code == 200
    assert unclaim_response.status_code == 200
    assert summary_response.json()["totals"] == []
    assert [
        item["name"] for item in summary_response.json()["unclaimed_items"]
    ] == ["Общее блюдо"]


def test_single_item_can_be_claimed_only_once(client):
    check = create_check(
        client,
        40001,
        "Плательщик",
        [{"name": "Индивидуальное блюдо", "price": 250, "type": "single"}],
    )
    item_id = check["items"][0]["id"]

    first_response = client.post(
        f"/items/{item_id}/claim",
        headers=auth_headers(40002, "Первый участник"),
    )
    second_response = client.post(
        f"/items/{item_id}/claim",
        headers=auth_headers(40003, "Второй участник"),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409


def test_closed_check_rejects_claim(client):
    check = create_check(
        client,
        50001,
        "Плательщик",
        [{"name": "Общее блюдо", "price": 101, "type": "shared"}],
    )
    item_id = check["items"][0]["id"]
    payer_headers = auth_headers(50001, "Плательщик")

    close_response = client.post(
        f"/checks/{check['id']}/close",
        headers=payer_headers,
    )
    claim_response = client.post(
        f"/items/{item_id}/claim",
        headers=auth_headers(50002, "Участник"),
    )

    assert close_response.status_code == 200
    assert claim_response.status_code == 400


def test_item_can_be_updated_and_deleted_by_payer(client):
    check = create_check(
        client,
        60001,
        "Плательщик",
        [{"name": "Старое название", "price": 100, "type": "shared"}],
    )
    item_id = check["items"][0]["id"]
    headers = auth_headers(60001, "Плательщик")

    update_response = client.patch(
        f"/checks/items/{item_id}",
        headers=headers,
        json={
            "name": "Новое название",
            "price": 125,
            "type": "single",
        },
    )
    get_response = client.get(f"/checks/{check['id']}")

    assert update_response.status_code == 200
    assert get_response.status_code == 200
    assert get_response.json()["items"][0]["name"] == "Новое название"
    assert get_response.json()["items"][0]["price"] == 125

    delete_response = client.delete(
        f"/checks/items/{item_id}",
        headers=headers,
    )
    get_after_delete = client.get(f"/checks/{check['id']}")

    assert delete_response.status_code == 200
    assert get_after_delete.status_code == 200
    assert get_after_delete.json()["items"] == []