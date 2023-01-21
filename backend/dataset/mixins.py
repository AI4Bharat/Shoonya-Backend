import tablib
from django.db.models.query import QuerySet


class ResourceMixin:
    """
    Resource Mixin for streaming CSV file
    """

    def export_as_generator(self, export_type, queryset=None, *args, **kwargs):
        self.before_export(queryset, *args, **kwargs)
        if queryset is None:
            queryset = self.get_queryset()
        headers = self.get_export_headers()
        data = tablib.Dataset(headers=headers)
        # Return headers
        if export_type == "tsv":
            yield data.tsv
        else:
            yield data.csv

        if isinstance(queryset, QuerySet):
            # Iterate without the queryset cache, to avoid wasting memory when
            # exporting large datasets.
            iterable = queryset.iterator()
        else:
            iterable = queryset
        for obj in iterable:
            # Return subset of the data (one row)
            # This is a simple implementation to fix the tablib library which is missing returning the data as
            # generator
            data = tablib.Dataset()
            data.append(self.export_resource(obj))
            if export_type == "tsv":
                yield data.tsv
            else:
                yield data.csv

        self.after_export(queryset, data, *args, **kwargs)

        yield
