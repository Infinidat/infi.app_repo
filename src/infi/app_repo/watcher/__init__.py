from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer
from logging import getLogger
from os import path, makedirs
from time import sleep
from ..tasks import process_incoming
logger = getLogger(__name__)

SUPPORTED_ARCHIVES = ['msi', 'rpm', 'deb', 'tar.gz', 'zip', 'ova', 'img', 'iso']


class Handler(FileSystemEventHandler):
    def __init__(self, base_directory):
        super(Handler, self).__init__()
        self._base_directory = base_directory

    def on_created(self, event):
        super(Handler, self).on_created(event)
        if not isinstance(event, FileCreatedEvent):
            return
        source = event.src_path
        if not any([source.endswith(item) for item in SUPPORTED_ARCHIVES]):
            return
        logger.info("detected new file: {}".format(source))
        logger.info("requesting processing of {}".format(source))
        process_incoming.apply_async((self._base_directory))


class Server(object):
    def __init__(self, config):
        super(Server, self).__init__()
        self._config = config
        self._observers = []
        self._base_directory = config['base_directory']
        self._incoming_directory = path.join(self._base_directory, 'incoming')

    def setup(self):
        self._setup_observers()
        logger.info("started")

    def _setup_observers(self):
        incoming_handler = Handler(self._base_directory)
        self._observers.append(self._create_observer(incoming_handler, self._incoming_directory))
        self.trigger_processing_of_incoming_directory()

    def teardown(self):
        for observer in self._observers:
            observer.stop()
            observer.join()

    def _create_observer(self, handler, path_to_monitor):
        if not path.exists(path_to_monitor):
            makedirs(path_to_monitor)
        observer = Observer()
        observer.schedule(handler, path_to_monitor, recursive=True)
        observer.start()
        logger.debug("started observer {!r} on {!r}".format(handler, path_to_monitor))
        return observer

    def trigger_processing_of_incoming_directory(self):
        logger.info("requesting processing of incoming directory")
        process_incoming.apply_async((self._base_directory, ))

    def run(self):
        while True:
            sleep(1)


def start(config):
    server = Server(config)
    server.setup()
    server.run()
