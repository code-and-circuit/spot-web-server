import hashlib
from importlib import reload

from SpotSite import spotFunction, secrets, websocket

import time, sys, math

import bosdyn.client, bosdyn.client.lease

from bosdyn.client.robot_command import RobotCommandClient
from bosdyn.client.power import power_off

import linecache
import sys

class Spot_Main:
    def __init__(self):
        self.is_running = False
        self.run_function = False
        self.spot_function = None
        self.command_client = None
        self.command_queue = []
        self.socket_index_program_start = 0
        
    def print(self, socket_index, message, all=False, type="output"):
        assert socket_index != -1, print(message)
        websocket.websocket_list.print(socket_index, message, all=all, type=type)

    def print_exception(self, socket_index):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        self.print(socket_index, f'<red<Exception</red> {exc_obj} <br>in {filename} line {lineno}')
        
    def turn_on(self, robot, socket_index):
        self.print(socket_index, "Powering On...")
        robot.power_on(timeout_sec=20)
        assert robot.is_powered_on(), "Robot Power On Failed"
        self.print(socket_index, "Powered On")
        
    def turn_off(self, robot, socket_index):
        robot.power_off(cut_immediately=False, timeout_sec=20)
        assert not robot.is_powered_on(), self.print(socket_index, "<red>Robot power off failed</red>")
        self.print(socket_index, "Powered Off")
        
    def get_checksum(self):
        with open("spotFunction.py", "rb") as f:
            newCheckSum = hashlib.md5(f.read()).hexdigest()
        return newCheckSum

    def start(self, socket_index):
        
        if self.is_running:
            self.print(socket_index, "Cannot start background process because background process is already running")
            return
        
        self.print(socket_index, "Connecting...")
        
        try:
            sdk = bosdyn.client.create_standard_sdk('will_spot_client')
            
            robot = sdk.create_robot('192.168.80.3')
            robot.authenticate(secrets.username, secrets.password)
            robot.time_sync.wait_for_sync()
            
            assert not robot.is_estopped(), self.print(socket_index, "Robot is estopped. The program will now exit.")
            
            lease_client = robot.ensure_client(bosdyn.client.lease.LeaseClient.default_service_name)
            lease = lease_client.acquire()
        except Exception as e:
            self.print_exception(socket_index)
            self.print(socket_index, "<red>Connection Failed</red>")
            print("FAILED")
            return
        
        self.print(socket_index, "<green>Connected</green>")
        self.print(socket_index, "Background process started from device " + socket_index, all=True)
        self.print(socket_index, "start", all=True, type="bg_close")
        
        try:
            with bosdyn.client.lease.LeaseKeepAlive(lease_client):
                self.turn_on(robot, socket_index)
                self.command_client = robot.ensure_client(RobotCommandClient.default_service_name)
                                        
                self.is_running = True
                while self.is_running:
                    if self.run_function and not self.spot_function:
                        time.sleep(0.2)
                        reload(spotFunction)
                        time.sleep(0.2)
                        try:
                            self.spot_function = spotFunction.SpotFunction(self.command_client, self.socket_index_program_start)
                            self.spot_function.do_function()
                        except:
                            self.print_exception(self.socket_index_program_start)
                        self.run_function = False
                        self.spot_function = None
                        
                    elif self.command_queue:
                        while self.command_queue:
                            command = self.command_queue[0]
                            try:
                                do_command(command)
                            except:
                                self.print_exception(socket_index)
                            self.command_queue.pop(0) 
                        self.spot_function = None
                        
        finally:
            self.turn_off(robot, socket_index)
            lease_client.return_lease(lease)
            
    def do_command(command):
        self.socket_index_program_start = -1
        self.spot_function = spotFunction.SpotFunction(self.command_client, self.socket_index_program_start)
        action = command['action']
        args = command['args']
        
        if action == 'stand':
            self.spot_function.stand()
            
    
class background_process:
    def __init__(self):
        self.main_function = Spot_Main()
        
    def start(self, socket_index):
        self.main_function.start(socket_index)
        
    def startFunction(self):
        self.main_function.run_function = True
        
    def end(self):
        self.main_function.is_running = False
    
bg_process = background_process()

def start_bg_process(socket_index):
    from threading import Thread
    thread = Thread(target=bg_process.start, args=(socket_index))
    thread.start()
    
def end_bg_process():
    bg_process.end()

def do_action(action, socket_index, args=None):
    if action == "start":
        print("START")
        if not bg_process.main_function.is_running:    
            print("STARTING")        
            from threading import Thread
            
            new_thread = Thread(target=start_bg_process, args=[socket_index])
            new_thread.start()
        print("STARTED")

    elif action == "end":
        if bg_process.main_function.is_running:
            end_bg_process(socket_index)
            bg_process.main_function.print(socket_index, "Background process ended")
        else:
            bg_process.main_function.print(socket_index, "Cannot end background process because background process is not running")
            
    elif action == "run_program":
        if not bg_process.main_function.is_running:
            bg_process.main_function.print(socket_index, "Cannot run program because background process is not running")
            return
        if bg_process.main_function.run_function:
            bg_process.main_function.print(socket_index, "Cannot run program because program is already running")
            return
        bg_process.main_function.socket_index_program_start = socket_index
        bg_process.startFunction()
        bg_process.main_function.print(socket_index, "Running Program")
    
    elif action == "check_if_running":
        return bg_process.main_function.is_running
    
    else:
        bg_process.main_function.print(socket_index, f"Command not recognized: {action}")