from infi.exceptools import InfiException

class AppRepoBaseException(InfiException):
    pass

class FileAlreadyExists(AppRepoBaseException):
    pass
