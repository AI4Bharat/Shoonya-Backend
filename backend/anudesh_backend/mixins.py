class DummyModelMixin:
    """
    Dummy Mixin
    """

    def has_permission(self, user):
        """Check if user has permission"""
        user = True
        return user
