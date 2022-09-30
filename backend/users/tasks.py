from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from celery.schedules import crontab

# from user_reports import caluculate_reports


def send_mail_task():
    # caluculate_reports()
    print("Mail sending.......")
    # subject = "welcome to Celery world"
    # message = "Hi thank you for using celery"
    # email_from = settings.EMAIL_HOST_USER
    # recipient_list = [
    #     "yourmail@gmail.com",
    # ]
    # send_mail(subject, message, email_from, recipient_list)
    # return "Mail has been sent........"
