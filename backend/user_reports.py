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
from projects.utils import convert_seconds_to_hours


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


def set_raw_duration(org_ids, project_types):

    with connection.cursor() as cursor:

        for org in org_ids:

            final_result_for_all__types = {}

            for pjt_type in project_types:

                sql_query = f"""
                            with annotation_tasks (language,raw_duration) as 
                            (
                            select pjt.tgt_language as language,sum(cast(tsk.data->'audio_duration' as float)) as raw_duration
                            from tasks_task as tsk 
                            join projects_project as pjt on pjt.id=tsk.project_id_id
                            where pjt.project_type in ('{pjt_type}')
                            and tsk.task_status in ('annotated','reviewed','super_checked')
                            and pjt.organization_id_id = {org}
                            group by pjt.tgt_language
                            ),
                            reviewer_tasks (language,raw_duration) as (
                            select pjt.tgt_language as language,sum(cast(tsk.data->'audio_duration' as float)) as raw_duration
                            from tasks_annotation as ta 
                            join tasks_task as tsk on tsk.id=ta.task_id
                            join projects_project as pjt on pjt.id=tsk.project_id_id
                            where pjt.project_type in ('{pjt_type}')
                            and tsk.task_status in ('reviewed','super_checked')
                            and pjt.project_stage in (2,3)
                            and pjt.organization_id_id = {org}
                            group by pjt.tgt_language
                            ),
                            superchecker_tasks (language,raw_duration) as (
                            select pjt.tgt_language as language,sum(cast(tsk.data->'audio_duration' as float)) as raw_duration
                            from tasks_annotation as ta 
                            join tasks_task as tsk on tsk.id=ta.task_id
                            join projects_project as pjt on pjt.id=tsk.project_id_id
                            where pjt.project_type in ('{pjt_type}')
                            and tsk.task_status in ('super_checked')
                            and pjt.project_stage in (3)
                            and pjt.organization_id_id = {org}
                            group by pjt.tgt_language
                            ),
                            annotation_tasks_exported (language,raw_duration) as (
                            select pjt.tgt_language as language,sum(cast(tsk.data->'audio_duration' as float)) as raw_duration
                            from tasks_annotation as ta 
                            join tasks_task as tsk on tsk.id=ta.task_id
                            join projects_project as pjt on pjt.id=tsk.project_id_id
                            where pjt.project_type in ('{pjt_type}')
                            AND tsk.task_status in ('exported')
                            AND pjt.project_stage in (1)
                            and pjt.organization_id_id = {org}
                            group by pjt.tgt_language
                            ),
                            reviewer_tasks_exported (language,raw_duration) as (
                            select pjt.tgt_language as language,sum(cast(tsk.data->'audio_duration' as float)) as raw_duration
                            from tasks_annotation as ta 
                            join tasks_task as tsk on tsk.id=ta.task_id
                            join projects_project as pjt on pjt.id=tsk.project_id_id
                            where pjt.project_type in ('{pjt_type}')
                            AND tsk.task_status in ('exported')
                            AND pjt.project_stage in (2)
                            and pjt.organization_id_id = {org}
                            group by pjt.tgt_language
                            ),
                            supercheck_tasks_exported (language,raw_duration) as (
                            select pjt.tgt_language as language,sum(cast(tsk.data->'audio_duration' as float)) as raw_duration
                            from tasks_annotation as ta 
                            join tasks_task as tsk on tsk.id=ta.task_id
                            join projects_project as pjt on pjt.id=tsk.project_id_id
                            where pjt.project_type in ('{pjt_type}')
                            AND tsk.task_status in ('exported')
                            AND pjt.project_stage in (3)
                            and pjt.organization_id_id = {org}
                            group by pjt.tgt_language
                            ),
                            reviewer_raw_duration (language,raw_duration,tag) as (
                            SELECT 
                                language,
                                SUM(raw_duration) as raw_duration,
                                'rew'
                            FROM (
                                SELECT language, raw_duration FROM reviewer_tasks
                                UNION ALL
                                SELECT language, raw_duration FROM reviewer_tasks_exported
                                UNION ALL
                                SELECT language, raw_duration FROM supercheck_tasks_exported
                            ) AS merged_tables
                            GROUP BY language
                            ),
                            annotation_raw_duration (language,raw_duration,tag) as (
                            SELECT 
                                language,
                                SUM(raw_duration) as raw_duration,
                                'ann'
                            FROM (
                                SELECT language, raw_duration FROM annotation_tasks
                                UNION ALL
                                SELECT language, raw_duration FROM annotation_tasks_exported
                                UNION ALL
                                SELECT language, raw_duration FROM reviewer_tasks_exported
                                UNION ALL
                                SELECT language, raw_duration FROM supercheck_tasks_exported
                            ) AS merged_tables
                            GROUP BY language
                            ),
                            supercheck_raw_duration (language,raw_duration,tag) as (
                            SELECT 
                                language,
                                SUM(raw_duration) as raw_duration,
                                'sup'
                            FROM (
                                SELECT language, raw_duration FROM superchecker_tasks
                                UNION ALL
                                SELECT language, raw_duration FROM supercheck_tasks_exported
                            ) AS merged_tables
                            GROUP BY language
                            ),
                            cumulative_raw_durations (language,raw_duration,tag) as (
                            select language,raw_duration,tag from annotation_raw_duration
                            union all
                            select language,raw_duration,tag from reviewer_raw_duration
                            union all
                            select language,raw_duration,tag from supercheck_raw_duration
                            )
                            SELECT 
                                language,
                                SUM(CASE WHEN tag = 'ann' THEN raw_duration ELSE 0 END) AS annotation_raw_duration,
                                SUM(CASE WHEN tag = 'rew' THEN raw_duration ELSE 0 END) AS reviewer_raw_duration,
                                SUM(CASE WHEN tag = 'sup' THEN raw_duration ELSE 0 END) AS superchecker_raw_duration
                            FROM cumulative_raw_durations
                            GROUP BY language;
                            """

                cursor.execute(sql=sql_query)
                result = cursor.fetchall()
                formatted_result = []
                for langResult in result:

                    ann, rev, sup = langResult[1:]
                    ann, rev, sup = (
                        checkNoneValue(ann),
                        checkNoneValue(rev),
                        checkNoneValue(sup),
                    )

                    formatted_result.append(
                        {
                            "language": checkLangNone(langResult[0]),
                            "ann_raw_aud_duration": convert_seconds_to_hours(
                                float(str(ann))
                            ),
                            "rev_raw_aud_duration": convert_seconds_to_hours(
                                float(str(rev))
                            ),
                            "sup_raw_aud_duration": convert_seconds_to_hours(
                                float(str(sup))
                            ),
                        }
                    )
                final_result_for_all__types[pjt_type] = formatted_result
            upsert_stat("raw_duration", org, final_result_for_all__types)


def set_meta_stats(org_ids, project_types, stat_types):

    # org_ids = [1, 2, 3]

    # project_types = [
    #     "ConversationTranslation",
    #     "ConversationTranslationEditing",
    #     "ConversationVerification",
    # ]

    # stat_types = ["word_count", "sentence_count"]

    with connection.cursor() as cursor:

        for org in org_ids:

            for stat_type in stat_types:

                final_result_for_all__types = {}

                for pjt_type in project_types:

                    sql_query = f"""
                                    with annotation_tasks (language,{stat_type}) as 
                                    (
                                    select pjt.tgt_language as language,sum(cast(ta.meta_stats->'{stat_type}' as float)) as {stat_type}
                                    from tasks_annotation as ta 
                                    join tasks_task as tsk on tsk.id=ta.task_id
                                    join projects_project as pjt on pjt.id=tsk.project_id_id
                                    where pjt.project_type in ('{pjt_type}')
                                    and tsk.task_status in ('annotated','reviewed','super_checked')
                                    and pjt.organization_id_id = {org}
                                    group by pjt.tgt_language
                                    ),
                                    reviewer_tasks (language,{stat_type}) as (
                                    select pjt.tgt_language as language,sum(cast(ta.meta_stats->'{stat_type}' as float)) as {stat_type}
                                    from tasks_annotation as ta 
                                    join tasks_task as tsk on tsk.id=ta.task_id
                                    join projects_project as pjt on pjt.id=tsk.project_id_id
                                    where pjt.project_type in ('{pjt_type}')
                                    and tsk.task_status in ('reviewed','super_checked')
                                    and pjt.project_stage in (2,3)
                                    and pjt.organization_id_id = {org}
                                    group by pjt.tgt_language
                                    ),
                                    superchecker_tasks (language,{stat_type}) as (
                                    select pjt.tgt_language as language,sum(cast(ta.meta_stats->'{stat_type}' as float)) as {stat_type}
                                    from tasks_annotation as ta 
                                    join tasks_task as tsk on tsk.id=ta.task_id
                                    join projects_project as pjt on pjt.id=tsk.project_id_id
                                    where pjt.project_type in ('{pjt_type}')
                                    and tsk.task_status in ('super_checked')
                                    and pjt.project_stage in (3)
                                    and pjt.organization_id_id = {org}
                                    group by pjt.tgt_language
                                    ),
                                    annotation_tasks_exported (language,{stat_type}) as (
                                    select pjt.tgt_language as language,sum(cast(ta.meta_stats->'{stat_type}' as float)) as {stat_type}
                                    from tasks_annotation as ta 
                                    join tasks_task as tsk on tsk.id=ta.task_id
                                    join projects_project as pjt on pjt.id=tsk.project_id_id
                                    where pjt.project_type in ('{pjt_type}')
                                    AND tsk.task_status in ('exported')
                                    AND pjt.project_stage in (1)
                                    and pjt.organization_id_id = {org}
                                    group by pjt.tgt_language
                                    ),
                                    reviewer_tasks_exported (language,{stat_type}) as (
                                    select pjt.tgt_language as language,sum(cast(ta.meta_stats->'{stat_type}' as float)) as {stat_type}
                                    from tasks_annotation as ta 
                                    join tasks_task as tsk on tsk.id=ta.task_id
                                    join projects_project as pjt on pjt.id=tsk.project_id_id
                                    where pjt.project_type in ('{pjt_type}')
                                    AND tsk.task_status in ('exported')
                                    AND pjt.project_stage in (2)
                                    and pjt.organization_id_id = {org}
                                    group by pjt.tgt_language
                                    ),
                                    supercheck_tasks_exported (language,{stat_type}) as (
                                    select pjt.tgt_language as language,sum(cast(ta.meta_stats->'{stat_type}' as float)) as {stat_type}
                                    from tasks_annotation as ta 
                                    join tasks_task as tsk on tsk.id=ta.task_id
                                    join projects_project as pjt on pjt.id=tsk.project_id_id
                                    where pjt.project_type in ('{pjt_type}')
                                    AND tsk.task_status in ('exported')
                                    AND pjt.project_stage in (3)
                                    and pjt.organization_id_id = {org}
                                    group by pjt.tgt_language
                                    ),
                                    reviewer_{stat_type} (language,{stat_type},tag) as (
                                    SELECT 
                                        language,
                                        SUM({stat_type}) as {stat_type},
                                        'rew'
                                    FROM (
                                        SELECT language, {stat_type} FROM reviewer_tasks
                                        UNION ALL
                                        SELECT language, {stat_type} FROM reviewer_tasks_exported
                                        UNION ALL
                                        SELECT language, {stat_type} FROM supercheck_tasks_exported
                                    ) AS merged_tables
                                    GROUP BY language
                                    ),
                                    annotation_{stat_type} (language,{stat_type},tag) as (
                                    SELECT 
                                        language,
                                        SUM({stat_type}) as {stat_type},
                                        'ann'
                                    FROM (
                                        SELECT language, {stat_type} FROM annotation_tasks
                                        UNION ALL
                                        SELECT language, {stat_type} FROM annotation_tasks_exported
                                        UNION ALL
                                        SELECT language, {stat_type} FROM reviewer_tasks_exported
                                        UNION ALL
                                        SELECT language, {stat_type} FROM supercheck_tasks_exported
                                    ) AS merged_tables
                                    GROUP BY language
                                    ),
                                    supercheck_{stat_type} (language,{stat_type},tag) as (
                                    SELECT 
                                        language,
                                        SUM({stat_type}) as {stat_type},
                                        'sup'
                                    FROM (
                                        SELECT language, {stat_type} FROM superchecker_tasks
                                        UNION ALL
                                        SELECT language, {stat_type} FROM supercheck_tasks_exported
                                    ) AS merged_tables
                                    GROUP BY language
                                    ),
                                    cumulative_{stat_type}s (language,{stat_type},tag) as (
                                    select language,{stat_type},tag from annotation_{stat_type}
                                    union all
                                    select language,{stat_type},tag from reviewer_{stat_type}
                                    union all
                                    select language,{stat_type},tag from supercheck_{stat_type}
                                    )
                                    SELECT 
                                        language,
                                        SUM(CASE WHEN tag = 'ann' THEN {stat_type} ELSE 0 END) AS annotation_{stat_type},
                                        SUM(CASE WHEN tag = 'rew' THEN {stat_type} ELSE 0 END) AS reviewer_{stat_type},
                                        SUM(CASE WHEN tag = 'sup' THEN {stat_type} ELSE 0 END) AS superchecker_{stat_type}
                                    FROM cumulative_{stat_type}s
                                    GROUP BY language;
                                """
                    cursor.execute(sql=sql_query)
                    result = cursor.fetchall()
                    formatted_result = []
                    for langResult in result:
                        ann, rev, sup = langResult[1:]
                        ann, rev, sup = (
                            checkNoneValue(ann),
                            checkNoneValue(rev),
                            checkNoneValue(sup),
                        )
                        if stat_type == "word_count":
                            formatted_result.append(
                                {
                                    "language": checkLangNone(langResult[0]),
                                    "ann_cumulative_word_count": int(float(str(ann))),
                                    "rew_cumulative_word_count": int(float(str(rev))),
                                    "sup_cumulative_word_count": int(float(str(sup))),
                                }
                            )
                        elif stat_type == "sentence_count":
                            formatted_result.append(
                                {
                                    "language": checkLangNone(langResult[0]),
                                    "total_ann_sentence_count": int(float(str(ann))),
                                    "total_rev_sentence_count": int(float(str(rev))),
                                    "total_sup_sentence_count": int(float(str(sup))),
                                }
                            )

                        elif stat_type == "audio_word_count":
                            formatted_result.append(
                                {
                                    "language": checkLangNone(langResult[0]),
                                    "ann_audio_word_count": int(float(str(ann))),
                                    "rev_audio_word_count": int(float(str(rev))),
                                    "sup_audio_word_count": int(float(str(sup))),
                                }
                            )

                        elif stat_type == "total_segment_duration":
                            formatted_result.append(
                                {
                                    "language": checkLangNone(langResult[0]),
                                    "ann_total_segment_duration": float(str(ann)),
                                    "rev_total_segment_duration": float(str(rev)),
                                    "sup_total_segment_duration": float(str(sup)),
                                }
                            )
                        elif stat_type == "not_null_segment_duration":
                            formatted_result.append(
                                {
                                    "language": checkLangNone(langResult[0]),
                                    "ann_not_null_segment_duration": float(str(ann)),
                                    "rev_not_null_segment_duration": float(str(rev)),
                                    "sup_not_null_segment_duration": float(str(sup)),
                                }
                            )
                        elif stat_type == "transcribed_duration":
                            formatted_result.append(
                                {
                                    "language": checkLangNone(langResult[0]),
                                    "ann_transcribed_duration": float(str(ann)),
                                    "rev_transcribed_duration": float(str(rev)),
                                    "sup_transcribed_duration": float(str(sup)),
                                }
                            )
                        elif stat_type == "verbatim_duration":
                            formatted_result.append(
                                {
                                    "language": checkLangNone(langResult[0]),
                                    "ann_verbatim_duration": float(str(ann)),
                                    "rev_verbatim_duration": float(str(rev)),
                                    "sup_verbatim_duration": float(str(sup)),
                                }
                            )
                        elif stat_type == "verbatim_word_count":
                            formatted_result.append(
                                {
                                    "language": checkLangNone(langResult[0]),
                                    "ann_verbatim_word_count": float(str(ann)),
                                    "rev_verbatim_word_count": float(str(rev)),
                                    "sup_verbatim_word_count": float(str(sup)),
                                }
                            )
                        elif stat_type == "acoustic_normalised_duration":
                            formatted_result.append(
                                {
                                    "language": checkLangNone(langResult[0]),
                                    "ann_acoustic_normalised_duration": float(str(ann)),
                                    "rev_acoustic_normalised_duration": float(str(rev)),
                                    "sup_acoustic_normalised_duration": float(str(sup)),
                                }
                            )
                        elif stat_type == "acoustic_normalised_word_count":
                            formatted_result.append(
                                {
                                    "language": checkLangNone(langResult[0]),
                                    "ann_acoustic_normalised_word_count": float(
                                        str(ann)
                                    ),
                                    "rev_acoustic_normalised_word_count": float(
                                        str(rev)
                                    ),
                                    "sup_acoustic_normalised_word_count": float(
                                        str(sup)
                                    ),
                                }
                            )
                    final_result_for_all__types[pjt_type] = formatted_result
                upsert_stat(stat_type, org, final_result_for_all__types)


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
