from celery import Celery

celery = Celery('infi.app_repo.worker.celery',
                    broker='redis://',
                    backend='redis',
                    include=['infi.app_repo.tasks'])

def init(config):
    import logging
    global celery
    celery.conf.CELERYD_HIJACK_ROOT_LOGGER = False
    celery.log.get_default_logger().handlers = logging.root.handlers
    celery.log.setup(loglevel=logging.DEBUG)
    celery.log.setup_logging_subsystem(loglevel=logging.DEBUG)
    celery.log.setup_task_loggers(loglevel=logging.DEBUG)
