from whatsapp import WhatsApp
from .config import settings
from typing import Optional

# Initialize WhatsApp client if config is present
messenger = None

if settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID:
    try:
        messenger = WhatsApp(
            token=settings.WHATSAPP_ACCESS_TOKEN,
            phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID
        )
    except Exception as e:
        print(f"Failed to init WhatsApp client: {e}")

def send_whatsapp_message(to_number: str, message: str):
    if not messenger:
        print("WhatsApp client not configured.")
        return False
    
    try:
        # Create a text message
        # whatsapp-python usage standard:
        # messenger.send_message(message="Hello", recipient_id="num")
        # Check docs or type definition if possible.
        # usually: messenger.send_message(message, to_number) 
        # But 'whatsapp-python' lib signature varies.
        # Assuming standard lib 'whatsapp-python' (HeyMilo/filipporomani):
        # messenger.send_message(message, to_number)
        
        # NOTE: 'to_number' must be just digits (e.g. 15550001234)
        messenger.send_message(
            message=message,
            recipient_id=to_number
        )
        return True
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
        return False
