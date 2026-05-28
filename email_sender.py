import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.email_config import EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT

def send_unlock_email(to_email, unlock_link):
    """
    Sends an account unlock email to the user with a secure, time-bound link.
    """
    subject = "SecuAuthX Account Unlock Notification"
    body = f"""
    <html>
        <body>
            <p>Hello,</p>
            <p>We have detected multiple failed login attempts on your SecuAuthX account.</p>
            <p>To unlock your account, please click the link below:</p>
            <p><a href="{unlock_link}">{unlock_link}</a></p>
            <p><strong>Note:</strong> This link will expire in 15 minutes for your security.</p>
            <p>If you did not attempt to log in, please ignore this email or contact support immediately.</p>
            <br>
            <p>Regards,<br>SecuAuthX Security Team</p>
        </body>
    </html>
    """

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = f"SecuAuthX Security <{EMAIL_ADDRESS}>"  # Better sender format
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    # Send the email via SMTP
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
            print(f"[INFO] Unlock email sent successfully to {to_email}")
    except Exception as e:
        print(f"[ERROR] Failed to send unlock email to {to_email}: {e}")