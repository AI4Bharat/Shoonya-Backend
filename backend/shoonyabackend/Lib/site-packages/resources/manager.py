class ResourceManager:
    def __init__(self, resource_class):
        self._resource_class = resource_class

    @property
    def client(self):
        return self._resource_class._meta.client

    @property
    def resource_class_name(self):
        return self._resource_class.__name__.replace('Resource', '')

    def _build_model(self, data):
        return self._resource_class(**data)

    def get(self, pk, **kwargs):
        resource = self.client.get(pk)
        return self._build_model(resource)

    def filter(self, **kwargs):
        content = self.client.filter(**kwargs)
        return [self._build_model(resource) for resource in content]

    def all(self):
        return self.filter()

    def create(self, **kwargs):
        resource = self.client.post(**kwargs)
        return self._build_model(resource)

    def update(self, pk, **kwargs):
        content = self.client.patch(pk, **kwargs)
        return self._build_model(content)

    def create_or_update(self, **kwargs):
        content = self.client.put(**kwargs)
        return self._build_model(content)

    def delete(self, pk):
        self.client.delete(pk)
