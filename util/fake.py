from unittest.mock import Mock


class Fake(object):
    """Create Mock()ed methods that match another class's methods."""

    @classmethod
    def imitate(cls, *others):
        for other in others:
            for name in other.__dict__:
                try:
                    setattr(cls, name, Mock())
                except (TypeError, AttributeError):
                    pass
        return cls
