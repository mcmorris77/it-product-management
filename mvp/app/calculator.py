def calculate(items: list[dict], claims: list[dict]) -> dict:
    """
    Считает, сколько должен заплатить каждый пользователь.

    :param items: список позиций в чеке
    :param claims: список тех, кто отметился на блюде
    :return: словарь, где по пользователям написано кто сколько должен и
    позиции, которые никто не отметил
    """
    totals = {}
    unclaimed_items = []

    claims_by_item = {}
    for claim in claims:
        item_id = claim["item_id"]
        user_id = claim["user_id"]
        claims_by_item.setdefault(item_id, []).append(user_id)

    for item in items:
        item_id = item["id"]
        price = item["price"]
        eaters = claims_by_item.get(item_id, [])

        if not eaters:
            unclaimed_items.append(item)
            continue

        share = price // len(eaters)
        remainder = price - share * len(eaters)

        for i, user_id in enumerate(eaters):
            amount = share
            if i == 0:
                amount += remainder # остаток копеек отдаём первому в списке
            totals[user_id] = totals.get(user_id, 0) + amount

    return {
        "totals": totals,
        "unclaimed_items": unclaimed_items,
    }
