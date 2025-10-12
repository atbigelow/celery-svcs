import celery
import pytest
import svcs
from celery import Celery, Task

import celery_svcs


@pytest.fixture
def svcs_registry():
    registry = svcs.Registry()
    yield registry
    registry.close()


@pytest.fixture
def svcsed_celery_app(celery_app: Celery, svcs_registry: svcs.Registry) -> Celery:
    celery_svcs.init(celery_app, registry=svcs_registry)
    return celery_app


def test_uninit_exception(celery_app: Celery):
    with pytest.raises(Exception):
        celery_svcs.get_registry(celery_app)


def test_init_default_registry(celery_app: Celery):
    celery_svcs.init(celery_app)

    assert celery_svcs.get_registry(celery_app)


def test_init_explicit_registry(celery_app: Celery, svcs_registry: svcs.Registry):
    celery_svcs.init(celery_app, registry=svcs_registry)

    assert celery_svcs.get_registry(celery_app) == svcs_registry


def test_registry_closed(celery_app: Celery):
    celery_svcs.init(celery_app)
    svcs_registry = celery_svcs.get_registry(celery_app)

    # Register a type
    svcs_registry.register_value(str, "A String")
    assert str in svcs_registry

    celery_svcs.close_registry(celery_app)

    # str should no longer be registered
    assert str not in svcs_registry


def test_task_is_svcsed(svcsed_celery_app: Celery, celery_worker):
    svcs_registry = celery_svcs.get_registry(svcsed_celery_app)
    svcs_registry.register_value(str, "A String")

    @svcsed_celery_app.task(bind=True)
    def test_task(task: Task):
        services = celery_svcs.svcs_from(task)

        return services.get(str)

    # Need to reload worker for task to be registered
    celery_worker.reload()

    res = test_task.delay()
    assert res.get() == "A String"


def test_task_is_not_svcsed(celery_app: Celery, celery_worker):
    @celery_app.task(bind=True)
    def test_task(task: Task):
        celery_svcs.svcs_from(task)

    # Need to reload worker for task to be registered
    celery_worker.reload()

    res = test_task.delay()
    with pytest.raises(AttributeError):
        res.get()


def test_task_unique_containers(svcsed_celery_app: Celery, celery_worker):
    svcs_registry = celery_svcs.get_registry(svcsed_celery_app)
    svcs_registry.register_value(int, 0)

    @svcsed_celery_app.task(bind=True)
    def test_task(task: Task, num: int):
        services = celery_svcs.svcs_from(task)

        # Get the value registered to the Registry
        test_int = services.get(int)

        # Set a new value JUST in the container, which should vanish
        services.register_local_value(int, num)

        return test_int

    # Need to reload worker for task to be registered
    celery_worker.reload()

    res = celery.group(test_task.s(2), test_task.s(3), test_task.s(4))()
    assert res.get() == [0, 0, 0]
