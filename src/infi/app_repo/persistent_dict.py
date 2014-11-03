from infi.gevent_utils.os import path, remove, fopen
from infi.gevent_utils.deferred import create_threadpool_executed_func
from UserDict import UserDict
from msgpack import packb, unpackb
from infi.rpc.base import SynchronizedMixin, synchronized
from gevent.lock import RLock


@create_threadpool_executed_func
def _read(filepath):
    with fopen(filepath, 'rb') as fd:
        return unpackb(fd.read())


@create_threadpool_executed_func
def _write(filepath, contents):
    with fopen(filepath, 'wb') as fd:
        fd.write(packb(contents))


class PersistentDict(UserDict, SynchronizedMixin):
    def __init__(self, filepath):
        UserDict.__init__(self)
        self.synchronized_mutex = RLock()
        self.filepath = filepath

    @synchronized
    def load(self):
        if path.exists(self.filepath):
            self.data = _read(self.filepath)
        else:
            self.data = dict()

    @synchronized
    def delete(self):
        if path.exists(self.filepath):
            remove(self.filepath)

    @synchronized
    def save(self):
        _write(self.filepath, self.data)

    def __setitem__(self, *args, **kwargs):
        UserDict.__setitem__(self, *args, **kwargs)
        self.save()

    def __delitem__(self, *args, **kwargs):
        UserDict.__delitem__(self, *args, **kwargs)
        self.save()

    def update(self, *args, **kwargs):
        UserDict.update(self, *args, **kwargs)
        self.save()

    def pop(self, *args, **kwargs):
        try:
            return UserDict.pop(self, *args, **kwargs)
        finally:
            self.save()
