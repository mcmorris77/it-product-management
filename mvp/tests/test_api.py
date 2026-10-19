import pytest
from fastapi.testclient import TestClient
from app import crud
from app.database import create_tables


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    В database.py путь к SQLite относительный,
    поэтому тестовая база создастся внутри временной папки.
    """
    monkeypatch.chdir(tmp_path)
    create_tables()

    # main.py тоже вызывает create_tables() при импорте.
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def create_user(telegram_id: int, name: str) -> int:
    return crud.create_user(telegram_id, name)


def create_check(client, payer_id: int, items: list[dict]) -> dict:
    response = client.post(
        "/checks/",
        json={
            "payer_id": payer_id,
            "title": "Тестовый чек",
            "payment_info": "Тестовые реквизиты",
            "items": items,
        },
    )

    assert response.status_code == 200
    return response.json()


def test_health_and_missing_check(client):
    health = client.get("/health")
    missing_check = client.get("/checks/999999")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    assert missing_check.status_code == 404


def test_summary_returns_claimed_amount_and_unclaimed_items(client):
    payer_id = create_user(10001, "Плательщик")
    eater_id = create_user(10002, "Участник")

    check = create_check(
        client,
        payer_id,
        [
            {"name": "Общее блюдо", "price": 101, "type": "shared"},
            {"name": "Десерт", "price": 250, "type": "single"},
        ],
    )

    shared_item_id = check["items"][0]["id"]

    claim_response = client.post(
        f"/items/{shared_item_id}/claim",
        headers={"X-User-Id": str(eater_id)},
    )
    summary_response = client.get(f"/checks/{check['id']}/summary")

    assert claim_response.status_code == 200
    assert summary_response.status_code == 200

    summary = summary_response.json()
    assert summary["check_total"] == 351
    assert summary["totals"] == [
        {
            "user_id": eater_id,
            "name": "Участник",
            "amount": 101,
        }
    ]
    assert [item["name"] for item in summary["unclaimed_items"]] == ["Десерт"]


def test_me_returns_current_users_amount(client):
    user_id = create_user(20001, "Участник")

    check = create_check(
        client,
        user_id,
        [
            {"name": "Общее блюдо", "price": 101, "type": "shared"},
            {"name": "Десерт", "price": 250, "type": "single"},
        ],
    )

    for item in check["items"]:
        response = client.post(
            f"/items/{item['id']}/claim",
            headers={"X-User-Id": str(user_id)},
        )
        assert response.status_code == 200

    me_response = client.get(
        f"/checks/{check['id']}/me",
        headers={"X-User-Id": str(user_id)},
    )

    assert me_response.status_code == 200
    assert me_response.json() == {
        "amount": 351,
        "is_payer": True,
        "payment_info": "Тестовые реквизиты",
    }


def test_unclaim_removes_claim_from_summary(client):
    payer_id = create_user(30001, "Плательщик")
    eater_id = create_user(30002, "Участник")

    check = create_check(
        client,
        payer_id,
        [{"name": "Общее блюдо", "price": 101, "type": "shared"}],
    )
    item_id = check["items"][0]["id"]
    headers = {"X-User-Id": str(eater_id)}

    claim_response = client.post(f"/items/{item_id}/claim", headers=headers)
    unclaim_response = client.delete(f"/items/{item_id}/claim", headers=headers)
    summary_response = client.get(f"/checks/{check['id']}/summary")

    assert claim_response.status_code == 200
    assert unclaim_response.status_code == 200
    assert summary_response.status_code == 200

    summary = summary_response.json()
    assert summary["totals"] == []
    assert [item["name"] for item in summary["unclaimed_items"]] == [
        "Общее блюдо"
    ]


def test_single_item_can_be_claimed_only_once(client):
    payer_id = create_user(40001, "Плательщик")
    first_user_id = create_user(40002, "Первый участник")
    second_user_id = create_user(40003, "Второй участник")

    check = create_check(
        client,
        payer_id,
        [{"name": "Индивидуальное блюдо", "price": 250, "type": "single"}],
    )
    item_id = check["items"][0]["id"]

    first_response = client.post(
        f"/items/{item_id}/claim",
        headers={"X-User-Id": str(first_user_id)},
    )
    second_response = client.post(
        f"/items/{item_id}/claim",
        headers={"X-User-Id": str(second_user_id)},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409


def test_closed_check_rejects_claim(client):
    payer_id = create_user(50001, "Плательщик")

    check = create_check(
        client,
        payer_id,
        [{"name": "Общее блюдо", "price": 101, "type": "shared"}],
    )
    item_id = check["items"][0]["id"]

    close_response = client.post(f"/checks/{check['id']}/close")
    claim_response = client.post(
        f"/items/{item_id}/claim",
        headers={"X-User-Id": str(payer_id)},
    )

    assert close_response.status_code == 200
    assert claim_response.status_code == 400


def test_item_can_be_updated_and_deleted(client):
    payer_id = create_user(60001, "Плательщик")

    check = create_check(
        client,
        payer_id,
        [{"name": "Старое название", "price": 100, "type": "shared"}],
    )
    item_id = check["items"][0]["id"]

    update_response = client.patch(
        f"/checks/items/{item_id}",
        json={"name": "Новое название", "price": 125, "type": "single"},
    )
    get_response = client.get(f"/checks/{check['id']}")

    assert update_response.status_code == 200
    assert get_response.status_code == 200
    assert get_response.json()["items"][0]["name"] == "Новое название"
    assert get_response.json()["items"][0]["price"] == 125

    delete_response = client.delete(f"/checks/items/{item_id}")
    get_after_delete = client.get(f"/checks/{check['id']}")

    assert delete_response.status_code == 200
    assert get_after_delete.status_code == 200
    assert get_after_delete.json()["items"] == []