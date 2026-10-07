from app.utils.email_service import send_email

result = send_email(
    "atuldhanak01@gmail.com",
    "SmartCare Test Email",
    """
    <h2>SmartCare Hospital Management System</h2>
    <p>This is a test email.</p>
    <p>Resend API integration is working successfully.</p>
    """
)

print("Result:", result)