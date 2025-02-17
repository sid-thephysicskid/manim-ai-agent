import os
import pytest
from app.email_service import send_email_notification

def test_email_service_without_sendgrid(monkeypatch, capsys):
    # Ensure SENDGRID_API_KEY is not set
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    monkeypatch.setenv("FROM_EMAIL", "test@example.com")

    response = send_email_notification("recipient@example.com", "Test Subject", "Test Content")
    captured = capsys.readouterr().out
    assert "Simulating email to recipient@example.com with subject 'Test Subject'" in captured
    assert response is None

def test_email_service_with_invalid_key(monkeypatch):
    # Set an invalid SendGrid key
    monkeypatch.setenv("SENDGRID_API_KEY", "INVALID_KEY")
    monkeypatch.setenv("FROM_EMAIL", "test@example.com")

    # With an invalid key, the error should be handled gracefully.
    response = send_email_notification("recipient@example.com", "Test Subject", "Test Content")
    assert response is None 