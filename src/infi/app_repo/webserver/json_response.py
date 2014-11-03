from infi.pyutils.decorators import wraps
import flask
import cjson


def json_response(func):
    """
    Decorator that returns an application/json content type and JSON encoded result. The decorated method should
    return a Python dict.
    """
    @wraps(func)
    def callable(*args, **kwargs):
        error_message = None
        return_value = None
        try:
            return_value = func(*args, **kwargs)
            success = True
        except Exception, error:
            error_message = str(error)
            success = False
        return flask.Response(cjson.encode(dict(success=success, return_value=return_value, error_message=error_message)),
                              content_type='application/json')
    return callable
