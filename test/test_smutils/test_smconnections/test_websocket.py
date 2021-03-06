""" Test the websocket server connection """

import unittest
import socket

import asyncio
import mock
import websockets


from smserver.smutils.smconnections import websocket

class WebSocketServerTest(unittest.TestCase):
    """ Test the thread which handle async tcp connection """

    def setUp(self):
        super().setUp()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        sock = socket.socket()
        sock.bind(("localhost", 0))
        self.ip, self.port = sock.getsockname()

        self.mock_server = mock.MagicMock()

        self.server = websocket.WebSocketServer(self.mock_server, self.ip, self.port, self.loop)
        self.client = None

    def tearDown(self):
        self.loop.close()
        self.mock_server.reset_mock()

    def start_client(self):
        """ Start the client """
        client = websockets.client.connect(
            'ws://%s:%s/' % (self.ip, self.port)
        )

        self.client = self.loop.run_until_complete(client)

    def start_server(self):
        """ Start the server """

        self.server.start_server()

    def stop_server(self):
        """ Stop the server """

        self.server.stop_server()

    def test_server_close_while_client_connected(self):
        """ Try stopping the server during client connection """

        self.start_server()
        self.start_client()
        self.stop_server()
        self.mock_server.add_connection.assert_called_once()

    @mock.patch("smserver.smutils.smconnections.websocket.WebSocketClient._on_data")
    def test_send_message(self, on_data):
        """ Test sending data to the server """

        self.start_server()
        self.start_client()
        self.mock_server.add_connection.assert_called_once()
        connection = self.mock_server.add_connection.call_args[0][0]
        self.loop.run_until_complete(self.client.send("Hello!"))

        on_data.side_effect = connection.send_data

        reply = self.loop.run_until_complete(self.client.recv())

        self.assertEqual(reply, "Hello!")
        on_data.assert_called_with("Hello!")

        self.stop_server()
