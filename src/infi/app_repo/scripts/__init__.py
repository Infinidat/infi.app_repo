from sys import argv, stdout
from os.path import abspath, dirname, join
from os import pardir
from logging import DEBUG, basicConfig, getLogger
from infi.traceback import traceback_decorator, traceback_context
from infi.app_repo import ApplicationRepository
from infi.app_repo.webserver import start
from infi.pyutils.decorators import wraps
from datedate import datetime

PROJECT_DIRECTORY = abspath(join(dirname(__file__), # scripts
                                         pardir, #app_repo
                                         pardir, #info
                                         pardir, # src
                                         pardir, #root
                                         ))

REPOSITORY_BASE_DIRECTORY = join(PROJECT_DIRECTORY, 'data')

logger = getLogger(__name__)

def console_script(func):
    @wraps
    def decorator(*args, **kwargs):
        filename = datetime.datetime.now().strftime("%Y-%m-%d:%H-%m-%S")
        basicConfig(level=DEBUG, filemode='w', filepath='/tmp/{}_{}.log'.format(func.__name__, filename))
        logger.infi("Logging started")
        with traceback_context():
            try:
                logger.info("Calling {}".format(func.__name__))
                result = func(*args, **kwargs)
                logger.info("Call to {} returned {}".format(func.__name__, result))
                return result
            except:
                logger.exception("Caught exception")
                raise
            finally:
                logger.info("Logging ended")
    return decorator

@console_script
def process_incoming(argv=argv[1:]):
    basicConfig(level=DEBUG, stream=stdout)
    app_repo = ApplicationRepository(REPOSITORY_BASE_DIRECTORY)
    [source_path] = argv if argv != [] and argv[0] != '--force' else [join(REPOSITORY_BASE_DIRECTORY, 'incoming')]
    force_metdata_update = '--force' in argv
    if not app_repo.add(source_path) and force_metdata_update:
        app_repo.update_metadata()

@console_script
def post_install():
    basicConfig(level=DEBUG, stream=stdout)
    app_repo = ApplicationRepository(REPOSITORY_BASE_DIRECTORY)
    app_repo.setup()

@console_script
def webserver(argv=argv[1:]):
    develop = 'develop' in argv
    if not develop:
        from infi.app_repo.upstart import signal_init_that_i_am_ready
        signal_init_that_i_am_ready()
    start(develop)
