import json
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from tasks.views import TaskViewSet
from users.models import User


# ─── Shared fixtures ──────────────────────────────────────────────────────────

MOCK_BBOXES = [
    {
        "x": 12.5,
        "y": 8.3,
        "width": 74.2,
        "height": 3.1,
        "text": "Sample text",
        "labels": ["Body"],
        "rotation": 0,
        "original_width": 1240,
        "original_height": 1754,
    }
]

MOCK_RAW_JSON = json.dumps(MOCK_BBOXES)


def make_mock_task(task_id=1, input_data_id=10, task_data=None):
    task = MagicMock()
    task.id = task_id
    task.input_data_id = input_data_id
    task.data = task_data or {}
    task.save = MagicMock()
    return task


def make_mock_ocr_document(doc_id=10, image_url="https://example.com/img.png", language="hi"):
    doc = MagicMock()
    doc.id = doc_id
    doc.image_url = image_url
    doc.language = language
    doc.save = MagicMock()
    return doc


# ─── Celery task tests ────────────────────────────────────────────────────────


class TestRegenerateOcrForTask(TestCase):

    @patch("functions.tasks.get_batch_ocr_predictions_using_arena")
    @patch("functions.tasks.dataset_models.OCRDocument.objects.get")
    @patch("functions.tasks.Task.objects.get")
    def test_success_updates_ocr_document_and_task_data(
        self, mock_task_get, mock_doc_get, mock_arena
    ):
        mock_task = make_mock_task()
        mock_doc = make_mock_ocr_document()
        mock_task_get.return_value = mock_task
        mock_doc_get.return_value = mock_doc
        mock_arena.return_value = MOCK_RAW_JSON

        from functions.tasks import regenerate_ocr_for_task

        result = regenerate_ocr_for_task(task_id=1)

        # OCRDocument saved with new json
        mock_doc.save.assert_called_once_with(update_fields=["ocr_prediction_json"])
        self.assertEqual(mock_doc.ocr_prediction_json, MOCK_RAW_JSON)

        # task.data updated with html table
        task_data_written = mock_task.data
        self.assertIn("ocr_prediction_json", task_data_written)
        self.assertIn("text", task_data_written["ocr_prediction_json"])
        self.assertIn("<table>", task_data_written["ocr_prediction_json"]["text"])
        mock_task.save.assert_called_once_with(update_fields=["data"])

        self.assertIn("1 bboxes", result)

    @patch("functions.tasks.Task.objects.get")
    def test_missing_task_raises_value_error(self, mock_task_get):
        from tasks.models import Task
        mock_task_get.side_effect = Task.DoesNotExist

        from functions.tasks import regenerate_ocr_for_task

        with self.assertRaises(ValueError):
            regenerate_ocr_for_task(task_id=9999)

    @patch("functions.tasks.get_batch_ocr_predictions_using_arena")
    @patch("functions.tasks.dataset_models.OCRDocument.objects.get")
    @patch("functions.tasks.Task.objects.get")
    def test_empty_microservice_response_raises_runtime_error(
        self, mock_task_get, mock_doc_get, mock_arena
    ):
        mock_task_get.return_value = make_mock_task()
        mock_doc_get.return_value = make_mock_ocr_document()
        mock_arena.return_value = ""

        from functions.tasks import regenerate_ocr_for_task

        with self.assertRaises(RuntimeError):
            regenerate_ocr_for_task(task_id=1)

    @patch("functions.tasks.get_batch_ocr_predictions_using_arena")
    @patch("functions.tasks.dataset_models.OCRDocument.objects.get")
    @patch("functions.tasks.Task.objects.get")
    def test_provider_override_passed_to_arena(
        self, mock_task_get, mock_doc_get, mock_arena
    ):
        mock_task_get.return_value = make_mock_task()
        mock_doc_get.return_value = make_mock_ocr_document()
        mock_arena.return_value = MOCK_RAW_JSON

        from functions.tasks import regenerate_ocr_for_task

        regenerate_ocr_for_task(task_id=1, provider="openai")

        call_kwargs = mock_arena.call_args[1]
        self.assertEqual(call_kwargs["provider"], "openai")

    @patch("functions.tasks.get_batch_ocr_predictions_using_arena")
    @patch("functions.tasks.dataset_models.OCRDocument.objects.get")
    @patch("functions.tasks.Task.objects.get")
    def test_existing_task_data_keys_preserved(
        self, mock_task_get, mock_doc_get, mock_arena
    ):
        mock_task = make_mock_task(task_data={"image_url": "https://example.com/img.png", "word_count": 42})
        mock_task_get.return_value = mock_task
        mock_doc_get.return_value = make_mock_ocr_document()
        mock_arena.return_value = MOCK_RAW_JSON

        from functions.tasks import regenerate_ocr_for_task

        regenerate_ocr_for_task(task_id=1)

        # Existing keys must not be wiped
        self.assertEqual(mock_task.data["image_url"], "https://example.com/img.png")
        self.assertEqual(mock_task.data["word_count"], 42)


# ─── API endpoint tests ───────────────────────────────────────────────────────


class TestRegenerateOcrEndpoint(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    def _make_user(self, role):
        user = MagicMock(spec=User)
        user.is_authenticated = True
        user.role = role
        return user

    @patch("tasks.views.regenerate_ocr_for_task")
    @patch("tasks.views.Task.objects.get")
    def test_workspace_manager_gets_202(self, mock_task_get, mock_celery):
        mock_task_get.return_value = make_mock_task()
        mock_celery_result = MagicMock()
        mock_celery_result.id = "celery-abc-123"
        mock_celery.delay.return_value = mock_celery_result

        request = self.factory.post(
            "/api/task/1/regenerate_ocr/", {}, format="json"
        )
        user = self._make_user(User.WORKSPACE_MANAGER)
        force_authenticate(request, user=user)

        view = TaskViewSet.as_view({"post": "regenerate_ocr"})
        response = view(request, pk=1)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["task_id"], 1)
        self.assertEqual(response.data["celery_task_id"], "celery-abc-123")

    @patch("tasks.views.Task.objects.get")
    def test_annotator_gets_403(self, mock_task_get):
        mock_task_get.return_value = make_mock_task()

        request = self.factory.post(
            "/api/task/1/regenerate_ocr/", {}, format="json"
        )
        user = self._make_user(User.ANNOTATOR)
        force_authenticate(request, user=user)

        view = TaskViewSet.as_view({"post": "regenerate_ocr"})
        response = view(request, pk=1)

        self.assertEqual(response.status_code, 403)

    @patch("tasks.views.Task.objects.get")
    def test_missing_task_returns_404(self, mock_task_get):
        from tasks.models import Task
        mock_task_get.side_effect = Task.DoesNotExist

        request = self.factory.post(
            "/api/task/999/regenerate_ocr/", {}, format="json"
        )
        user = self._make_user(User.WORKSPACE_MANAGER)
        force_authenticate(request, user=user)

        view = TaskViewSet.as_view({"post": "regenerate_ocr"})
        response = view(request, pk=999)

        self.assertEqual(response.status_code, 404)

    @patch("tasks.views.regenerate_ocr_for_task")
    @patch("tasks.views.Task.objects.get")
    def test_provider_field_forwarded_to_celery(self, mock_task_get, mock_celery):
        mock_task_get.return_value = make_mock_task()
        mock_celery.delay.return_value = MagicMock(id="celery-xyz")

        request = self.factory.post(
            "/api/task/1/regenerate_ocr/",
            {"provider": "openai"},
            format="json",
        )
        user = self._make_user(User.ADMIN)
        force_authenticate(request, user=user)

        view = TaskViewSet.as_view({"post": "regenerate_ocr"})
        view(request, pk=1)

        mock_celery.delay.assert_called_once_with(1, "openai")