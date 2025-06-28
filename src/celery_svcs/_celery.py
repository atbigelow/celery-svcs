import celery
from celery.signals import task_postrun, task_prerun
from svcs import Container, Registry

# Copied from svcs library
_KEY_REGISTRY = "svcs_registry"
_KEY_CONTAINER = "svcs_container"


def svcs_from(
    task: celery.Task | None = None,
) -> Container:
    """Get a Container from a specified Task. Or if None given, attempt to retrieve it from the current task."""

    # Explicit Task or use the current_task
    task = task or celery.current_task

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


def close_registry(app: celery.Celery):
    """Close the svcs Registry attached to a Celery instance."""

    get_registry(app).close()


# Attach signals to Celery; by importing this module, we're going to assume the desire to use svcs with Celery.
@task_prerun.connect
def _celery_svcs_task_prerun(task: celery.Task, *args, **kwargs):
    """Attach a container to a Task request before it runs. Only instantiates a Container if the Task's Celery app was svcs-ed."""

    registry: Registry | None
    if registry := getattr(task.app, _KEY_REGISTRY, None):
        container = Container(registry)

        setattr(task.request, _KEY_CONTAINER, container)


@task_postrun.connect
def _celery_svcs_task_postrun(task: celery.Task, *args, **kwarg):
    """Close a container when a Task request is finished, regardless of success. Only closes a Container if the Task's Celery app was svcs-ed."""

    container: Container | None
    if hasattr(task.app, _KEY_REGISTRY) and (container := getattr(task.app, _KEY_CONTAINER, None)):
        container.close()
