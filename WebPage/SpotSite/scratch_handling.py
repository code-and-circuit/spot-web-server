from pprint import pprint
import time
from SpotSite.utils import start_thread
import socket as socket_lib
import json
from SpotSite.utils import output_to_socket

class Scratch_Handler:
    def __init__(self):
        self.sockets = {}
        self.keep_sockets_alive = True

    async def accept_ws_connection(self, socket):
        ip = socket._scope['client'][0]

        await socket.send_json({
            "type": "request-name"
        })

        self.sockets[ip] = {
            "socket": socket,
            "name": "unset"
        }
        await self.keep_socket_alive(socket, ip)

    async def keep_socket_alive(self, socket, ip):
        while self.keep_sockets_alive:
            message = await socket.receive_text()
            if (message == "Disconnected"):
                break
            else:
                message = json.loads(message)
                if message["type"] == "change-name":
                    self.sockets[ip]["name"] = message["name"] if message["name"] != "" else ip
                    output_to_socket(-1,[(client["name"], ip) for ip, client in self.sockets.items()], all=True, type="client-list")
        
        del self.sockets[ip]

scratch_handler = Scratch_Handler()
