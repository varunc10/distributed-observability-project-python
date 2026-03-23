from fastapi import FastAPI, HTTPException
from schema import OrderRequest
from db_mongo import orders_collection
from service4.src.service4.db_mongo import user_collection
import uvicorn

app = FastAPI()

@app.post("/api/v1/tracing/service4")
async def create_order(request: OrderRequest):
    try:
        user = await user_collection.find_one({"order_id": request.user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        order = {
            "order_number": request.order_id,
            "user_id": user.user_id,
        }
        await orders_collection.insert_one(order)

        return {"message": "order created"}
    except Exception as e:
        raise e

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
