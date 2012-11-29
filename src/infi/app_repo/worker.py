from celery import Celery
from datetime import timedelta

celery = Celery('infi.app_repo.worker.celery',
                    broker='redis://',
                    backend='redis',
                    include=['infi.app_repo.tasks'])

def init(config):
    global celery
    celery.conf.CELERYBEAT_SCHEDULE = {
        'process-incoming': {
            'task': 'infi.app_repo.tasks.process_incoming',
            'schedule': timedelta(seconds=config.worker.process_incoming_interval),
            'args': (config.base_directory, False,),
        }
    }
