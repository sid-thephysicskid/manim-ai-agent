import pytest
import importlib.util
from pathlib import Path
from app.workflow.graph import workflow
from app.workflow.nodes import plan_scenes, generate_code
from app.core.config import BASE_DIR
from unittest.mock import patch, MagicMock

@pytest.mark.integration
class TestWorkflowIntegration:
    def test_template_imports(self):
        """Test that template files can be imported without errors."""
        gcf_path = BASE_DIR / "app" / "templates" / "examples" / "gcf.py"
        spec = importlib.util.spec_from_file_location("gcf", gcf_path)
        gcf_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gcf_module)
        
        assert hasattr(gcf_module, "GCFCalculationScene")
        scene = gcf_module.GCFCalculationScene()
        assert hasattr(scene, "construct")

    @patch('app.workflow.nodes.client')
    def test_workflow_node_integration(self, mock_client):
        """Test workflow nodes work together."""
        # Mock OpenAI response for planning
        mock_client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content="Test plan"))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content=self.get_valid_code()))])
        ]
        
        state = {
            "user_input": "What is the GCF of 18 and 24?",
            "current_stage": "plan",
            "correction_attempts": 0
        }
        
        # Test plan generation
        state = plan_scenes(state)
        assert state["plan"] is not None
        assert "error" not in state
        
        # Test code generation
        state = generate_code(state)
        assert state["generated_code"] is not None
        assert "error" not in state

    def get_valid_code(self):
        """Helper to get valid test code."""
        return """
from manim import *
from manim_voiceover import VoiceoverScene

class GCFScene(VoiceoverScene):
    def construct(self):
        with self.voiceover(text="Let's calculate the GCF"):
            self.play(Write(Text("GCF")))
        self.clear()
"""

@pytest.mark.integration
def test_workflow_execution():
    """Test complete workflow execution."""
    # Test code here 