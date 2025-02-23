from app.workflow.graph import create_workflow
from app.models.state import GraphState

def test_fibonacci_animation():
    # Create initial state
    initial_state = GraphState(
        user_input="add 2 numbers",
        plan=None,
        generated_code=None,
        execution_result=None,
        error=None,
        current_stage="plan",
        correction_attempts=0
    )
    
    # Create workflow
    workflow = create_workflow()
    
    # Execute workflow
    final_state = workflow.invoke(initial_state)
    
    # Print results
    print("\nFinal State:")
    print(f"Current Stage: {final_state['current_stage']}")
    print(f"Error: {final_state.get('error')}")
    print(f"Correction Attempts: {final_state['correction_attempts']}")
    if final_state.get('execution_result'):
        print(f"Video URL: {final_state['execution_result'].get('video_url')}")

if __name__ == "__main__":
    test_fibonacci_animation() 