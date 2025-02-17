from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import logging
from app.config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def send_email_notification(to_email: str, subject: str, content: str) -> int:
    """
    Send an email notification using SendGrid.
    
    Parameters:
        to_email (str): The recipient's email address.
        subject (str): The subject for the email.
        content (str): The plain text content of the email.
        
    Returns:
        int: The status code returned by the SendGrid API.
    """
    message = Mail(
        from_email=settings.FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        plain_text_content=content,
    )
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Email sent to {to_email} with status code {response.status_code}")
        return response.status_code
    except Exception as e:
        logger.error("Failed to send email", exc_info=True)
        raise e 