"""Resend email helpers for SmartCare."""

import os
import resend


def send_email(to, subject, html, attachments=None):
    """Send a transactional email through Resend.

    Returns the Resend response on success and None on failure. Email failures
    are intentionally isolated from the main database transaction so that a
    notification problem does not undo a successful hospital workflow.

    ``attachments`` should be a list of Resend attachment dictionaries. For
    generated PDFs, use base64-encoded content, for example::

        {
            "filename": "prescription.pdf",
            "content": base64_string,
            "content_type": "application/pdf",
        }
    """
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("MAIL_FROM")

    if not api_key:
        print("Email not sent: RESEND_API_KEY is not configured.")
        return None

    if not sender:
        print("Email not sent: MAIL_FROM is not configured.")
        return None

    if not to:
        print("Email not sent: recipient email is empty.")
        return None

    resend.api_key = api_key

    email_data = {
        "from": sender,
        "to": [to],
        "subject": subject,
        "html": html,
    }

    if attachments:
        email_data["attachments"] = attachments

    try:
        response = resend.Emails.send(email_data)
        print("Email sent successfully:", response)
        return response
    except Exception as exc:
        print("Email sending failed:", exc)
        return None
