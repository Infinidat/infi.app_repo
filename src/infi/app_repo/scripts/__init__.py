from sys import argv, stdout
from os.path import abspath, dirname, join
from os import pardir
from logging import DEBUG, basicConfig
from infi.traceback import traceback_decorator
from infi.app_repo import ApplicationRepository

REPOSITORY_BASE_DIRECTORY = abspath(join(dirname(__file__), # scripts
                                         pardir, #app_repo
                                         pardir, #info
                                         pardir, # src
                                         pardir, #root
                                         'data'
                                         ))
@traceback_decorator
def process_incoming(argv=argv[1:]):
    basicConfig(level=DEBUG, stream=stdout)
    app_repo = ApplicationRepository(REPOSITORY_BASE_DIRECTORY)
    [source_path] = argv
    app_repo.add(source_path)

def post_install():
    basicConfig(level=DEBUG, stream=stdout)
    app_repo = ApplicationRepository(REPOSITORY_BASE_DIRECTORY)
    app_repo.setup()
