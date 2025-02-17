from typing import TypedDict, Literal

class GraphState(TypedDict):
    """State model for the Manim workflow graph."""
    user_input: str
    plan: str | None
    generated_code: str | None
    execution_result: dict | None
    error: str | None
    current_stage: Literal['plan', 'code', 'execute', 'correct', 'lint', 'lint_passed']
    correction_attempts: int
