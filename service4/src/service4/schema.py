from pydantic import BaseModel

class OrderRequest(BaseModel):
    orderNumber: str
    userId: int