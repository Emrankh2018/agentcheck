"""Future adapter boundary; no live integrations or tool execution are included."""

from typing import Protocol

from .models import Trace


class TraceAdapter(Protocol):
    """Convert a recorded local artifact into the validated canonical Trace.

    Implementations should parse recorded data only, preserve scenario IDs and
    call ordering, and return Trace (which validates the canonical schema).
    Never execute recorded tool calls or infer missing calls. Adapters own
    source-specific parsing; evaluate() owns all scoring decisions.
    """

    def to_trace(self) -> Trace:
        """Return a validated trace from an implementation's recorded artifact."""
        ...
