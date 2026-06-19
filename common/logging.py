import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    REDACT_KEYS = {"password", "token", "secret", "authorization", "cookie"}

    def format(self, record):
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }
        for key in ("request_id", "user_id", "household_id", "job_id", "error_type"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = str(value)
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False)

