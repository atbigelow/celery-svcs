import celery
from celery.signals import task_postrun, task_prerun
from svcs import Container, Registry

# Copied from svcs library.
_ATTR_REGISTRY = "svcs_registry"
_ATTR_CONTAINER = "svcs_container"


def svcs_from(task: celery.Task | None = None) -> Container:
    """Get a Container from a specified Task. Or if None given, attempt to retrieve it from Celery's current task."""

    if task is not None:
        return getattr(task.request, _ATTR_CONTAINER)

    # Handle Celery's Proxy object with a bool check.
    if not celery.current_task:
        raise ValueError("No current Celery task.")

    return getattr(celery.current_task.request, _ATTR_CONTAINER)


def get_registry(app: celery.Celery) -> Registry:
    """Get a svcs Registry attached to a Celery instance.

    Does not default to the current_app to prevent the "app trap"."""

    return getattr(app, _ATTR_REGISTRY)


def init(
    app: celery.Celery,
    *,
    registry: Registry | None = None,
):
    """Initialize a Celery instance with a svcs Registry, creating a new svcs Container from that Registry for each task request that is ran."""

    setattr(app, _ATTR_REGISTRY, registry or Registry())


def close_registry(app: celery.Celery):
    """Close the svcs Registry attached to a Celery instance.

    Does not default to the current_app to prevent accidental registry closing with the "app trap"."""

    get_registry(app).close()


# Attach signals to Celery; by importing this module, we're going to assume the desire to use svcs with Celery.
@task_prerun.connect
def _celery_svcs_task_prerun(task: celery.Task, *args, **kwargs):
    """Attach a container to a Task Context before it runs. Only instantiates a Container if the Task's Celery app was svcs-ed."""

    registry: Registry | None
    if registry := getattr(task.app, _ATTR_REGISTRY, None):
        container = Container(registry)

        setattr(task.request, _ATTR_CONTAINER, container)


@task_postrun.connect
def _celery_svcs_task_postrun(task: celery.Task, *args, **kwarg):
    """Close a container from a Task Context when the Task is finished, regardless of success. Only closes a Container if the Task's Celery app was svcs-ed."""

    container: Container | None
    if hasattr(task.app, _ATTR_REGISTRY) and (container := getattr(task.app, _ATTR_CONTAINER, None)):
        container.close()
