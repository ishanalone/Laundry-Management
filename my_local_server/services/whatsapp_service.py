import requests
import os
from dotenv import load_dotenv

load_dotenv()

class WhatsAppService:
    def __init__(self):
        self.api_url = "https://graph.facebook.com/v17.0"
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")

    def send_message(self, to_phone, message):
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": to_phone,
                "type": "text",
                "text": {"body": message}
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                f"{self.api_url}/{self.phone_number_id}/messages",
                json=payload,
                headers=headers
            )
            return response.json()
        except Exception as e:
            print(f"Error sending WhatsApp message: {str(e)}")
            return None

    def send_template_message(self, to_phone, template_name, language_code="en", components=None):
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": to_phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": language_code
                    }
                }
            }

            if components:
                payload["template"]["components"] = components

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                f"{self.api_url}/{self.phone_number_id}/messages",
                json=payload,
                headers=headers
            )
            return response.json()
        except Exception as e:
            print(f"Error sending template message: {str(e)}")
            return None 