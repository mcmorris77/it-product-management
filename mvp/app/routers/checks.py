from http.client import responses

from fastapi import APIRouter, HTTPException
from .. import crud, schemas

router = APIRouter(prefix="/checks", tags=["checks"])

@router.post("/", response_model=schemas.CheckOut)
def create_check(check: schemas.CheckCreate):
    check_id = crud.create_check_with_items(
        payer_id=check.payer_id,
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
def update_item(item_id: int, item: schemas.ItemCreate):
    crud.update_item(item_id, name=item.name, price=item.price, item_type=item.type)
    return {"status": "updated"}

@router.delete("/items/{item_id}")
def delete_item(item_id: int):
    crud.delete_item(item_id)
    return {"status": "deleted"}

@router.post("/{check_id}/close")
def close_check(check_id):
    crud.close_check(check_id)
    return {"status": "closed"}