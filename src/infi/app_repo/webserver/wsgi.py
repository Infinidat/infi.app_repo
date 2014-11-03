from logbook import Logger
from infi.logging.plugins.request_id_tag import set_random_tag
from gevent.wsgi import WSGIHandler


logger = Logger(__name__)


class DummyWSGILogger(object):
    @staticmethod
    def write(*args, **kwargs):
        logger.info(*args, **kwargs)


class WSGIHandlerWithWorkarounds(WSGIHandler):
    """
    WSGI handler that:

    * logs each request, the time it took to serve it and its http code
    * sets a log tag per request
    * workaround for client disconnects when sending the result
    """
    def run_application(self):
        set_random_tag()
        self.log_request()
        return super(WSGIHandlerWithWorkarounds, self).run_application()

    def log_request(self):
        logger.debug(self.format_request())

    def format_request(self):
        start_msg = "processing http request {!r} from {}"
        end_msg = "finished processing http request {!r} from {}, returning http code {} after {} seconds"
        if self.time_finish:
            delta = '%.6f' % (self.time_finish - self.time_start)
            return_code = (getattr(self, 'status', None) or '000').split()[0]
            return end_msg.format(self.requestline, self.client_address[0], return_code, delta)
        return start_msg.format(self.requestline, self.client_address[0])

    def process_result(self):
        from gevent.socket import error
        # IZBOX-1902
        # http://stackoverflow.com/questions/10215161/detecting-client-disconnects-within-gevent
        # http://stackoverflow.com/questions/14925413/gevent-websocket-detecting-closed-connection
        # https://github.com/benoitc/gunicorn/issues/414
        try:
            return super(WSGIHandlerWithWorkarounds, self).process_result()
        except error as _error:
            logger.warn("got {} while sending result to client, probably got disconnected", _error)
