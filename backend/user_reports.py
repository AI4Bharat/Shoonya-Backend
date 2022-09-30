import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shoonya_backend.settings")
django.setup()
import schedule
import requests
import time
from requests.auth import HTTPBasicAuth
import json
from users.models import User
from projects.models import Project
from datetime import datetime, timedelta
from users.views import AnalyticsViewSet
from django.db.models import Q
import pandas as pd
from django.core.mail import send_mail
from django.conf import settings


def caluculate_reports():
    analytics = AnalyticsViewSet()
    proj = Project.objects.all()

    use = User.objects.filter(Q(role=1) | Q(role=2))

    all_annotators = [list(proj1.annotators.all()) for proj1 in proj]
    all_annotators_flat_list = [num for sublist in all_annotators for num in sublist]
    final_annot_unique_list = list(set(all_annotators_flat_list))
    final_annot_unique_list = [
        annot for annot in final_annot_unique_list if annot in use
    ]

    all_reviewers = [list(proj1.annotation_reviewers.all()) for proj1 in proj]
    all_reviewers_flat_list = [num for sublist in all_reviewers for num in sublist]
    final_reviewer_unique_list = list(set(all_reviewers_flat_list))
    final_reviewer_unique_list = [
        reviewer for reviewer in final_reviewer_unique_list if reviewer in use
    ]

    yest_date = f"{(datetime.now() - timedelta(days = 1) ):%Y-%m-%d}"
    for annotator in final_annot_unique_list:

        user1 = User.objects.get(id=annotator.id)

        if not user1.enable_mail:
            continue

        userId = annotator.id
        data = {
            "user_id": userId,
            "project_type": "ContextualTranslationEditing",
            "reports_type": "annotation",
            "start_date": yest_date,
            "end_date": yest_date,
        }
        try:
            res = analytics.get_user_analytics(data)
        except:
            continue

        final_data = res.data
        if "total_summary" not in final_data or "project_summary" not in final_data:
            continue

        if len(final_data["project_summary"]) > 0:

            df = pd.DataFrame.from_records(final_data["project_summary"])
            blankIndex = [""] * len(df)
            df.index = blankIndex
        else:

            df = "NO projects selected"

        df1 = pd.DataFrame.from_records(final_data["total_summary"], index=[0])
        blankIndex = [""] * len(df1)
        df1.index = blankIndex
        email_to_send = {"ProjectWiseReport": df, "Total Reports Summary": df1}

        # print(email_to_send)

        send_mail(
            "Your Annotation Reports",
            f"Your Annotation Reports are:{email_to_send}",
            settings.DEFAULT_FROM_EMAIL,
            [annotator.email],
        )

    for reviewer in final_reviewer_unique_list:

        user1 = User.objects.get(id=reviewer.id)

        if not user1.enable_mail:
            continue

        userId = reviewer.id
        data = {
            "user_id": userId,
            "project_type": "ContextualTranslationEditing",
            "reports_type": "review",
            "start_date": yest_date,
            "end_date": yest_date,
        }
        try:
            res = analytics.get_user_analytics(data)
        except:
            continue

        final_data = res.data
        if "total_summary" not in final_data or "project_summary" not in final_data:
            continue
        if len(final_data["project_summary"]) > 0:

            df = pd.DataFrame.from_records(final_data["project_summary"])
            blankIndex = [""] * len(df)
            df.index = blankIndex
        else:

            df = "NO projects selected"

        df1 = pd.DataFrame.from_records(final_data["total_summary"], index=[0])
        blankIndex = [""] * len(df1)
        df1.index = blankIndex
        email_to_send = {"ProjectWiseReport": df, "Total Reports Summary": df1}

        # print(email_to_send)

        send_mail(
            "Your Review Reports",
            f"Your Review Reports are:{email_to_send}",
            settings.DEFAULT_FROM_EMAIL,
            [reviewer.email],
        )
