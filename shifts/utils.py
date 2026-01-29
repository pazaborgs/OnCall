# utils.py
import threading
from django.core.mail import EmailMultiAlternatives
from django.conf import settings


class EmailThread(threading.Thread):
    def __init__(
        self, subject, message, recipient_list, html_message=None, bcc_list=None
    ):
        self.subject = subject
        self.message = message
        self.recipient_list = recipient_list
        self.html_message = html_message
        self.bcc_list = bcc_list
        threading.Thread.__init__(self)

    def run(self):
        try:
            # Usamos EmailMultiAlternatives para suportar HTML e BCC
            email = EmailMultiAlternatives(
                subject=self.subject,
                body=self.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=self.recipient_list,
                bcc=self.bcc_list,
            )

            # Se tiver HTML, anexa ele
            if self.html_message:
                email.attach_alternative(self.html_message, "text/html")

            email.send(fail_silently=False)

        except Exception as e:
            # Em produção, idealmente use logging, mas print resolve agora
            print(f"❌ Erro ao enviar email em background: {e}")


def send_email_background(
    subject, message, recipient_list, html_message=None, bcc_list=None
):
    email_thread = EmailThread(subject, message, recipient_list, html_message, bcc_list)
    email_thread.start()
