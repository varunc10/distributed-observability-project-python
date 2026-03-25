import logging
import os

from pythonjsonlogger import jsonlogger

from opentelemetry import trace


class TraceContextFilter(logging.Filter):
    """
    Custom filter to inject trace_id and span_id into log records
    from the current OpenTelemetry context.
    """
    def filter(self, record):
        span = trace.get_current_span()
        ctx = span.get_span_context()

        if ctx and ctx.is_valid:
            # Format as 32-char hex (trace) and 16-char hex (span)
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
        else:
            record.trace_id = None
            record.span_id = None
        record.service_name = "service3"

        return True


def setup_logging():
    log_dir = "./logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # File handler
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(os.path.join(log_dir, "python.log"))

    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s %(span_id)s %(service)s",
        rename_fields={"asctime": "@timestamp", "levelname": "level"}
    )

    handler.setFormatter(formatter)
    handler.addFilter(TraceContextFilter())

    logger.addHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(levelname)s [%(trace_id)s] %(message)s'
    ))

    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(TraceContextFilter())

    logger.addHandler(console_handler)