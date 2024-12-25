# pragma: no cover
import os

from celery import Celery, Task

from shooter.__main__ import make_screenshot_from_url

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_BACKEND_URL = os.getenv("CELERY_BACKEND_URL")

celery_app = Celery(
    "tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_BACKEND_URL,
    task_send_sent_event=True,
    task_track_started=True,
    task_store_eager_result=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_send_task_events=True,
    result_expires=None,  # never
)


class StoreArgsTask(Task):  # pragma: no cover
    def __call__(self, *args, **kwargs):
        result = super().__call__(*args, **kwargs)
        return {"result": result, "args": args, "kwargs": kwargs}


celery_app.Task = StoreArgsTask


@celery_app.task(name="shooter.celery_app.take_screenshot", ignore_result=False)
def take_screenshot(url, output_path, config_dict):  # pragma: no cover
    make_screenshot_from_url(url, output_path, **config_dict)
    return {
        "url": url,
        "output_path": output_path,
        "config": config_dict,
    }
