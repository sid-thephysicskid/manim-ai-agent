import pytest
import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
from pathlib import Path
from app.workflow.graph import workflow
from app.core.config import GENERATED_DIR
from app.workflow.runner import WorkflowRunner
from app.models.state import GraphState

@pytest.mark.e2e
class TestEndToEnd(unittest.TestCase):
    """End-to-end tests for the complete workflow."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_generated_dir = str(GENERATED_DIR)
        os.environ["GENERATED_DIR"] = self.temp_dir
    
    def tearDown(self):
        """Clean up test environment."""
        os.environ["GENERATED_DIR"] = self.original_generated_dir
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete workflow with all stages."""
        with patch('app.workflow.nodes.client') as mock_client, \
             patch('subprocess.run') as mock_run:
            
            mock_client.chat.completions.create.side_effect = [
                MagicMock(choices=[MagicMock(message=MagicMock(content="Test plan"))]),
                MagicMock(choices=[MagicMock(message=MagicMock(content=self.get_valid_code()))])
            ]
            
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Success",
                stderr=""
            )
            
            initial_state = GraphState(
                user_input="What is the GCF of 18 and 24?",
                current_stage="plan",
                correction_attempts=0
            )
            
            runner = WorkflowRunner(initial_state, "test-job-id")
            result = await runner.run()
            
            self.assertIsNone(result.get("error"))
            self.assertIsNotNone(result.get("execution_result"))
        
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test workflow error recovery."""
        with patch('app.workflow.nodes.client') as mock_client:
            # First attempt fails, second succeeds
            mock_client.chat.completions.create.side_effect = [
                MagicMock(choices=[MagicMock(message=MagicMock(content="Test plan"))]),
                MagicMock(choices=[MagicMock(message=MagicMock(content="invalid code"))]),
                MagicMock(choices=[MagicMock(message=MagicMock(content=self.get_valid_code()))])
            ]
            
            initial_state = GraphState(
                user_input="What is the GCF of 18 and 24?",
                current_stage="plan",
                correction_attempts=0
            )
            
            runner = WorkflowRunner(initial_state, "test-job-id")
            result = await runner.run()
            
            self.assertIsNone(result.get("error"))
            self.assertEqual(result["correction_attempts"], 1)
        
    def get_valid_code(self):
        """Return valid Manim code for testing."""
        return '''
from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.openai import OpenAIService

class GCFScene(VoiceoverScene):
    def __init__(self):
        super().__init__()
        self.set_speech_service(OpenAIService(voice="nova"))
    
    def construct(self):
        with self.voiceover(text="Let's find the GCF"):
            self.play(Create(Circle()))
        self.clear()
''' 