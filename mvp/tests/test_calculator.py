from app.calculator import calculate

def test_single_item_one_eater():
    items = [{"id": 1, "price": 10000, "type": 'single'}]
    claims = [{"item_id": 1, "user_id": 1}]
    result = calculate(items, claims)

    assert result["totals"] == {1: 10000}
    assert result["unclaimed_items"] == []


def test_shared_item_splits():
    items = [{"id": 1, "price": 9000, "type": "shared"}]
    claims = [
        {"item_id": 1, "user_id": 1},
        {"item_id": 1, "user_id": 2},
        {"item_id": 1, "user_id": 3},
    ]
    result = calculate(items, claims)
    assert result["totals"] == {1: 3000, 2: 3000, 3: 3000}
    assert sum(result["totals"].values()) == 9000

def test_shared_item_with_remainder():
    items=[{"id": 1, "price": 10000, "type": "shared"}]
    claims = [
        {"item_id": 1, "user_id": 1},
        {"item_id": 1, "user_id": 2},
        {"item_id": 1, "user_id": 3},
    ]

    result = calculate(items, claims)

    assert result["totals"][1] == 3334
    assert result["totals"][2] == 3333
    assert result["totals"][3] == 3333
    assert sum(result["totals"].values()) == 10000

def test_unclaimed_item():
    items = [{"id": 1, "price": 5000, "type": "single"}]
    claims = []

    result = calculate(items, claims)

    assert result["totals"] == {}
    assert result["unclaimed_items"] == [items[0]]

def test_multiple_items_same_user():
    items = [
        {"id": 1, "price": 5000, "type": "single"},
        {"id": 2, "price": 3000, "type": "single"}
    ]
    claims = [
        {"item_id": 1, "user_id": 1},
        {"item_id": 2, "user_id": 1},
    ]

    result  = calculate(items, claims)

    assert result["totals"] == {1: 8000}