import asyncio
import json
import time
from threading import Thread
import background_process

# A class to hold a websocket and its information
# I did not write the class for the python websocket
class Websocket:
    def __init__(self, s, l, i):
        self.socket = s
        self.alive = True
        self.list = l
        self.index = i
    
    # Opens the socket
    async def open(self):
        await self.socket.accept()

    # Closes the socket
    async def close(self):
        await self.socket.close()
        
    # Keeps the socket alive
    async def keep_alive(self):
        while self.alive:
            # The program relies on a command being sent from the client when
            # the webpage closes but this command is inconsistent based on what device is being used.
            # The socket is removed from the list of active sockets if an error occurs
            
            # TODO: Fix the issue in a better way. This is more of a temporary fix but might just stay because it's
            # not worth the effort to figure it out. This works.            
            newMessage = await self.socket.receive_text()
            message = json.loads(newMessage)

            '''
            try:
                pass
            except Exception as e:
                print("EXCEPTION: ", e)
                self.alive = False
                self.list.remove_key(self.index)
            '''
            
            
            if message:
                if message['action'] == "unload":
                    self.alive = False
                elif message['action'] == 'key_press':
                    websocket_list.key_press(message['keys_pressed'], self.index)
                elif message['action'] == 'keyboard_control_start':
                    websocket_list.start_keyboard_control(self.index)
                elif message['action'] == 'keyboard_control_release':
                    websocket_list.release_keyboard_control(self.index)
                    
        try:    
            await self.close()
        except RuntimeError:
            print("ERROR CLOSING SOCKET")
            print(self.socket._client_state)
        # Removes itself from the list of sockets so that the list does not get arbitrarily long if many devices are connecting
        # and disconnecting
        self.list.remove_key(self.index)

    # Sets the socket passed from the client        
    def set_socket(self, s):
        self.socket = s
        

# The list of all sockets and their indexes (indicies? this isn't an english class)
# Also handles printing
class Websocket_List:
    def __init__(self):
        self.sockets = {}
        # A list of queued outputs
        self.keyboard_control_socket_index = -1
        self.loop_is_running = False
        
    # Removes a socket from the list
    def remove_key(self, key):
        if key in self.sockets:
            self.sockets.pop(key, None)
        
    # Adds a socket to the list
    def add_socket(self, s):
        # Chooses the minimum index needed for the incoming socket. Not technically needed but if it was not used,
        # the socket indices could get large over time. Cleaner and easier to always use the smallest number necessary.
        # The socket index is completely arbitrary as the client holds the index for its own socket. The index does not refer
        # to a position in a list, it's simply an identifier. Maybe the term "ID" is better
        for i in range(0, len(self.sockets) + 1):
            if str(i) not in self.sockets:   
                new_socket = Websocket(s, self, str(i))
                self.sockets[str(i)] = new_socket
                return str(i)
    
    # Outputs messages to the client. Almost all messages are just output, but there is one that 
    # is sent when the background process is sucessfully started, so that all clients are updated to show that
    # the background process is running
    async def print_out(self, socket_index, message, all=False, type="output"):
        # Outputs to every socket
        try:
            if all:
                for sI in self.sockets:
                    await self.sockets[sI].socket.send_json({
                        "type" : type,
                        "output" : message
                    })
            # Outputs to a single specified socket
            else:
                try:
                    await self.sockets[socket_index].socket.send_json({
                        "type" : type,
                        "output" : message
                    })
                except KeyError:
                    print ("KEY ERORR: ", socket_index)
                    print("MESSAGE: ", message)
        except Exception as e:
            print(self.sockets)
            print(e)
            print("ERROR IN SOCKETS")
                
    # Used to add an output to the queue of outputs
    def print(self, socket_index, message, all=False, type="output"):
        asyncio.run(self.print_out(socket_index, message, all=all, type=type))
        
    def start_keyboard_control(self, socket_index):
        if not background_process.bg_process.is_handling_keyboard_commands:
            background_process.bg_process.is_handling_keyboard_commands = True
            self.keyboard_control_socket_index = socket_index
        
    def release_keyboard_control(self, socket_index):
        if socket_index == self.keyboard_control_socket_index:
            self.keyboard_control_socket_index = -1
            background_process.bg_process.is_handling_keyboard_commands = False
    
    def key_press(self, keys_pressed, socket_index):
        if socket_index == self.keyboard_control_socket_index:
            background_process.bg_process.do_keyboard_commands(keys_pressed)
    
# Creates an instance of the Websocket_list() class. I don't like declaring it globally like this
# but I don't know of any other way.
websocket_list = Websocket_List()