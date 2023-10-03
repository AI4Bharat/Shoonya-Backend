from django.shortcuts import render,HttpResponse
from .models import Notification
from users.models import User
from projects.models import Project
import json
from django.db import models
# Create your views here.
def createNotification(request):
    '''this is called after project has published'''
    project_title='Kt project' #project title of pubulished project here
    project=Project.objects.get(title=project_title)
    annotators=[]
    for a in project.annotators.all():
        annotators.append(a.email)
    # print(annotators)
    d={"project": project.title,"description":project.description,"annotators":annotators,"status":f'{200} - notifications sent'}
    notif=Notification(notification_type='Publish Project',title=f'{project_title} has been published.',metadata_json='null')
    notif.save()
    for a_email in annotators:
        try:
            reciever_user=User.objects.get(email=a_email)
            notif.reciever_user_id.add(reciever_user)
        except models.DoesNotExist as e:
            return HttpResponse(f'Bad Request. {a_email} does not exist.')
    response=json.dumps(d,indent=4)
    return HttpResponse(response)

