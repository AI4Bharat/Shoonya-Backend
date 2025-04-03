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
from tasks.models import Statistic
from django.db import connection


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
                "user_id": 1,
                "project_type": "Test Contextual Translation Editing",
                "reports_type": "annotation",
                "start_date": "2025-01-01",
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
            ['sleya7110@gmail.com'],
            html_message=email_to_send,
        )
        break
        
        


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
        "OCRSegmentCategorizationEditing",
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


def fetch_workspace_task_counts():

    sql_query = """
    WITH
	ANNOTATION_TASKS (LANGUAGE, PROJECT_TYPE, WORKSPACE_ID, COUNT) AS (
		SELECT
			PJT.TGT_LANGUAGE,
			PJT.PROJECT_TYPE,
			PJT.WORKSPACE_ID_ID,
			COUNT(TSK.ID)
		FROM
			TASKS_TASK AS TSK,
			PROJECTS_PROJECT AS PJT
		WHERE
			TSK.PROJECT_ID_ID = PJT.ID
			AND TSK.TASK_STATUS IN ('annotated', 'reviewed', 'super_checked')
		GROUP BY
			PJT.TGT_LANGUAGE,
			PJT.PROJECT_TYPE,
			PJT.WORKSPACE_ID_ID
	),
	REVIEWER_TASKS (LANGUAGE, PROJECT_TYPE, WORKSPACE_ID, COUNT) AS (
		SELECT
			PJT.TGT_LANGUAGE,
			PJT.PROJECT_TYPE,
			PJT.WORKSPACE_ID_ID,
			COUNT(TSK.ID)
		FROM
			TASKS_TASK AS TSK,
			PROJECTS_PROJECT AS PJT
		WHERE
			TSK.PROJECT_ID_ID = PJT.ID
			AND TSK.TASK_STATUS IN ('reviewed', 'super_checked')
			AND PJT.PROJECT_STAGE IN (2, 3)
		GROUP BY
			PJT.TGT_LANGUAGE,
			PJT.PROJECT_TYPE,
			PJT.WORKSPACE_ID_ID
	),
	SUPERCHECKER_TASKS (LANGUAGE, PROJECT_TYPE, WORKSPACE_ID, COUNT) AS (
		SELECT
			PJT.TGT_LANGUAGE,
			PJT.PROJECT_TYPE,
			PJT.WORKSPACE_ID_ID,
			COUNT(TSK.ID)
		FROM
			TASKS_TASK AS TSK,
			PROJECTS_PROJECT AS PJT
		WHERE
			TSK.PROJECT_ID_ID = PJT.ID
			AND TSK.TASK_STATUS IN ('super_checked')
			AND PJT.PROJECT_STAGE IN (3)
		GROUP BY
			PJT.TGT_LANGUAGE,
			PJT.PROJECT_TYPE,
			PJT.WORKSPACE_ID_ID
	),
	ANNOTATION_TASKS_EXPORTED (LANGUAGE, PROJECT_TYPE, WORKSPACE_ID, COUNT) AS (
		SELECT
			PJT.TGT_LANGUAGE,
			PJT.PROJECT_TYPE,
			PJT.WORKSPACE_ID_ID,
			COUNT(TSK.ID)
		FROM
			TASKS_TASK AS TSK,
			PROJECTS_PROJECT AS PJT
		WHERE
			TSK.PROJECT_ID_ID = PJT.ID
			AND TSK.TASK_STATUS IN ('exported')
			AND PJT.PROJECT_STAGE IN (1)
		GROUP BY
			PJT.TGT_LANGUAGE,
			PJT.PROJECT_TYPE,
			PJT.WORKSPACE_ID_ID
	),
	REVIEWER_TASKS_EXPORTED (LANGUAGE, PROJECT_TYPE, WORKSPACE_ID, COUNT) AS (
		SELECT
			PJT.TGT_LANGUAGE,
			PJT.PROJECT_TYPE,
			PJT.WORKSPACE_ID_ID,
			COUNT(TSK.ID)
		FROM
			TASKS_TASK AS TSK,
			PROJECTS_PROJECT AS PJT
		WHERE
			TSK.PROJECT_ID_ID = PJT.ID
			AND TSK.TASK_STATUS IN ('exported')
			AND PJT.PROJECT_STAGE IN (2)
		GROUP BY
			PJT.TGT_LANGUAGE,
			PJT.PROJECT_TYPE,
			PJT.WORKSPACE_ID_ID
	),
	SUPERCHECK_TASKS_EXPORTED (LANGUAGE, PROJECT_TYPE, WORKSPACE_ID, COUNT) AS (
		SELECT
			PJT.TGT_LANGUAGE,
			PJT.PROJECT_TYPE,
			PJT.WORKSPACE_ID_ID,
			COUNT(TSK.ID)
		FROM
			TASKS_TASK AS TSK,
			PROJECTS_PROJECT AS PJT
		WHERE
			TSK.PROJECT_ID_ID = PJT.ID
			AND TSK.TASK_STATUS IN ('exported')
			AND PJT.PROJECT_STAGE IN (3)
		GROUP BY
			PJT.TGT_LANGUAGE,
			PJT.PROJECT_TYPE,
			PJT.WORKSPACE_ID_ID
	),
	REVIEWER_TASKS_COUNT (LANGUAGE, PROJECT_TYPE, WORKSPACE_ID, COUNT, TAG) AS (
		SELECT
			LANGUAGE,
			PROJECT_TYPE,
			WORKSPACE_ID,
			SUM(COUNT) AS TASK_COUNT,
			'rew'
		FROM
			(
				SELECT
					LANGUAGE,
					PROJECT_TYPE,
					WORKSPACE_ID,
					COUNT
				FROM
					REVIEWER_TASKS
				UNION ALL
				SELECT
					LANGUAGE,
					PROJECT_TYPE,
					WORKSPACE_ID,
					COUNT
				FROM
					REVIEWER_TASKS_EXPORTED
				UNION ALL
				SELECT
					LANGUAGE,
					PROJECT_TYPE,
					WORKSPACE_ID,
					COUNT
				FROM
					SUPERCHECK_TASKS_EXPORTED
			) AS MERGED_TABLES
		GROUP BY
			LANGUAGE,
			PROJECT_TYPE,
			WORKSPACE_ID
	),
	ANNOTATION_TASKS_COUNT (LANGUAGE, PROJECT_TYPE, WORKSPACE_ID, COUNT, TAG) AS (
		SELECT
			LANGUAGE,
			PROJECT_TYPE,
			WORKSPACE_ID,
			SUM(COUNT) AS TASK_COUNT,
			'ann'
		FROM
			(
				SELECT
					LANGUAGE,
					PROJECT_TYPE,
					WORKSPACE_ID,
					COUNT
				FROM
					ANNOTATION_TASKS
				UNION ALL
				SELECT
					LANGUAGE,
					PROJECT_TYPE,
					WORKSPACE_ID,
					COUNT
				FROM
					ANNOTATION_TASKS_EXPORTED
				UNION ALL
				SELECT
					LANGUAGE,
					PROJECT_TYPE,
					WORKSPACE_ID,
					COUNT
				FROM
					REVIEWER_TASKS_EXPORTED
				UNION ALL
				SELECT
					LANGUAGE,
					PROJECT_TYPE,
					WORKSPACE_ID,
					COUNT
				FROM
					SUPERCHECK_TASKS_EXPORTED
			) AS MERGED_TABLES
		GROUP BY
			LANGUAGE,
			PROJECT_TYPE,
			WORKSPACE_ID
	),
	SUPERCHECK_TASKS_COUNT (LANGUAGE, PROJECT_TYPE, WORKSPACE_ID, COUNT, TAG) AS (
		SELECT
			LANGUAGE,
			PROJECT_TYPE,
			WORKSPACE_ID,
			SUM(COUNT) AS TASK_COUNT,
			'sup'
		FROM
			(
				SELECT
					LANGUAGE,
					PROJECT_TYPE,
					WORKSPACE_ID,
					COUNT
				FROM
					SUPERCHECKER_TASKS
				UNION ALL
				SELECT
					LANGUAGE,
					PROJECT_TYPE,
					WORKSPACE_ID,
					COUNT
				FROM
					SUPERCHECK_TASKS_EXPORTED
			) AS MERGED_TABLES
		GROUP BY
			LANGUAGE,
			PROJECT_TYPE,
			WORKSPACE_ID
	),
	CUMULATIVE_TASK_COUNTS (LANGUAGE, PROJECT_TYPE, WORKSPACE_ID, COUNT, TAG) AS (
		SELECT
			LANGUAGE,
			PROJECT_TYPE,
			WORKSPACE_ID,
			COUNT,
			TAG
		FROM
			ANNOTATION_TASKS_COUNT
		UNION ALL
		SELECT
			LANGUAGE,
			PROJECT_TYPE,
			WORKSPACE_ID,
			COUNT,
			TAG
		FROM
			REVIEWER_TASKS_COUNT
		UNION ALL
		SELECT
			LANGUAGE,
			PROJECT_TYPE,
			WORKSPACE_ID,
			COUNT,
			TAG
		FROM
			SUPERCHECK_TASKS_COUNT
	),
	WORKSPACE_COUNTS (
		WORKSPACE_ID,
		LANGUAGE,
		PROJECT_TYPE,
		ANNOTATION_COUNT,
		REVIEWER_COUNT,
		SUPERCHECKER_COUNT
	) AS (
		SELECT
			CTC.WORKSPACE_ID,
			COALESCE(CTC.LANGUAGE, 'Others'),
			CTC.PROJECT_TYPE,
			SUM(
				CASE
					WHEN TAG = 'ann' THEN CTC.COUNT
					ELSE 0
				END
			) AS ANNOTATION_COUNT,
			SUM(
				CASE
					WHEN TAG = 'rew' THEN CTC.COUNT
					ELSE 0
				END
			) AS REVIEWER_COUNT,
			SUM(
				CASE
					WHEN TAG = 'sup' THEN CTC.COUNT
					ELSE 0
				END
			) AS SUPERCHECKER_COUNT
		FROM
			CUMULATIVE_TASK_COUNTS AS CTC
			JOIN WORKSPACES_WORKSPACE AS WSP ON WSP.ID = CTC.WORKSPACE_ID
		GROUP BY
			CTC.LANGUAGE,
			CTC.PROJECT_TYPE,
			CTC.WORKSPACE_ID,
			WSP.WORKSPACE_NAME
	),
	AGGREGATED_DATA (WORKSPACE_ID, PROJECT_TYPE, PROJECT_DATA) AS (
		SELECT
			WORKSPACE_ID,
			PROJECT_TYPE,
			JSON_AGG(
				JSON_BUILD_OBJECT(
					'language',
					LANGUAGE,
					'ann_cumulative_tasks_count',
					ANNOTATION_COUNT,
					'rew_cumulative_tasks_count',
					REVIEWER_COUNT,
					'sup_cumulative_tasks_count',
					SUPERCHECKER_COUNT
				)
			) AS PROJECT_DATA
		FROM
			WORKSPACE_COUNTS
		GROUP BY
			PROJECT_TYPE,
			WORKSPACE_ID
	),
	WORKSPACE_TASK_COUNTS (WORKSPACE_ID, ORGANIZATION_ID, RESULT) AS (
		SELECT
			ADT.WORKSPACE_ID,
			WSP.ORGANIZATION_ID,
			JSON_OBJECT_AGG(ADT.PROJECT_TYPE, ADT.PROJECT_DATA) AS RESULT
		FROM
			AGGREGATED_DATA AS ADT
			JOIN WORKSPACES_WORKSPACE AS WSP ON WSP.ID = ADT.WORKSPACE_ID
		GROUP BY
			ADT.WORKSPACE_ID,
			WSP.ORGANIZATION_ID
	)
SELECT
	ORGANIZATION_ID,
	JSONB_OBJECT_AGG(WORKSPACE_ID, RESULT) as workspace_task_counts
FROM
	WORKSPACE_TASK_COUNTS
GROUP BY
	ORGANIZATION_ID
    """
    with connection.cursor() as cursor:

        cursor.execute(sql=sql_query)
        result = cursor.fetchall()
        for org_id, workspace_task_counts in result:
            workspace_task_counts = json.loads(workspace_task_counts)
            upsert_stat(
                stat_type="workspace_task_counts",
                org_id=org_id,
                result=workspace_task_counts,
            )
