from sys import argv, stdout
from os.path import abspath, dirname, join
from os import pardir
from logging import DEBUG, basicConfig
from infi.traceback import traceback_decorator
from infi.app_repo import ApplicationRepository
from infi.app_repo.webserver import start

PROJECT_DIRECTORY = abspath(join(dirname(__file__), # scripts
                                         pardir, #app_repo
                                         pardir, #info
                                         pardir, # src
                                         pardir, #root
                                         ))

REPOSITORY_BASE_DIRECTORY = join(PROJECT_DIRECTORY, 'data')

@traceback_decorator
def process_incoming(argv=argv[1:]):
    basicConfig(level=DEBUG, stream=stdout)
    app_repo = ApplicationRepository(REPOSITORY_BASE_DIRECTORY)
    [source_path] = argv if argv != [] and argv[0] != '--force' else [join(REPOSITORY_BASE_DIRECTORY, 'incoming')]
    force_metdata_update = '--force' in argv
    if not app_repo.add(source_path) and force_metdata_update:
        app_repo.update_metadata()

def post_install():
    basicConfig(level=DEBUG, stream=stdout)
    app_repo = ApplicationRepository(REPOSITORY_BASE_DIRECTORY)
    app_repo.setup()

def webserver(argv=argv[1:]):
    develop = 'develop' in argv
    if not develop:
        from infi.app_repo.upstart import signal_init_that_i_am_ready
        signal_init_that_i_am_ready()
    start(develop)
