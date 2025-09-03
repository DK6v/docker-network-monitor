import socket
from telegraf.client import ClientBase

class TelegrafClient(ClientBase):
    def __init__(self, host='localhost', port=8086, tags=None):
        super(TelegrafClient, self).__init__(host, port, tags)

    def send(self, data):
        """
        Sends the given data to the socket via TCP
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.socket.sendall(data.encode('utf8') + b'\n')
            self.socket.close()

        except (socket.error, RuntimeError):
            # Socket errors should fail silently so they don't affect anything else
            pass
