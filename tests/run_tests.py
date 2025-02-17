#!/usr/bin/env python3
import pytest
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from datetime import datetime
import sys
import os

def run_test_category(name, marker):
    """Run tests for a specific category and handle errors."""
    console = Console()
    console.print(f"\n[bold blue]Running {name}[/]")
    
    result = pytest.main([
        "-v",
        f"-m={marker}",
        "--disable-warnings",
        "--asyncio-mode=strict",
        "tests"
    ])
    
    return result == 0  # Return True if tests passed

def main():
    console = Console()
    
    # Print header
    console.print(Panel.fit(
        "[bold magenta]Running Test Suite[/]",
        border_style="blue"
    ))
    
    # Run tests with different markers
    categories = [
        ("Unit Tests", "unit"),
        ("Integration Tests", "integration"),
        ("End-to-End Tests", "e2e"),
        ("API Tests", "api")
    ]
    
    success = True
    for name, marker in categories:
        if not run_test_category(name, marker):
            success = False
            console.print(f"[red]❌ {name} failed[/]")
        else:
            console.print(f"[green]✓ {name} passed[/]")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 