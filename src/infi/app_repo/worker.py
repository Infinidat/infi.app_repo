from celery import Celery
from datetime import timedelta

celery = Celery('infi.app_repo.worker.celery',
                    broker='redis://',
                    backend='redis',
                    include=['infi.app_repo.tasks'])

def init(config):
    global celery
