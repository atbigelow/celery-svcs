import celery
from svcs import Container, Registry

# Copied from svcs library
_KEY_REGISTRY = "svcs_registry"
_KEY_CONTAINER = "svcs_container"


def svcs_from(
    task: celery.Task | None = None,
) -> Container:
    """Get a Container from a specified Task. Or if None given, attempt to retrieve it from the current task."""
    if task is None:
        task = celery.current_task

    # Attach the container to the Task's current request context
    request = task.request

    return getattr(request, _KEY_CONTAINER)


def get_registry(app: celery.Celery) -> Registry:
    """Get a svcs Registry attached to a Celery instance."""
    app = app or celery.current_app

    return getattr(app, _KEY_REGISTRY)


def init(
    app: celery.Celery,
    *,
    registry: Registry | None = None,
):
    """Initialize a Celery instance with a svcs Registry."""
    setattr(app, _KEY_REGISTRY, registry or Registry())

    _connect_signals()  # TODO: Only needs to be called once


def close_registry(app: celery.Celery):
    """Close the svcs Registry attached to a Celery instance."""
    get_registry(app).close()


def _connect_signals():
    """Connect signals from Celery."""
    celery.signals.task_prerun.connect(_celery_svcs_task_prerun)
    celery.signals.task_postrun.connect(_celery_svcs_task_postrun)


def _celery_svcs_task_prerun(*args, **kwargs):
    """Attach a container to a Task request before it runs. Only instantiates a Container if the Task's Celery app was svcs-ed."""

    task = kwargs.get("task")
    if task and hasattr(task.app, _KEY_REGISTRY):
        container = Container(getattr(task.app, _KEY_REGISTRY))
        setattr(task.request, _KEY_CONTAINER, container)


def _celery_svcs_task_postrun(*args, **kwargs):
    """Close a container when a Task request is finished, regardless of success. Only closes a Container if the Task's Celery app was svcs-ed."""

    task = kwargs.get("task")
    if task and hasattr(task.app, _KEY_REGISTRY):
        container = getattr(task.request, _KEY_CONTAINER)
        container.close()
