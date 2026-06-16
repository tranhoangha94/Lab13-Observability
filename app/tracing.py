from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

try:
    from langfuse import get_client, observe
except Exception:  # pragma: no cover
    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    def get_client() -> Any:
        class _DummyClient:
            def update_current_trace(self, **kwargs: Any) -> None:
                return None

            def update_current_span(self, **kwargs: Any) -> None:
                return None

            def flush(self) -> None:
                return None

            def shutdown(self) -> None:
                return None

        return _DummyClient()


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def flush_traces() -> None:
    if tracing_enabled():
        get_client().flush()
