from http.client import responses
from os.path import exists

from fastapi import APIRouter, Depends, HTTPException
from .. import crud, schemas
+from ..auth import get_current_user

router = APIRouter(prefix="/checks", tags=["checks"])

def require_payer(check_id: int, user: dict):
    check = crud.get_check(check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Чек не найден")
    if check["payer_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Это может делать только плательщик")
    return check

@router.post("/", response_model=schemas.CheckOut)
def create_check(check: schemas.CheckCreate, user: dict = Depends(get_current_user)):
    check_id = crud.create_check_with_items(
        payer_id=user["id"],
        title=check.title,
        payment_info=check.payment_info,
        items=check.items
    )
    return crud.get_check_with_items(check_id)

@router.get("/{check_id}", response_model=schemas.CheckOut)
def get_check(check_id: int):
    check = crud.get_check_with_items(check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Чек не найден")
    return check

@router.patch("/items/{item_id}")
def update_item(item_id: int, item: schemas.ItemCreate, user: dict = Depends(get_current_user)):
    existing = crud.get_item(item_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
    require_payer(existing["check_id"], user)
    crud.update_item(item_id, name=item.name, price=item.price, item_type=item.type)
    return {"status": "updated"}

@router.delete("/items/{item_id}")
def delete_item(item_id: int, user: dict = Depends(get_current_user)):
    existing = crud.get_item(item_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
    require_payer(existing["check_id"], user)
    crud.delete_item(item_id)
    return {"status": "deleted"}

@router.post("/{check_id}/close")
def close_check(check_id: int, user: dict = Depends(get_current_user)):
    require_payer(check_id, user)
    crud.close_check(check_id)
    return {"status": "closed"}