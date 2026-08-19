import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import Notification, NotificationType

def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send an email using the configured provider (Console log or SMTP)."""
    if settings.EMAIL_PROVIDER == "console":
        print("\n" + "="*80)
        print(f" [MOCK EMAIL] TO: {to_email}")
        print(f" SUBJECT: {subject}")
        print(f" CONTENT:\n{html_content}")
        print("="*80 + "\n")
        return True
    
    # SMTP Delivery
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email
        
        part = MIMEText(html_content, "html")
        msg.attach(part)
        
        # Connect to SMTP server
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP delivery failed to {to_email}: {str(e)}")
        # Graceful fallback to console logging in development
        if settings.ENV == "development":
            print(f" [Fallback Console Email] TO: {to_email} | SUBJECT: {subject} | {html_content}")
        return False

def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.SYSTEM
) -> Notification:
    """Create an in-app database notification and send a matching email alert."""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    # Send email notification as well
    from app.models.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.email:
        email_body = f"""
        <html>
            <body style="font-family: sans-serif; color: #1C1C1C; background: #FAF9F6; padding: 20px;">
                <h2 style="color: #2D5A27;">{title}</h2>
                <p style="font-size: 16px; line-height: 1.5;">{message}</p>
                <br/>
                <hr style="border: 0; border-top: 1px solid #E7E5E4;"/>
                <p style="font-size: 12px; color: #A8A29E;">
                    This is an automated notification from the Food Redistribution Platform. 
                    You can manage your settings inside your account dashboard.
                </p>
            </body>
        </html>
        """
        send_email(user.email, f"[FoodShare Alert] {title}", email_body)
        
    return notification
