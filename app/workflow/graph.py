from langgraph.graph import StateGraph, END
from app.models.state import GraphState
from app.workflow.nodes import (
    plan_scenes,
    generate_code,
    validate_code,
    execute_code,
    error_correction,
    lint_code
)

def create_workflow() -> StateGraph:
    """Create and return the workflow graph."""
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("plan_scenes", plan_scenes)
    workflow.add_node("generate_code", generate_code)
    workflow.add_node("validate_code", validate_code)
    workflow.add_node("execute_code", execute_code)
    workflow.add_node("correct_code", error_correction)
    workflow.add_node("lint_code", lint_code)
    
    # Set entry point and basic flow
    workflow.set_entry_point("plan_scenes")
    workflow.add_edge("plan_scenes", "generate_code")
    workflow.add_edge("generate_code", "validate_code")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "validate_code",
        lambda state: "correct_code" if state.get("error") else "execute_code",
        {
            "correct_code": "correct_code",
            "execute_code": "execute_code"
        }
    )
    
    workflow.add_conditional_edges(
        "correct_code",
        lambda state: "validate_code" if state["correction_attempts"] < 3 else END,
        {
            "validate_code": "validate_code",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "execute_code",
        lambda state: "correct_code" if (state.get("error") and state["correction_attempts"] < 3) else END,
        {
            "correct_code": "correct_code",
            END: END
        }
    )
    
    return workflow.compile()

# Create the compiled workflow
workflow = create_workflow() 