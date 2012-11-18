from celery import Celery
from datetime import timedelta

celery = None

def init(config):
    global celery
    celery = Celery('infi.app_repo.worker.celery',
                    broker='amqp://',
                    backend='amqp',
                    include=['infi.app_repo.tasks'])

    celery.conf.CELERYBEAT_SCHEDULE = {
        'process-incoming': {
            'task': 'infi.app_repo.tasks.process_incoming',
            'schedule': timedelta(seconds=config.worker.process_incoming_interval),
            'args': (config.base_directory, False,),
        }
    }
