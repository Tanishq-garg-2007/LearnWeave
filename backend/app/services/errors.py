"""Domain exceptions shared by services and API routers.

Both subclass ValueError so existing ``except ValueError`` handlers keep working,
but routers should map them explicitly: NotFoundError -> 404, StepError -> its
``status_code`` (400 for bad input, 409 for out-of-order or conflicting requests).
"""


class NotFoundError(ValueError):
    """The requested resource does not exist OR is not visible to the current user.

    Ownership failures deliberately use the same error as a missing row so that
    callers cannot probe for other users' resources.
    """


class StepError(ValueError):
    """The request is invalid for the current state (bad input or out-of-order step)."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code
