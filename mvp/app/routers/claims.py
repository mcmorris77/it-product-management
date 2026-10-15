from fastapi import APIRouter, Header, HTTPException
from .. import calculator, crud, schemas

router = APIRouter(tags=["claims"])

def get_current_user(x_user_id: int) -> dict:
    user = crud.get_user(x_user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user

@router.post("/items/{item_id}/claim")
def claim_item(item_id: int, x_user_id:int = Header()):
    user = get_current_user(x_user_id)

    item = crud.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Позиция не найдена")

    check = crud.get_check(item["check_id"])
    if check["status"] == "closed":
        raise HTTPException(status_code=400, detail="Чек закрыт")

    if crud.get_claim(item_id, user["id"]) is not None:
        return {"status": "already_claimed"}

    claims = crud.get_item_claims(item_id)
    if item["type"] == "single" and len(claims) > 0:
        raise HTTPException(status_code=409, detail="Эту позицию уже взял другой человек")

    crud.create_claims(item_id, user["id"])
    return {"status": "claimed"}

@router.delete("/items/{item_id}/claim")
def unclaim_item(item_id: int, x_user_id: int = Header()):
    user = get_current_user(x_user_id)

    item = crud.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Позиция не найдена")

    check = crud.get_check(item["check_id"])
    if check["status"] == "closed":
        raise HTTPException(status_code=400, detail="Чек закрыт")

    crud.delete_claim(item_id, user["id"])
    return{"status": "unclaimed"}

@router.get("/checks/{check_id}/summary", response_model=schemas.SummaryOut)
def get_summary(check_id: int):
    check = crud.get_check(check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Чек не найден")
    items = crud.get_check_with_items(check_id)
    claims = crud.get_check_claims(check_id)
    result = calculator.calculate(items, claims)

    names = crud.get_users_names(list(result["totals"].keys()))
    totals = []
    for user_id, amount in result["totals"].items():
        totals.append({
            "user_id": user_id,
            "name": names.get(user_id, "?"),
            "amount": amount,
        })

    return {
        "check_id": check_id,
        "check_total": sum(item["price"] for item in items),
        "totals": totals,
        "unclaimed_items": result["unclaimed_items"],
    }

@router.get("/checks/{check_id}/me", response_model=schemas.MeOut)
def get_me(check_id: int, x_user_id: int = Header()):
    user = get_current_user(x_user_id)

    check = crud.get_check(check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Чек не найден")

    items = crud.get_check_with_items(check_id)
    claims =  crud.get_check_claims(check_id)
    result =  calculator.calculate(items, claims)

    return {
        "amount": result["totals"].get(user[id], 0),
        "is_payer": check["payer_id"] == user["id"],
        "payment_info": check["payment_info"]
    }

