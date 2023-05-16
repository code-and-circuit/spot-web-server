"""
Manages websockets and websocket actions

Classes:

    Websocket
    Websocket_list
    
Functions:

    close_all_sockets()
    
Misc Variables:

    websocket_list (Websocket_list): the list to hold the websockets
"""
import asyncio
import json
import time
import sys
import os
import inspect
from threading import Thread
from SpotSite import background_process
from SpotSite.spot_logging import log

class Websocket:
    """
    A class to hold a websocket and its information
    
    Attributes:
        socket(WebSocket): The websocket
        alive(bool): Whether the socket should be alive
        list(Websocket_List): the websocket list
        index(int): the index (or id) of the websocket
        
    Methods:
        open():
            Opens the websocket
        close():
            Closes the socket
        keep_alive():
            Keeps the socket alive
        set_socket(socket):
            Sets the socket passed from the client
        
    """
    def __init__(self, socket: object, socket_list: list, index: str):
        self.socket = socket
        self.alive = True
        self.list = socket_list
        self.index = index

    async def open(self) -> None:
        """
        Opens the websocket
        
        """
        await self.socket.accept()
        
    async def close(self) -> None:
        """
        Closes the socket

        """
        await self.socket.close()

    async def keep_alive(self) -> None:
        """
        Keeps the socket alive

        Raises:
            RuntimeError: raised if issues with the websocket arise
        """
        while self.alive:
            """
            The program relies on a command being sent from the client when
                the webpage closes but this command is inconsistent based on what device is being used.
                The socket is removed from the list of active sockets if an error occurs

            TODO: Fix the issue in a better way. This is more of a temporary fix but might just stay because it's
                not worth the effort to figure it out. This works.
            """
            newMessage = await self.socket.receive_text()
            if newMessage == "Disconnected":
                break
            message = json.loads(newMessage)
            if message:
                if message['action'] == "unload":
                    self.alive = False
                elif message['action'] == 'keys':
                    keys = (message['keys_down'], message['keys_up'])
                    websocket_list.keys(keys, self.index)
                elif message['action'] == 'keyboard_control_start':
                    websocket_list.start_keyboard_control(self.index)
                elif message['action'] == 'keyboard_control_release':
                    websocket_list.release_keyboard_control(self.index)
                else:
                    raise RuntimeError(
                        f"Action {message['action']} not recognized.")
        log(f"Socket closed: {self.index}")

        # Removes itself from the list of sockets so that the list does not get arbitrarily long if many devices are connecting
        # and disconnecting
        self.list.remove_key(self.index)

    def set_socket(self, socket: object) -> None:
        """
        Sets the socket passed from the client

        Args:
            socket (object): the Websocket object
        """
        self.socket = socket

class Websocket_List:
    """
    The list of all sockets and their indexes (indicies?)
        Also handles printing
        
    Attributes:
        sockets(dict): a dictionary of all active sockets
        keyboard_control_socket_index(int): the index of the socket with keyboard control
        loop(AbstractEventLoop): the asyncio event loop
        
    Methods:
        remove_key(key):
            Removes a socket from the list
        _find_lowest_key():
            Finds the lowest available number not in the list to be used for a new socket
        add_socket(socket):
            Adds a socket to the list
        print_out(socket_index, message, all, type):
            Outputs information to the client(s)
        print(socket_index, message, all, type):
            Takes information to be sent to ```print_out``` and creates an asynchronous task to output information
        start_keyboard_control(socket_index):
            Allows a client to take keyboard control if another does not already have control
        release_keyboard_control(socket_index):
            Releases keyboard control from a socket with control to allow a different client to control the robot
        keys(keys_changed, socket_index):
            Handles keyboard controls and relays them to the background process
    """
    def __init__(self):
        self.sockets = {}
        # A list of queued outputs
        self.keyboard_control_socket_index = -1
        self.loop = asyncio.get_event_loop()

    def remove_key(self, key: str) -> None:
        """
        Removes a socket from the list

        Args:
            key (str): the index of the socket to remove
        """
        if key in self.sockets:
            self.sockets.pop(key, None)

    def _find_lowest_key(self) -> str:
        """
        Finds the lowest available number not in the list to be used for a new socket

        Returns:
            str: the number, as a string
        """
        for i in range(0, len(self.sockets) + 1):
            if str(i) not in self.sockets:
                return str(i)

    def add_socket(self, socket: object) -> str:
        """
        Adds a socket to the list


        Args:
            socket (object): the socket to be added

        Returns:
            str: the index of the socket, determined during the procedure
        """

        new_index = self._find_lowest_key()
        new_socket = Websocket(socket, self, new_index)
        self.sockets[new_index] = new_socket
        return new_index

    async def print_out(self, socket_index: any, message: str, all: bool = False, type: str = "output") -> None:
        """
        Outputs information to the client(s)

        Args:
            socket_index (int, str): the index of the socket to output to (-1 can be used to denote that there are multiple sockets)
            message (str): the information to be outputted
            all (bool, optional): whether all sockets should receive the information. Defaults to False.
            type (str, optional): the type of information being sent. Defaults to "output".
        """
        if socket_index == -1 and not all:
            print(message)
            return 
        try:
            if all:
                for sI in self.sockets:
                    await self.sockets[sI].socket.send_json({
                        "type": type,
                        "output": message
                    })
            # Outputs to a single specified socket
            else:
                try:
                    await self.sockets[socket_index].socket.send_json({
                        "type": type,
                        "output": message
                    })
                except KeyError:
                    print("KEY ERORR: ", socket_index)
                    print("MESSAGE: ", message)
        except Exception as e:
            if str(e) == "Unexpected ASGI message 'websocket.send', after sending 'websocket.close'.":
                pass
            else:
                self.print(-1, str(message), all=True)
                # print(e)
                # print(message)
                # print("ERROR IN SOCKETS")

    def print(self, socket_index: any, message: str, all: bool = False, type: str = "output") -> None:
        """
        Takes information to be sent to ```print_out``` and creates an asynchronous task to output information

        see ```print_out``` method for argument information
        """
        asyncio.ensure_future(self.print_out(socket_index, message, all=all, type=type), loop=self.loop)

    def start_keyboard_control(self, socket_index: str) -> None:
        """
        Allows a client to take keyboard control if another does not already have control

        Args:
            socket_index str: the index of the socket attemtping to take control
        """
        if not background_process.bg_process.is_handling_keyboard_commands:
            background_process.bg_process.is_handling_keyboard_commands = True
            self.keyboard_control_socket_index = socket_index

    def release_keyboard_control(self, socket_index: str) -> None:
        """
        Releases keyboard control from a socket with control to allow a different client to control the robot

        Args:
            socket_index (str): the index of the socket reliquishing control
        """
        
        if socket_index == self.keyboard_control_socket_index:
            self.keyboard_control_socket_index = -1
            background_process.bg_process.is_handling_keyboard_commands = False

    def keys(self, keys_changed: list, socket_index: str) -> None:
        """
        Handles keyboard controls and relays them to the background process

        See ```background_process.bg_process.keyboard``` method for implentation of keyboard inputs

        Args:
            keys_changed (list): the keys changed, both keypresses and keyups
            socket_index (str): the index of the socket with the key changes
        """
        # Only the socket that currently has control can send commands
        if socket_index == self.keyboard_control_socket_index:
            background_process.bg_process.keyboard(keys_changed)


# Creates an instance of the Websocket_list() class. I don't like declaring it globally like this
# but I don't know of any other way.
websocket_list = Websocket_List()


def close_all_sockets() -> None:
    """
        Closes all sockets
        Called when the server is shutting down
    """
    for _, socket in websocket_list.sockets.items():
        socket.alive = False
    print("\033[92m" + "    Websockets" + "\033[0m" + ": Closing sockets")
    time.sleep(0.5)
