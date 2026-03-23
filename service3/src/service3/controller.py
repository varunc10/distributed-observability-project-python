from fastapi import FastAPI, HTTPException, Request
from schema import OrderRequest
from db_postgres import SessionLocal
from models import Order, User
import uvicorn

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

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

@app.post("/api/v1/tracing/service3")
async def create_order(request: OrderRequest, raw_request: Request):
    print(f"Incoming Headers: {raw_request.headers}")
    session = SessionLocal()

    try:
        user = session.query(User).filter(User.id == request.userId).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        order = Order(
            order_number=request.orderNumber,
            user=user,
        )
        session.add(order)
        session.commit()
        session.refresh(order)

        return {"message": "order created"}
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)