import asyncio
from threading import Thread

class Websocket:
    def __init__(self, s, l, i):
        self.socket = s
        self.alive = True
        self.list = l
        self.index = i
        
    async def open(self):
        await self.socket.accept()
        return
    
    async def close(self):
        await self.socket.close()
        return
        
    async def keep_alive(self):
        while self.alive:
            try:
                message = await self.socket.receive_text()
            except:
                self.list.remove_key(self.index)
            if message == "unload":
                self.alive = False
        await self.close()
        self.list.remove_key(self.index)
        return
        
    def set_socket(self, s):
        self.socket = s
        

        
class Websocket_List:
    def __init__(self):
        self.sockets = {}
        self.print_queue = []
        thread = Thread(target=self.start_print_loop)
        thread.start()
        
    def remove_key(self, key):
        self.sockets.pop(key, None)
    def add_socket(self, s):
        for i in range(0, len(self.sockets) + 1):
            if str(i) not in self.sockets:   
                new_socket = Websocket(s, self, str(i))
                self.sockets[str(i)] = new_socket
                return str(i)
        
    async def print_out(self, socket_index, message, all=False, type="output"):
        if all:
            for sI in self.sockets:
                await self.sockets[sI].socket.send_json({
                    "type" : type,
                    "output" : message
                })

        else:
            await self.sockets[socket_index].socket.send_json({
                "type" : type,
                "output" : message
            })
            
    async def print_loop(self):
        while True:
            if self.print_queue:
                await self.print_out(self.print_queue[0]['socket_index'], self.print_queue[0]["message"])
                self.print_queue.pop(0)
                
    def start_print_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.print_loop())
        loop.close()
        print("LOOP STARTED")
            
    def print(self, socket_index, message, all=False, type="output"):
        self.print_queue.append({
            "socket_index": socket_index,
            "message": message,
            "all": all,
            "type": type
        })
    
websocket_list = Websocket_List()