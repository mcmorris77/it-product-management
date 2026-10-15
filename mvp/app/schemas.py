from pydantic import BaseModel
from typing import Optional

class ItemCreate(BaseModel):
    name: str
    price: int
    type: str

class CheckCreate(BaseModel):
    payer_id: int
    title: Optional[str] = None
    payment_info: Optional[str] = None
    items: list[ItemCreate]

class ItemOut(BaseModel):
    id: int
    name: str
    price: int
    type: str

class CheckOut(BaseModel):
    id: int
    payer_id: int
    title: Optional[str]
    payment_info: Optional[str]
    status: str
    items: list[ItemOut]

class UserTotal(BaseModel):
    user_id : int
    name: str
    amount: int

class SummaryOut(BaseModel):
    check_id: int
    check_total: int
    totals: list[UserTotal]
    unclaimed_items: list[ItemOut]

class MeOut(BaseModel):
    amount: int
    is_payer: bool
    payment_info: Optional[str]

