from __future__ import print_function
import socket
import sys
import os
import threading
import stat

from .configuration import settings, configure
from cli.launchers import Launcher, RequireSubCommand


class Listen(Launcher, RequireSubCommand):

    @classmethod
    def create_parser(cls, subparsers):
        parser = subparsers.add_parser(
            'listen',
            help='Put message on message queue server'
        )

        return parser

    def launch(self):
        configure(filename=self.args.config_file)

        from .job import Job
        thread_pool = [
            threading.Thread(
                target=Job.worker,
                name='Worker%d' % i
            )  for i in range(1, settings.threads+1)
        ]

        # Make sure the socket does not already exist
        try:
            os.unlink(settings.socket_file)
        except OSError:
            if os.path.exists(settings.socket_file):
                print(
                    'The socket file is already exists: %s' % settings.socket_file,
                    file=sys.stderr
                )

        # Create a UDS socket
        unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        print('Listening on %s' % settings.socket_file)
        unix_socket.bind(settings.socket_file)
        os.chmod(settings.socket_file, stat.S_IRWXU + stat.S_IRWXG + stat.S_IROTH)
        unix_socket.listen(settings.backlog)

        for thread in thread_pool:
            thread.daemon = True
            thread.start()

        while True:
            # Wait for a connection
            print('Waiting for a connection')
            connection, client_address = unix_socket.accept()
            Job.put(Job(connection, client_address))

