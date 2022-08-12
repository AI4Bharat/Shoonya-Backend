from typing import TypeVar, List

from django.db import transaction
from django.db.models import Model
from django.db.models.query import QuerySet

M = TypeVar("M", bound=Model)


def multi_inheritance_table_bulk_insert(data: List[M]) -> None:
    """
    Bulk insert data into a multi-inheritance table.
    """
    if not data:
        return

    model = data[0].__class__
    local_fields = model._meta.local_fields
    parent_model = model._meta.pk.related_model
    parent_fields = parent_model._meta.local_fields

    parent_objects = [
        parent_model(
            **{field.name: getattr(obj, field.name) for field in parent_fields}
        )
        for obj in data
    ]
    parent_model.objects.bulk_create(parent_objects)
    for parent, obj in zip(parent_objects, data):
        obj.pk = parent.pk

    queryset = QuerySet(model)
    queryset._for_write = True
    with transaction.atomic(using=queryset.db, savepoint=False):
        queryset._batched_insert(
            data,
            local_fields,
            batch_size=None,
        )
