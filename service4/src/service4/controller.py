import logging
import time

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from db_mongo import orders_collection
from schema import OrderRequest
from service4.src.service4.db_mongo import user_collection

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

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["service", "method", "endpoint"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency", ["service", "endpoint"]
)

ERROR_COUNT = Counter(
    "http_errors_total","Total errors",["service", "endpoint"]
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    try:
        return await call_next(request)
    except Exception as e:
        ERROR_COUNT.labels("service3", request.scope.get("route").path).inc()
        logger.error(e)
        raise e
    finally:
        latency = time.time() - start_time

        REQUEST_COUNT.labels(
            service="service3", method=request.method, endpoint=request.scope.get("route").path
        ).inc()

        REQUEST_LATENCY.labels(
            service="service3", endpoint=request.scope.get("route").path
        ).observe(latency)

@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

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
