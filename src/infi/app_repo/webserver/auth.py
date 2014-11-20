from infi.pyutils.decorators import wraps
import flask


def check_password(username, password):
    """Checks the user name and password with PAM"""
    ftpserver_config = flask.current_app.app_repo_config.ftpserver
    return ftpserver_config.username == username and ftpserver_config.password == password


def requires_auth(func):
    """Decorator for methods that does basic authentication using PAM"""
    @wraps(func)
    def decorated(*args, **kwargs):
        auth = flask.request.authorization
        if not auth or not check_password(auth.username, auth.password):
            return flask.Response('Could not verify your access level for that URL.\n'
                                  'You have to login with proper credentials', 401,
                                  {'WWW-Authenticate': 'Basic realm="app_repo"'})
        return func(*args, **kwargs)
    return decorated
