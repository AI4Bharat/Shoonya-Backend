from .client import ResourceClient
from .manager import ResourceManager


class ResourceBase(type):
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)
        parents = [b for b in bases if isinstance(b, ResourceBase)]
        if not parents:
            return new_class

        meta = attrs.pop('Meta', None)
        if meta is None:
            raise ValueError("Resource {} must specify a Meta class.".format(new_class.__name__))

        try:
            endpoints = meta.endpoints
        except AttributeError:
            raise ValueError(
                "Resource {} Meta class must have an 'endpoints' attribute.".format(new_class.__name__)
            )

        client_class = getattr(meta, 'client_class', ResourceClient)
        headers = getattr(meta, 'headers', {})
        new_class.client = client_class(endpoints=endpoints, headers=headers)
        meta.client = new_class.client  # XXX

        new_class._meta = meta
        new_class.resources = ResourceManager(resource_class=new_class)
        return new_class


class Field:
    def __init__(self, name, value, model):
        self.name = name
        self.value = value
        self._model = model
        self._updated = False

    def __setattr__(self, name, value):
        if not name.startswith('_'):
            self._updated = True
        super().__setattr__(name, value)

    @property
    def updated(self):
        return self._updated

    @property
    def is_patch_field(self):
        try:
            return self.name in self._model._meta.patch_fields
        except AttributeError:
            return True  # by default all fields are patch fields


class Resource(metaclass=ResourceBase):
    def __init__(self, **kwargs):
        self._fields = {}
        for name, value in kwargs.items():
            self._fields[name] = Field(name, value, self)
            setattr(self, name, value)

    def __setattr__(self, name, value):
        if not name.startswith('_'):
            self._fields[name].value = value
        super().__setattr__(name, value)

    def __iter__(self):
        for name, field in self._fields.items():
            yield name, field.value

    def _get_patch_fields(self, updated=True):
        patch_fields = (
            (field.name, field.value) for field in self._fields.values()
            if field.is_patch_field
        )
        if updated:
            return dict((field.name, field.value) for field in patch_fields if field.updated)
        return dict(patch_fields)

    def save(self, partial=True):
        if not partial:
            data = self._get_patch_fields(updated=False)
            return type(self).client.patch(pk=self.id, **data)

        updated_fields = self._get_patch_fields()
        if not updated_fields:
            return

        return type(self).client.patch(pk=self.id, **updated_fields)
