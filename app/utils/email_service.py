import os
import resend


def send_email(to, subject, html, attachments=None):
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL")

    if not api_key:
        print("RESEND_API_KEY is missing")
        return False

    if not from_email:
        print("RESEND_FROM_EMAIL is missing")
        return False

    if not to:
        print("Recipient email is missing")
        return False

    resend.api_key = api_key

    try:
        email_data = {
            "from": from_email,
            "to": [to],
            "subject": subject,
            "html": html,
        }

        # Add attachments only when provided
        if attachments:
            email_data["attachments"] = attachments

        response = resend.Emails.send(email_data)

        print("Email sent successfully:", response)
        return True

    except Exception as e:
        print("Email sending failed:", e)
        return False