from fastapi import FastAPI, HTTPException, Request
from schema import OrderRequest
from db_postgres import SessionLocal
from models import Order, User
import uvicorn
import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from observability import setup_logging

set_global_textmap(TraceContextTextMapPropagator())

# ✅ 1. Define resource (service name)
resource = Resource.create({
    "service.name": "service3"
})

# ✅ 2. Set tracer provider
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

# ✅ 3. Configure exporter (to collector)
otlp_exporter = OTLPSpanExporter(endpoint="localhost:4317", insecure=True)

# ✅ 4. Add span processor
span_processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(span_processor)

# ✅ 5. FastAPI instrumentation
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

logger = logging.getLogger(__name__)

@app.post("/api/v1/tracing/service3")
async def create_order(request: OrderRequest, raw_request: Request):
    logger.info("Received request", extra={
            "headers": dict(raw_request.headers),
            "path": raw_request.url.path,
            "method": raw_request.method,
        }
    )
    session = SessionLocal()

    try:
        logger.info("Fetching user", extra={"user_id": request.userId})
        user = session.query(User).filter(User.id == request.userId).first()
        if not user:
            logger.warning("No user", extra={"user_id": request.userId})
            raise HTTPException(status_code=404, detail="User not found")

        logger.info("Creating order", extra={"order_number": request.orderNumber})
        order = Order(
            order_number=request.orderNumber,
            user=user,
        )
        session.add(order)
        session.commit()
        session.refresh(order)

        logger.info(
            "Order created successfully",
            extra={
                "order_id": order.id,
                "user_id": request.userId
            }
        )

        return {"message": "order created"}
    except Exception as e:
        session.rollback()
        logger.error(
            "Order creation failed",
            extra={
                "error": str(e),
                "user_id": request.userId,
            }
        )
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    setup_logging()
    uvicorn.run(app, host="0.0.0.0", port=8003)