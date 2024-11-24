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
from pretty_html_table import build_table
import numpy as np
from django.db import connection
from psycopg2.extras import Json
from tasks.models import Statistic
import pprint
from projects.utils import ocr_word_count

from projects.models import (
    Project,
    ANNOTATION_STAGE,
    REVIEW_STAGE,
    SUPERCHECK_STAGE,
)
from tasks.models import (
    Task,
    Annotation,
    ANNOTATOR_ANNOTATION,
    REVIEWER_ANNOTATION,
    SUPER_CHECKER_ANNOTATION,
)


def checkNoneValue(value):
    if value == None:
        return "0.0"
    return value


def checkLangNone(language):
    if language == None:
        return "Others"
    return language


def upsert_stat(stat_type, org_id, result):
    obj, created = Statistic.objects.update_or_create(
        stat_type=stat_type,
        org_id=org_id,
        defaults={
            "result": result,
        },
    )

    return obj, created


def fetch_task_counts():
    org_ids = [1, 2, 3]
    project_types = [
        "AcousticNormalisedTranscriptionEditing",
        "AudioSegmentation",
        "AudioTranscription",
        "AudioTranscriptionEditing",
        "StandardisedTranscriptionEditing",
        "ContextualSentenceVerification",
        "ContextualSentenceVerificationAndDomainClassification",
        "ContextualTranslationEditing",
        "ConversationTranslation",
        "ConversationTranslationEditing",
        "ConversationVerification",
        "MonolingualTranslation",
        "OCRTranscriptionEditing",
        "SemanticTextualSimilarity_Scale5",
        "SentenceSplitting",
        "TranslationEditing",
    ]

    with connection.cursor() as cursor:

        for org in org_ids:

            final_result_for_all__types = {}

            for pjt_type in project_types:

                sql_query = f"""
                        with annotation_tasks (language,count) as 
                        (
                        SELECT
                            pjt.tgt_language,
                            count(tsk.id)
                        FROM
                            tasks_task AS tsk,
                            projects_project AS pjt
                        WHERE
                            tsk.project_id_id = pjt.id
                            AND tsk.task_status in ('annotated','reviewed','super_checked')
                            AND pjt.project_type in ('{pjt_type}')
                            AND pjt.organization_id_id = {org}
                        GROUP BY
                            pjt.tgt_language
                        ),reviewer_tasks (language,count) as 
                        (
                        SELECT
                            pjt.tgt_language,
                            count(tsk.id)
                        FROM
                            tasks_task AS tsk,
                            projects_project AS pjt
                        WHERE
                            tsk.project_id_id = pjt.id
                            AND tsk.task_status in ('reviewed','super_checked')
                            AND pjt.project_stage in (2,3)
                            AND pjt.project_type in ('{pjt_type}')
                            AND pjt.organization_id_id = {org}
                        GROUP BY
                            pjt.tgt_language
                        )
                        ,superchecker_tasks (language,count) as 
                        (
                        SELECT
                            pjt.tgt_language,
                            count(tsk.id)
                        FROM
                            tasks_task AS tsk,
                            projects_project AS pjt
                        WHERE
                            tsk.project_id_id = pjt.id
                            AND tsk.task_status in ('super_checked')
                            AND pjt.project_stage in (3)
                            AND pjt.project_type in ('{pjt_type}')
                            AND pjt.organization_id_id = {org}
                        GROUP BY
                            pjt.tgt_language
                        ),
                        annotation_tasks_exported (language,count) as 
                        (
                        SELECT
                            pjt.tgt_language,
                            count(tsk.id)
                        FROM
                            tasks_task AS tsk,
                            projects_project AS pjt
                        WHERE
                            tsk.project_id_id = pjt.id
                            AND tsk.task_status in ('exported')
                            AND pjt.project_stage in (1)
                            AND pjt.project_type in ('{pjt_type}')
                            AND pjt.organization_id_id = {org}
                        GROUP BY
                            pjt.tgt_language
                        ), reviewer_tasks_exported (language,count) as 
                        (
                        SELECT
                            pjt.tgt_language,
                            count(tsk.id)
                        FROM
                            tasks_task AS tsk,
                            projects_project AS pjt
                        WHERE
                            tsk.project_id_id = pjt.id
                            AND tsk.task_status in ('exported')
                            AND pjt.project_stage in (2)
                            AND pjt.project_type in ('{pjt_type}')
                            AND pjt.organization_id_id = {org}
                        GROUP BY
                            pjt.tgt_language
                        ), supercheck_tasks_exported (language,count) as 
                        (
                        SELECT
                            pjt.tgt_language,
                            count(tsk.id)
                        FROM
                            tasks_task AS tsk,
                            projects_project AS pjt
                        WHERE
                            tsk.project_id_id = pjt.id
                            AND tsk.task_status in ('exported')
                            AND pjt.project_stage in (3)
                            AND pjt.project_type in ('{pjt_type}')
                            AND pjt.organization_id_id = {org}
                        GROUP BY
                            pjt.tgt_language
                        ),
                        reviewer_tasks_count (language,count,tag) as (
                        SELECT 
                            language,
                            SUM(count) as task_count,
                            'rew'
                        FROM (
                            SELECT language, count FROM reviewer_tasks
                            UNION ALL
                            SELECT language, count FROM reviewer_tasks_exported
                            UNION ALL
                            SELECT language, count FROM supercheck_tasks_exported
                        ) AS merged_tables
                        GROUP BY language
                        ),
                        annotation_tasks_count (language,count,tag) as (
                        SELECT 
                            language,
                            SUM(count) as task_count,
                            'ann'
                        FROM (
                            SELECT language, count FROM annotation_tasks
                            UNION ALL
                            SELECT language, count FROM annotation_tasks_exported
                            UNION ALL
                            SELECT language, count FROM reviewer_tasks_exported
                            UNION ALL
                            SELECT language, count FROM supercheck_tasks_exported
                        ) AS merged_tables
                        GROUP BY language
                        ),
                        supercheck_tasks_count (language,count,tag) as (
                        SELECT 
                            language,
                            SUM(count) as task_count,
                            'sup'
                        FROM (
                            SELECT language, count FROM superchecker_tasks
                            UNION ALL
                            SELECT language, count FROM supercheck_tasks_exported
                        ) AS merged_tables
                        GROUP BY language
                        ),
                        cumulative_task_counts (language,count,tag) as (
                        select language,count,tag from annotation_tasks_count
                        union all
                        select language,count,tag from reviewer_tasks_count
                        union all
                        select language,count,tag from supercheck_tasks_count
                        )
                        SELECT 
                            language,
                            SUM(CASE WHEN tag = 'ann' THEN count ELSE 0 END) AS annotation_count,
                            SUM(CASE WHEN tag = 'rew' THEN count ELSE 0 END) AS reviewer_count,
                            SUM(CASE WHEN tag = 'sup' THEN count ELSE 0 END) AS superchecker_count
                        FROM cumulative_task_counts
                        GROUP BY language;
                    """
                cursor.execute(sql=sql_query)
                result = cursor.fetchall()
                formatted_result = []
                for langResult in result:
                    ann, rev, sup = langResult[1:]
                    formatted_result.append(
                        {
                            "language": checkLangNone(langResult[0]),
                            "ann_cumulative_tasks_count": int(str(ann)),
                            "rew_cumulative_tasks_count": int(str(rev)),
                            "sup_cumulative_tasks_count": int(str(sup)),
                        }
                    )
                final_result_for_all__types[pjt_type] = formatted_result
            upsert_stat("task_count", org, final_result_for_all__types)


def calculate_reports():
    analytics = AnalyticsViewSet()
    proj = Project.objects.all()

    use = User.objects.filter(
        role__in=[User.ANNOTATOR, User.REVIEWER, User.SUPER_CHECKER]
    )

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

    all_supercheckers = [list(proj1.review_supercheckers.all()) for proj1 in proj]
    all_supercheckers_flat_list = [
        num for sublist in all_supercheckers for num in sublist
    ]
    final_superchecker_unique_list = list(set(all_supercheckers_flat_list))
    final_superchecker_unique_list = [
        superchecker
        for superchecker in final_superchecker_unique_list
        if superchecker in use
    ]

    yest_date = f"{(datetime.now() - timedelta(days = 1) ):%Y-%m-%d}"

    final_user_unique_list = list(
        set(
            final_annot_unique_list
            + final_reviewer_unique_list
            + final_superchecker_unique_list
        )
    )  # list of all annotators and reviewers

    for user in final_user_unique_list:
        user1 = User.objects.get(id=user.id)

        if not user1.enable_mail:
            continue

        userId = user.id

        if user in final_annot_unique_list:
            data = {
                "user_id": userId,
                "project_type": "all",
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
                html_table_df_annotation = build_table(
                    df,
                    "orange_light",
                    font_size="medium",
                    text_align="left",
                    width="auto",
                    index=False,
                )

            else:
                html_table_df_annotation = ""

            df1 = pd.DataFrame.from_records(final_data["total_summary"])
            blankIndex = [""] * len(df1)
            df1.index = blankIndex

            html_table_df1_annotation = build_table(
                df1,
                "orange_dark",
                font_size="medium",
                text_align="left",
                width="auto",
                index=False,
            )

        if user in final_reviewer_unique_list:
            data = {
                "user_id": userId,
                "project_type": "all",
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
                html_table_df_review = build_table(
                    df,
                    "green_light",
                    font_size="medium",
                    text_align="left",
                    width="auto",
                    index=False,
                )

            else:
                html_table_df_review = ""

            df1 = pd.DataFrame.from_records(final_data["total_summary"])
            blankIndex = [""] * len(df1)
            df1.index = blankIndex

            html_table_df1_review = build_table(
                df1,
                "green_dark",
                font_size="medium",
                text_align="left",
                width="auto",
                index=False,
            )

        if user in final_superchecker_unique_list:
            data = {
                "user_id": userId,
                "project_type": "all",
                "reports_type": "supercheck",
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
                html_table_df_supercheck = build_table(
                    df,
                    "blue_light",
                    font_size="medium",
                    text_align="left",
                    width="auto",
                    index=False,
                )

            else:
                html_table_df_supercheck = ""

            df1 = pd.DataFrame.from_records(final_data["total_summary"])
            blankIndex = [""] * len(df1)
            df1.index = blankIndex

            html_table_df1_supercheck = build_table(
                df1,
                "blue_dark",
                font_size="medium",
                text_align="left",
                width="auto",
                index=False,
            )

        message = (
            "Dear "
            + str(user.username)
            + ",\n Your progress reports for "
            + f"{(datetime.now() - timedelta(days = 1) ):%d-%m-%Y}"
            + " are ready.\n Thanks for contributing on Shoonya!"
        )

        if (
            user in final_annot_unique_list
            and user in final_reviewer_unique_list
            and user in final_superchecker_unique_list
        ):
            email_to_send = (
                "<p>"
                + message
                + "</p><br><h1><b>Annotation Reports</b></h1>"
                + "<br><h2><b>Total Reports</b></h2>"
                + html_table_df1_annotation
                + "<br><h2><b>Project-wise Reports</b></h2>"
                + html_table_df_annotation
                + "<br><br><hr>"
                + "</p><br><br><h1><b>Review Reports</b></h1>"
                + "<br><h2><b>Total Reports</b></h2>"
                + html_table_df1_review
                + "<br><h2><b>Project-wise Reports</b></h2>"
                + html_table_df_review
                + "<br><br><hr>"
                + "</p><br><br><h1><b>SuperCheck Reports</b></h1>"
                + "<br><h2><b>Total Reports</b></h2>"
                + html_table_df1_supercheck
                + "<br><h2><b>Project-wise Reports</b></h2>"
                + html_table_df_supercheck
            )
        elif user in final_annot_unique_list and user in final_reviewer_unique_list:
            email_to_send = (
                "<p>"
                + message
                + "</p><br><h1><b>Annotation Reports</b></h1>"
                + "<br><h2><b>Total Reports</b></h2>"
                + html_table_df1_annotation
                + "<br><h2><b>Project-wise Reports</b></h2>"
                + html_table_df_annotation
                + "<br><br><hr>"
                + "</p><br><br><h1><b>Review Reports</b></h1>"
                + "<br><h2><b>Total Reports</b></h2>"
                + html_table_df1_review
                + "<br><h2><b>Project-wise Reports</b></h2>"
                + html_table_df_review
            )
        elif user in final_annot_unique_list and user in final_superchecker_unique_list:
            email_to_send = (
                "<p>"
                + message
                + "</p><br><h1><b>Annotation Reports</b></h1>"
                + "<br><h2><b>Total Reports</b></h2>"
                + html_table_df1_annotation
                + "<br><h2><b>Project-wise Reports</b></h2>"
                + html_table_df_annotation
                + "<br><br><hr>"
                + "</p><br><br><h1><b>SuperCheck Reports</b></h1>"
                + "<br><h2><b>Total Reports</b></h2>"
                + html_table_df1_supercheck
                + "<br><h2><b>Project-wise Reports</b></h2>"
                + html_table_df_supercheck
            )
        elif (
            user in final_reviewer_unique_list
            and user in final_superchecker_unique_list
        ):
            email_to_send = (
                "<p>"
                + message
                + "</p><br><h1><b>Review Reports</b></h1>"
                + "<br><h2><b>Total Reports</b></h2>"
                + html_table_df1_review
                + "<br><h2><b>Project-wise Reports</b></h2>"
                + html_table_df_review
                + "<br><br><hr>"
                + "</p><br><br><h1><b>SuperCheck Reports</b></h1>"
                + "<br><h2><b>Total Reports</b></h2>"
                + html_table_df1_supercheck
                + "<br><h2><b>Project-wise Reports</b></h2>"
                + html_table_df_supercheck
            )
        elif user in final_annot_unique_list:
            email_to_send = (
                "<p>"
                + message
                + "</p><br><h><b>Total Reports</b></h>"
                + html_table_df1_annotation
                + "<br><h><b>Project-wise Reports</b></h>"
                + html_table_df_annotation
            )
        elif user in final_superchecker_unique_list:
            email_to_send = (
                "<p>"
                + message
                + "</p><br><h><b>Total Reports</b></h>"
                + html_table_df1_supercheck
                + "<br><h><b>Project-wise Reports</b></h>"
                + html_table_df_supercheck
            )
        else:
            email_to_send = (
                "<p>"
                + message
                + "</p><br><h><b>Total Reports</b></h>"
                + html_table_df1_review
                + "<br><h><b>Project-wise Reports</b></h>"
                + html_table_df_review
            )

        send_mail(
            "Daily Annotation and Review Reports",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=email_to_send,
        )


def fetch_conversation_dataset_stats():

    org_ids = [1, 2, 3]

    project_types = [
        "ConversationTranslation",
        "ConversationTranslationEditing",
        "ContextualTranslationEditing",
    ]

    with connection.cursor() as cursor:

        for org in org_ids:

            final_result_for_all__types = {}

            for pjt_type in project_types:

                stat_query = f"""
                                WITH
                                    ANN_WORD_COUNTS (LANGUAGE, ANN_CUMULATIVE_WORD_COUNT) AS (
                                        SELECT
                                            PJT.TGT_LANGUAGE,
                                            SUM(CAST(TSK.DATA -> 'word_count' AS INTEGER)) AS WORD_COUNT
                                        FROM
                                            TASKS_TASK AS TSK
                                            JOIN PROJECTS_PROJECT AS PJT ON PJT.ID = TSK.PROJECT_ID_ID
                                        WHERE
                                            PJT.PROJECT_TYPE IN ('{pjt_type}')
                                            AND TSK.TASK_STATUS IN ('annotated', 'reviewed', 'super_checked')
                                            AND PJT.ORGANIZATION_ID_ID = {org}
                                        GROUP BY
                                            PJT.TGT_LANGUAGE
                                    ),
                                    REV_WORD_COUNTS (LANGUAGE, REW_CUMULATIVE_WORD_COUNT) AS (
                                        SELECT
                                            PJT.TGT_LANGUAGE,
                                            SUM(CAST(TSK.DATA -> 'word_count' AS INTEGER)) AS WORD_COUNT
                                        FROM
                                            TASKS_TASK AS TSK
                                            JOIN PROJECTS_PROJECT AS PJT ON PJT.ID = TSK.PROJECT_ID_ID
                                        WHERE
                                            PJT.PROJECT_TYPE IN ('{pjt_type}')
                                            AND TSK.TASK_STATUS IN ('reviewed', 'super_checked')
                                            AND PJT.PROJECT_STAGE IN (2, 3)
                                            AND PJT.ORGANIZATION_ID_ID = {org}
                                        GROUP BY
                                            PJT.TGT_LANGUAGE
                                    ),
                                    ANN_SENTENCE_COUNTS (LANGUAGE, TOTAL_ANN_SENTENCE_COUNT) AS (
                                        SELECT
                                            PJT.TGT_LANGUAGE,
                                            SUM(CAST(TSK.DATA -> 'sentence_count' AS INTEGER)) AS WORD_COUNT
                                        FROM
                                            TASKS_TASK AS TSK
                                            JOIN PROJECTS_PROJECT AS PJT ON PJT.ID = TSK.PROJECT_ID_ID
                                        WHERE
                                            PJT.PROJECT_TYPE IN ('{pjt_type}')
                                            AND TSK.TASK_STATUS IN ('annotated', 'reviewed', 'super_checked')
                                            AND PJT.ORGANIZATION_ID_ID = {org}
                                        GROUP BY
                                            PJT.TGT_LANGUAGE
                                    ),
                                    REV_SENTENCE_COUNTS (LANGUAGE, TOTAL_REV_SENTENCE_COUNT) AS (
                                        SELECT
                                            PJT.TGT_LANGUAGE,
                                            SUM(CAST(TSK.DATA -> 'sentence_count' AS INTEGER)) AS WORD_COUNT
                                        FROM
                                            TASKS_TASK AS TSK
                                            JOIN PROJECTS_PROJECT AS PJT ON PJT.ID = TSK.PROJECT_ID_ID
                                        WHERE
                                            PJT.PROJECT_TYPE IN ('{pjt_type}')
                                            AND TSK.TASK_STATUS IN ('reviewed', 'super_checked')
                                            AND PJT.PROJECT_STAGE IN (2, 3)
                                            AND PJT.ORGANIZATION_ID_ID = {org}
                                        GROUP BY
                                            PJT.TGT_LANGUAGE
                                    )
                                SELECT
                                    COALESCE(
                                        AWCS.LANGUAGE,
                                        RWCS.LANGUAGE,
                                        ASCS.LANGUAGE,
                                        RSCS.LANGUAGE
                                    ) AS LANGUAGE,
                                    COALESCE(AWCS.ANN_CUMULATIVE_WORD_COUNT, 0) AS ANN_CUMULATIVE_WORD_COUNT,
                                    COALESCE(RWCS.REW_CUMULATIVE_WORD_COUNT, 0) AS REW_CUMULATIVE_WORD_COUNT,
                                    COALESCE(ASCS.TOTAL_ANN_SENTENCE_COUNT, 0) AS TOTAL_ANN_SENTENCE_COUNT,
                                    COALESCE(RSCS.TOTAL_REV_SENTENCE_COUNT, 0) AS TOTAL_REV_SENTENCE_COUNT
                                FROM
                                    ANN_WORD_COUNTS AWCS
                                    FULL OUTER JOIN REV_WORD_COUNTS RWCS ON AWCS.LANGUAGE = RWCS.LANGUAGE
                                    FULL OUTER JOIN ANN_SENTENCE_COUNTS ASCS ON COALESCE(AWCS.LANGUAGE, RWCS.LANGUAGE) = ASCS.LANGUAGE
                                    FULL OUTER JOIN REV_SENTENCE_COUNTS RSCS ON COALESCE(AWCS.LANGUAGE, RWCS.LANGUAGE, ASCS.LANGUAGE) = RSCS.LANGUAGE;
                                """
                cursor.execute(sql=stat_query)
                result = cursor.fetchall()
                formatted_result = []
                for langResult in result:
                    awc, rwc, asc, rsc = langResult[1:]
                    formatted_result.append(
                        {
                            "language": checkLangNone(langResult[0]),
                            "ann_cumulative_word_count": int(str(awc)),
                            "rew_cumulative_word_count": int(str(rwc)),
                            "total_rev_sentance_count": int(str(asc)),
                            "total_ann_sentance_count": int(str(rsc)),
                        }
                    )
                final_result_for_all__types[pjt_type] = formatted_result
            upsert_stat("conversation_meta_stats", org, final_result_for_all__types)


def fetch_translation_dataset_stats():

    org_ids = [1, 2, 3]

    project_types = [
        "MonolingualTranslation",
        "TranslationEditing",
        "SemanticTextualSimilarity_Scale5",
    ]

    with connection.cursor() as cursor:

        for org in org_ids:

            final_result_for_all__types = {}

            for pjt_type in project_types:

                stat_query = f"""
                                WITH
                                    ANN_WORD_COUNTS (LANGUAGE, ANN_CUMULATIVE_WORD_COUNT) AS (
                                        SELECT
                                            PJT.TGT_LANGUAGE,
                                            SUM(CAST(TSK.DATA -> 'word_count' AS INTEGER)) AS WORD_COUNT
                                        FROM
                                            TASKS_TASK AS TSK
                                            JOIN PROJECTS_PROJECT AS PJT ON PJT.ID = TSK.PROJECT_ID_ID
                                        WHERE
                                            PJT.PROJECT_TYPE IN ('{pjt_type}')
                                            AND TSK.TASK_STATUS IN ('annotated', 'reviewed', 'super_checked')
                                            AND PJT.ORGANIZATION_ID_ID = {org}
                                        GROUP BY
                                            PJT.TGT_LANGUAGE
                                    ),
                                    REV_WORD_COUNTS (LANGUAGE, REW_CUMULATIVE_WORD_COUNT) AS (
                                        SELECT
                                            PJT.TGT_LANGUAGE,
                                            SUM(CAST(TSK.DATA -> 'word_count' AS INTEGER)) AS WORD_COUNT
                                        FROM
                                            TASKS_TASK AS TSK
                                            JOIN PROJECTS_PROJECT AS PJT ON PJT.ID = TSK.PROJECT_ID_ID
                                        WHERE
                                            PJT.PROJECT_TYPE IN ('{pjt_type}')
                                            AND TSK.TASK_STATUS IN ('reviewed', 'super_checked')
                                            AND PJT.PROJECT_STAGE IN (2, 3)
                                            AND PJT.ORGANIZATION_ID_ID = {org}
                                        GROUP BY
                                            PJT.TGT_LANGUAGE
                                    )
                                SELECT
                                    COALESCE(AWCS.LANGUAGE, RWCS.LANGUAGE) AS LANGUAGE,
                                    COALESCE(AWCS.ANN_CUMULATIVE_WORD_COUNT, 0) AS ANN_CUMULATIVE_WORD_COUNT,
                                    COALESCE(RWCS.REW_CUMULATIVE_WORD_COUNT, 0) AS REW_CUMULATIVE_WORD_COUNT
                                FROM
                                    ANN_WORD_COUNTS AWCS
                                    FULL OUTER JOIN REV_WORD_COUNTS RWCS ON AWCS.LANGUAGE = RWCS.LANGUAGE
                                """
                cursor.execute(sql=stat_query)
                result = cursor.fetchall()
                formatted_result = []
                for langResult in result:
                    awc, rwc = langResult[1:]
                    formatted_result.append(
                        {
                            "language": checkLangNone(langResult[0]),
                            "ann_cumulative_word_count": int(str(awc)),
                            "rew_cumulative_word_count": int(str(rwc)),
                        }
                    )
                final_result_for_all__types[pjt_type] = formatted_result
            upsert_stat("translation_meta_stats", org, final_result_for_all__types)


def fetch_ocr_dataset_stats():

    org_ids = [1, 2, 3]

    project_types = ["OCRTranscription", "OCRTranscriptionEditing"]

    for org in org_ids:

        final_result_for_all__types = {}

        for pjt_type in project_types:

            proj_objs = Project.objects.filter(
                organization_id=org, project_type=pjt_type
            )

            result = []
            languages = list(set([proj.tgt_language for proj in proj_objs]))

            for lang in languages:
                proj_lang_filter = proj_objs.filter(tgt_language=lang)
                annotation_tasks = Task.objects.filter(
                    project_id__in=proj_lang_filter,
                    task_status__in=[
                        "annotated",
                        "reviewed",
                        "super_checked",
                    ],
                )
                reviewer_tasks = Task.objects.filter(
                    project_id__in=proj_lang_filter,
                    project_id__project_stage__in=[REVIEW_STAGE, SUPERCHECK_STAGE],
                    task_status__in=["reviewed", "super_checked"],
                )

                total_rev_word_count = 0
                total_computed_rev_word_count = 0

                for each_task in reviewer_tasks:
                    if each_task.task_status == "reviewed":
                        anno = Annotation.objects.filter(
                            task=each_task,
                            annotation_type=REVIEWER_ANNOTATION,
                        )[0]
                    elif each_task.task_status == "super_checked":
                        anno = Annotation.objects.filter(
                            task=each_task,
                            annotation_type=SUPER_CHECKER_ANNOTATION,
                        )[0]
                    else:
                        anno = each_task.correct_annotation
                    total_rev_word_count += ocr_word_count(anno.result)
                    try:
                        total_computed_rev_word_count += anno.meta_stats["word_count"]
                    except:
                        pass

                total_anno_word_count = 0
                total_computed_anno_word_count = 0

                for each_task in annotation_tasks:
                    if each_task.task_status == "reviewed":
                        anno = Annotation.objects.filter(
                            task=each_task,
                            annotation_type=REVIEWER_ANNOTATION,
                        )[0]
                    elif each_task.task_status == "exported":
                        anno = each_task.correct_annotation
                    elif each_task.task_status == "super_checked":
                        anno = Annotation.objects.filter(
                            task=each_task,
                            annotation_type=SUPER_CHECKER_ANNOTATION,
                        )[0]
                    else:
                        anno = Annotation.objects.filter(
                            task=each_task,
                            annotation_type=ANNOTATOR_ANNOTATION,
                        )[0]
                    total_anno_word_count += ocr_word_count(anno.result)
                    try:
                        total_computed_anno_word_count += anno.meta_stats["word_count"]
                    except:
                        pass

                result.append(
                    {
                        "language": checkLangNone(lang),
                        "ann_ocr_cumulative_word_count": total_anno_word_count,
                        "rew_ocr_cumulative_word_count": total_rev_word_count,
                    }
                )

            final_result_for_all__types[pjt_type] = result
        upsert_stat("ocr_meta_stats", org, final_result_for_all__types)
