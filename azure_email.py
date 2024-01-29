from azure.communication.email import EmailClient
from config import email_connection_string, sender_address

def send_mail(subject, text, sender, recepient, html_message=None):
    try:
        client = EmailClient.from_connection_string(email_connection_string)

        message = {
            "senderAddress": sender_address,
            "recipients":  {
                "to": [{"address": recepient[0]}],
            },
            "content": {
                "subject": subject,
                "plainText": text,
                "html": html_message
            }
        }

        poller = client.begin_send(message)
        result = poller.result()
    except Exception as ex:
        print(ex)