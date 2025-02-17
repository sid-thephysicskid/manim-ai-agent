import os
import sys
import pytest
from rich.console import Console
from rich.live import Live
from rich.table import Table
from datetime import datetime
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture(scope="session")
def test_console():
    return Console()

@pytest.fixture(autouse=True)
def test_timer():
    start_time = time.time()
    yield
    duration = time.time() - start_time
    return duration

def pytest_configure(config):
    """Add custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "api: API tests")

class TestProgress:
    def __init__(self):
        self.console = Console()
        self.table = Table(show_header=True, header_style="bold magenta")
        self.table.add_column("Category")
        self.table.add_column("Total")
        self.table.add_column("Passed")
        self.table.add_column("Failed")
        self.table.add_column("Duration")
        self.stats = {
            "unit": {"total": 0, "passed": 0, "failed": 0, "duration": 0},
            "integration": {"total": 0, "passed": 0, "failed": 0, "duration": 0},
            "e2e": {"total": 0, "passed": 0, "failed": 0, "duration": 0},
            "api": {"total": 0, "passed": 0, "failed": 0, "duration": 0},
        }
        self.live = None
        # Initialize table with empty rows
        self.refresh_table()

    def start(self):
        """Start the live display"""
        try:
            self.refresh_table()  # Ensure table has rows before starting
            self.live = Live(self.table, refresh_per_second=4)
            self.live.start()
        except Exception:
            self.live = None  # Ensure live is None if start fails

    def stop(self):
        """Stop the live display"""
        if self.live:
            try:
                self.refresh_table()  # Ensure table has rows before stopping
                self.live.stop()
            except Exception:
                pass  # Suppress errors during shutdown
            finally:
                self.live = None

    def refresh_table(self):
        """Refresh the table with current stats"""
        self.table.rows.clear()
        # Always add all categories to ensure table has rows
        for category, stats in self.stats.items():
            self.table.add_row(
                category,
                str(stats["total"]),
                f"[green]{stats['passed']}[/]",
                f"[red]{stats['failed']}[/]",
                f"{stats['duration']:.2f}s"
            )

    def update_stats(self, category, passed, duration):
        """Update test statistics"""
        if category not in self.stats:
            return  # Ignore invalid categories
        self.stats[category]["total"] += 1
        if passed:
            self.stats[category]["passed"] += 1
        else:
            self.stats[category]["failed"] += 1
        self.stats[category]["duration"] += duration
        try:
            self.refresh_table()
        except Exception:
            pass  # Suppress errors during update

test_progress = TestProgress()

@pytest.fixture(scope="session", autouse=True)
def progress_tracker():
    test_progress.start()
    yield test_progress
    test_progress.stop()

def pytest_runtest_logreport(report):
    """Update progress after each test"""
    if report.when == "call":
        # Get markers from the nodeid instead
        test_path = report.nodeid
        marker_found = False
        for marker_name in ["unit", "integration", "e2e", "api"]:
            if marker_name in test_path:
                test_progress.update_stats(
                    marker_name,
                    report.passed,
                    report.duration
                )
                marker_found = True
                break
        
        # If no marker found, assume it's a unit test
        if not marker_found:
            test_progress.update_stats(
                "unit",
                report.passed,
                report.duration
            )

@pytest.fixture
def mock_workflow():
    """Mock the entire workflow process."""
    with patch('app.workflow.nodes.client') as mock_client, \
         patch('subprocess.run') as mock_run, \
         patch('app.workflow.nodes.read_gcf_example') as mock_gcf, \
         patch('app.workflow.nodes.get_manim_api_context') as mock_api:
        
        # Mock OpenAI responses
        mock_client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content="Scene 1: Introduction\nScene 2: Explanation"))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content=get_valid_code()))])
        ]
        
        # Mock subprocess
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Success",
            stderr=""
        )
        
        yield {
            'client': mock_client,
            'run': mock_run,
            'gcf': mock_gcf,
            'api': mock_api
        }

def get_valid_code():
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
