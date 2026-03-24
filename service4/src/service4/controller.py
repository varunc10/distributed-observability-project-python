import logging

import uvicorn
from fastapi import FastAPI, HTTPException, Request

from db_mongo import orders_collection
from schema import OrderRequest
from service4.src.service4.db_mongo import user_collection

app = FastAPI()
from observability import setup_logging

logger = logging.getLogger(__name__)

@app.post("/api/v1/tracing/service4")
async def create_order(request: OrderRequest, raw_request: Request):
    logger.info("Received request", extra={
            "headers": dict(raw_request.headers),
            "path": raw_request.url.path,
            "method": raw_request.method,
        }
    )
    try:
        logger.info("Fetching user", extra={"user_id": request.user_id})
        user = await user_collection.find_one({"order_id": request.user_id})
        if not user:
            logger.warning("No user", extra={"user_id": request.user_id})
            raise HTTPException(status_code=404, detail="User not found")

        order = {
            "order_number": request.order_id,
            "user_id": user.user_id,
        }
        await orders_collection.insert_one(order)

        logger.info(
            "Order created successfully",
            extra={
                "user_id": request.userId
            }
        )

        return {"message": "order created"}
    except Exception as e:
        logger.error(
            "Order creation failed",
            extra={
                "error": str(e),
                "user_id": request.user_id,
            }
        )
        raise e

if __name__ == "__main__":
    setup_logging()
    uvicorn.run(app, host="0.0.0.0", port=8004)
