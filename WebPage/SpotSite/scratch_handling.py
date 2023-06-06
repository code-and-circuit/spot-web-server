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
        self.allowed_ip = ""

    async def accept_ws_connection(self, socket):
        ip = socket._scope['client'][0]

        await socket.send_json({
            "type": "request-name"
        })

        self.sockets[ip] = {
            "socket": socket,
            "name": "unset"
        }
        if self.allowed_ip == "":
            self.allowed_ip = ip

        await self.keep_socket_alive(socket, ip)

    def find_new_allowed_client(self):
        if (self.sockets):
            self.allowed_ip = list(self.sockets.keys())[0]
        else:
            self.allowed_ip = ""

    async def keep_socket_alive(self, socket, ip):
        while self.keep_sockets_alive:
            message = await socket.receive_text()
            if (message == "Disconnected"):
                del self.sockets[ip]
                if ip == self.allowed_ip:
                    self.find_new_allowed_client()

                self.update_scratch_clients()
                break
            else:
                message = json.loads(message)
                if message["type"] == "change-name":
                    self.sockets[ip]["name"] = message["name"] if message["name"] != "" else ip
                    self.update_scratch_clients()
        
    def get_client_list(self):
        return [(client["name"], ip) for ip, client in self.sockets.items()]
    
    def get_allowed_client_name(self):
        if self.allowed_ip != "":
            return self.sockets[self.allowed_ip]["name"]
        else:
            return "No one"
    
    def set_allowed_client(self, ip):
        self.allowed_ip = ip
        self.update_scratch_clients()

    def update_scratch_clients(self):
        output_to_socket(-1, (self.get_client_list(), (self.get_allowed_client_name(), self.allowed_ip)), all=True, type="scratch_clients")

scratch_handler = Scratch_Handler()
