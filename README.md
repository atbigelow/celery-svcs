# celery-svcs: A Celery integration for SVCS

Very unrefined!

## Usage

### Initialization
```python
import celery
import svcs
import celery_svcs

# Have a Celery app
celery_app = celery.Celery()

# Have a svcs Registry
registry = svcs.Registry()

# Initialize svcs with the Celery app, with an existing registry
celery_svcs.init(celery_app, registry=registry)
```

### Service Acquisition
```python
import celery_svcs

@celery_app.task:
def a_celery_task():
    svcs = celery_svcs.svcs_from()

    db, api, cache = svcs.get(Database, WebAPIClient, Cache)

    ...
```
