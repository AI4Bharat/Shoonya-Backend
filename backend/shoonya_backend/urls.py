import os
from django.contrib import admin
from django.urls import path, include, re_path
from os.path import basename
from rest_framework import permissions
from rest_framework import routers
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from tasks.views import (
    TaskViewSet,
    AnnotationViewSet,
    PredictionViewSet,
    SentenceOperationViewSet,
)


class BothHttpAndHttpsSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.schemes = ["http", "https"]
        return schema


SchemaView = get_schema_view(
    openapi.Info(
        title="Shoonya API Docs",
        default_version="v1",
        description="API documentation for Shoonya Platform.",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    generator_class=BothHttpAndHttpsSchemaGenerator,
    url=os.getenv("API_URL"),
    public=True,
    permission_classes=[permissions.AllowAny],
)
urlpatterns = [
    path("admin/", admin.site.urls),
    path("users/", include("users.urls")),
    path("session/", include("rest_framework.urls")),
    path("organizations/", include("organizations.urls")),
    path("workspaces/", include("workspaces.urls")),
    # path("/", include("tasks.urls")),
    path("projects/", include("projects.urls")),
    path("functions/", include("functions.urls")),
    path("data/", include("dataset.urls")),
    path("logs/", include("loging.urls")),
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        SchemaView.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"^swagger/$",
        SchemaView.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"^redoc/$", SchemaView.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
]

router = routers.DefaultRouter()
router.register(r"task", TaskViewSet, basename="task")
router.register(r"annotation", AnnotationViewSet, basename="annotation")
router.register(r"prediction", PredictionViewSet, basename="prediction")
router.register(
    r"sentenceoperation", SentenceOperationViewSet, basename="sentenceoperation"
)

urlpatterns += router.urls
