# import os
# import requests


# def send_sms(phone, message):
#     api_key = os.getenv("SMS_API_KEY")

#     if not api_key:
#         return False, "SMS API key is not configured"

#     # Your SMS provider API call goes here.
#     # Example:
#     response = requests.post(
#         "YOUR_SMS_PROVIDER_API_URL",
#         headers={
#             "Authorization": f"Bearer {api_key}"
#         },
#         json={
#             "to": phone,
#             "message": message
#         },
#         timeout=15,
#     )

#     if response.ok:
#         return True, "SMS sent successfully"

#     return False, response.text