from fastapi import APIRouter, Depends, HTTPException
from .. import calculator, crud, schemas
from ..auth import get_current_user

router = APIRouter(tags=["claims"])

@router.post("/items/{item_id}/claim")
def claim_item(item_id: int, user: dict = Depends(get_current_user)):

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
def unclaim_item(item_id: int, user: dict = Depends(get_current_user)):

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
    check_with_items = crud.get_check_with_items(check_id)
    items = check_with_items["items"]
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
def get_me(check_id: int, user = Depends(get_current_user)):

    check = crud.get_check(check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Чек не найден")
    check_with_items = crud.get_check_with_items(check_id)
    items = check_with_items["items"]
    claims =  crud.get_check_claims(check_id)
    result =  calculator.calculate(items, claims)

    return {
        "amount": result["totals"].get(user["id"], 0),
        "is_payer": check["payer_id"] == user["id"],
        "payment_info": check["payment_info"]
    }

@router.get("/checks/{check_id}/state")
def get_state(check_id: int, user: dict = Depends(get_current_user)):
    check = crud.get_check(check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Чек не найден")
    items = crud.get_check_items(check_id)
    claims = crud.get_check_claims(check_id)

    result = []
    for item in items:
        item_claims = [c for c in claims if c["item_id"] == item["id"]]
        item["claims_count"] = len(item_claims)
        item["mine"] = any(c["user_id"] == user["id"] for c in item_claims)
        result.append(item)

    return {
        "id": check["id"],
        "title": check["title"],
        "status": check["status"],
        "is_payer": check["payer_id"] == user["id"],
        "items": result,
    }
