import json
import uuid
import time
import random
import logging
from contextvars import ContextVar
from kafka import KafkaProducer
from logging import Handler, LogRecord
from fastapi import Request, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

try:
    producer = KafkaProducer(
        bootstrap_servers="localhost:29092",
        value_serializer=lambda v: v.encode("utf-8"),
    )
    KAFKA_TOPIC = "logs"
    print("[KafkaSetup] Producer connection established successfully.")
except Exception as e:
    print(f"[KafkaSetup] Producer not available the error is: {e}")
    producer = None


trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


class KafkaLoggingHandler(Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.producer = producer
        self.topic = KAFKA_TOPIC

    def emit(self, record: LogRecord):
        if not self.producer:
            return
        try:
            log_message = self.format(record)
            self.producer.send(self.topic, value=log_message)
        except Exception:
            self.handleError(record)


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = service_name

    def format(self, record: LogRecord) -> str:
        trace_id = trace_id_var.get()

        if random.random() < 0.1:
            cpu_usage = round(random.uniform(85.0, 99.0), 2)
            time.sleep(random.randint(4, 15))
        else:
            cpu_usage = round(random.uniform(5.0, 30.0), 2)

        if random.random() < 0.05:
            mem_usage = round(random.uniform(90.0, 98.0), 2)
            time.sleep(random.randint(4, 15))
        else:
            mem_usage = round(random.uniform(20.0, 50.0), 2)

        mock_metrics = {
            "cpu_percent": cpu_usage,
            "memory_percent": mem_usage,
        }
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "service": self.service_name,
            "level": record.levelname,
            "trace_id": trace_id,
            "message": record.getMessage(),
            "logger_name": record.name,
            "funcName": record.funcName,
            "metrics": mock_metrics,
        }
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)

        log_data = json.dumps(log_data, indent=4, ensure_ascii=False)
        return log_data


def setup_logging(service_name: str):
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    kafka_handler = KafkaLoggingHandler()
    kafka_handler.setFormatter(JsonFormatter(service_name=service_name))
    logger.addHandler(kafka_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JsonFormatter(service_name=service_name))
    logger.addHandler(console_handler)


class UnifiedLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, service_name: str, *args, **kwargs):
        self.service_name = service_name
        BaseHTTPMiddleware.__init__(self, app, *args, **kwargs)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())

        token = trace_id_var.set(trace_id)

        logger = logging.getLogger(self.service_name)
        logger.info(f"Request {request.method} {request.url.path} started")

        status_code = None
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            logger.error("Unhandled exception", exc_info=True)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000

            level = logging.INFO
            if not status_code or status_code >= 500:
                level = logging.ERROR
            elif status_code >= 400:
                level = logging.WARNING

            logger.log(
                level,
                f"Response {status_code} {request.method} {request.url.path} finished in {duration_ms:.2f}ms",
            )

            trace_id_var.reset(token)

        response.headers["X-Trace-ID"] = trace_id
        return response
