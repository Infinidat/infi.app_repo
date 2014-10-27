from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


class AppRepoFtpHandler(FTPHandler):
    def on_file_received(self, filepath):
        server.rpc_client.process_source(filepath)


def start(config):
    from .service import get_client
    # Instantiate a dummy authorizer for managing 'virtual' users
    authorizer = DummyAuthorizer()

    # Define a new user that can upload files
    authorizer.add_user(config.ftpserver.username, config.ftpserver.password, config.incoming_directory, perm='lrwe')
    # Define a read-only user
    authorizer.add_anonymous(config.base_directory)

    # Instantiate FTP handler class
    handler = AppRepoFtpHandler
    handler.authorizer = authorizer

    # Define a customized banner (string returned when client connects)
    handler.banner = "app-repo ftp ready."

    # Specify a masquerade address and the range of ports to use for
    # passive connections.  Decomment in case you're behind a NAT.
    #handler.masquerade_address = '151.25.42.11'
    #handler.passive_ports = range(60000, 65535)

    # Instantiate FTP server class and listen on 0.0.0.0:2121
    address = (config.ftpserver.address, config.ftpserver.port)
    server = FTPServer(address, handler)

    # we need this for later
    server.rpc_client = get_client(config)

    # set a limit for connections
    server.max_cons = 256
    server.max_cons_per_ip = 5

    return server
