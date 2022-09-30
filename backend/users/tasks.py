from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from celery.task.schedules import crontab
from celery.decorators import periodic_task
from email_service import send_emails

# this will run every minute, see http://celeryproject.org/docs/reference/celery.task.schedules.html#celery.task.schedules.crontab
@periodic_task(run_every=crontab(hour="*", minute="*", day_of_week="*"))
def send_mail_task():
    print("Mail sending.......")
    # subject = "welcome to Celery world"
    # message = "Hi thank you for using celery"
    # email_from = settings.EMAIL_HOST_USER
    # recipient_list = [
    #     "yourmail@gmail.com",
    # ]
    # send_mail(subject, message, email_from, recipient_list)
    # return "Mail has been sent........"
