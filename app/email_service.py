import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger("email_service")
logger.setLevel(logging.INFO)

def send_email_notification(to_email: str, subject: str, content: str):
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("FROM_EMAIL", "no-reply@example.com")
    
    # If SendGrid is not configured, simulate email sending.
    if not sendgrid_api_key:
        logger.warning("SendGrid is not configured. Skipping email send.")
        print(f"Simulating email to {to_email} with subject '{subject}'")
        return None

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        plain_text_content=content
    )
    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        logger.info(f"Email sent: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        # Instead of raising the exception, simply return None
        return None

def send_email(recipient: str, subject: str, body: str) -> None:
    """
    Stub function to send email notifications.
    
    TODO: Replace this stub with actual SendGrid integration.
    This function should be harmless if SendGrid is not configured.
    """
    try:
        # For now, just log the email sending attempt.
        logger.info(f"Sending email to {recipient}: Subject: {subject} - Body: {body}")
        # TODO: Integrate SendGrid email sending.
    except Exception as e:
        logger.error(f"Failed to send email: {e}") 