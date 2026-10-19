"""AgentCheck: deterministic evaluation of recorded agent tool-call traces."""

from .engine import EvaluationReport, evaluate
from .models import Scenario, ToolCall, Trace, ValidationError

__all__ = ["EvaluationReport", "Scenario", "ToolCall", "Trace", "ValidationError", "evaluate"]
__version__ = "0.1.0"
