import hashlib
from importlib import reload

from SpotSite import spotFunction, secrets, websocket

import time, sys, math

import bosdyn.client, bosdyn.client.lease

from bosdyn.client.robot_command import RobotCommandClient
from bosdyn.client.power import power_off

import linecache
import sys

# TODO: Make code cleaner, possible remove the need for the background_process class
# !! Renaming some classes may help !!

class Spot_Main:
    def __init__(self):
        # Tells if background program is running (if it's connected to the robot)
        self.is_running = False
        # Tells if a program is being run from a file
        self.program_is_running = False
        # The class needed to send motor commands to the robot (sit, stand, walk, etc.)
        self.spot_function = None
        self.command_client = None
        self.command_queue = []
        # The index of the socket that sent the command to run a program. Used to output
        # any information to the right client
        self.socket_index_program_start = 0
        
    def print(self, socket_index, message, all=False, type="output"):
        # If socket index == -1, then the command came from Scratch, so there is no websocket to output to
        assert socket_index != -1, print(message)
        websocket.websocket_list.print(socket_index, message, all=all, type=type)

    def print_exception(self, socket_index):
        # Copy and pasted from stack overflow. It works
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
        assert robot.is_powered_on(), "<red>Robot Power On Failed</red>"
        self.print(socket_index, "Powered On")
        
    def turn_off(self, robot, socket_index):
        self.print(socket_index, "Powering off...")
        robot.power_off(cut_immediately=False, timeout_sec=20)
        assert not robot.is_powered_on(), self.print(socket_index, "<red>Robot power off failed</red>")
        self.print(socket_index, "Powered Off")
        
    def get_checksum(self):
        # Used to detect file changes for hot reload (not currently used)
        with open("spotFunction.py", "rb") as f:
            newCheckSum = hashlib.md5(f.read()).hexdigest()
        return newCheckSum

    def start(self, socket_index):
        # Starts the background process / connects to robot and stays connected
        
        assert not self.is_running, self.print(socket_index, "Cannot start background process because background process is already running")
        
        self.print(socket_index, "Connecting...")
        
        try:
            # Connects to the robot and acquires a lease
            # TODO: Handle lease acquisition better. Sometimes if the server attempts to connect to quickly after being disconnected,
            # errors with lease acquisition occur
            sdk = bosdyn.client.create_standard_sdk('server_spot_client')
            
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
                # Command client necessary for sending motor commands to the robot
                self.command_client = robot.ensure_client(RobotCommandClient.default_service_name)
                                        
                self.is_running = True
                while self.is_running:
                    # If the program is not already running and if no instance of spot function exists, run the program.
                    # An instance of a spot function can exist without the program being run if commands are being sent from Scratch
                    if self.program_is_running and not self.spot_function:
                        # Reload the function to allow for changes
                        time.sleep(0.2)
                        reload(spotFunction)
                        time.sleep(0.2)
                        try:
                            self.spot_function = spotFunction.SpotFunction(self.command_client, self.socket_index_program_start)
                            self.spot_function.do_function()
                        except:
                            self.print_exception(self.socket_index_program_start)
                            
                        self.program_is_running = False
                        self.spot_function = None
                    # If there are commands in the queue from Scratch and no program is already running, run the commands
                    # from the queue. All commands in the queue will be executed before anything else is allowed to happen
                    # TODO: Allow queued command execution to halt or pause based on user input or a special command type
                    # TODO: Allow a chunk of commands to executed together and have the program wait until a command is sent to
                    # signifiy the end of a chunk. A chunk of code could also be run by a single spot_function instance
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
            # IMPORTANT: turn of the robot and return the lease
            # TODO: Do this automatically when the server shuts off or something fails. The robot should do it automatically
            # but it's good practice to do it from the client side
            self.turn_off(robot, socket_index)
            lease_client.return_lease(lease)
            
    def do_command(command):
        # Executes commands from the queue
        self.socket_index_program_start = -1
        self.spot_function = spotFunction.SpotFunction(self.command_client, self.socket_index_program_start)
        action = command['action']
        args = command['args']
        
        if action == 'stand':
            self.spot_function.stand()
            

# Can potentially be removed but is nice for readability in code handling actions from the client
class background_process:
    def __init__(self):
        self.main_function = Spot_Main()
        
    def start(self, socket_index):
        self.main_function.start(socket_index)
        
    def run_program(self):
        self.main_function.program_is_running = True
        
    def end(self):
        self.main_function.is_running = False
        
    def start_bg_process(socket_index):
        # Create a thread so the background process can be run in the background
        from threading import Thread
        thread = Thread(target=self.bg_process.start, args=(socket_index))
        thread.start()
    
# Creates an instance of the background_process class used for interacting with the background process connected to the robot
# Don't like declaring it globally in this way but not sure how else to do it
bg_process = background_process()
    
# Handles actions from the client, pretty intuitive
# background_process class helps with readability here
def do_action(action, socket_index, args=None):
    if action == "start":
        assert not bg_process.main_function.is_running, bg_process.main_function.print(socket_index,
            "Cannot start background process because background process is already running")  
        
        bg_process.start_bg_process(socket_index)      
            
    elif action == "end":
        assert bg_process.main_function.is_running, bg_process.main_function.print(socket_index, 
            "Cannot end background process because background process is not running")
        
        bg_process.end()
        bg_process.main_function.print(socket_index, "Background process ended")
            
    elif action == "run_program":
        assert bg_process.main_function.is_running, bg_process.main_function.print(socket_index, 
            "Cannot run program because background process is not running")
        assert not bg_process.main_function.program_is_running, bg_process.main_function.print(socket_index, 
            "Cannot run program because program is already running")

        bg_process.main_function.socket_index_program_start = socket_index
        bg_process.run_program()
        bg_process.main_function.print(socket_index, "Running Program")
    
    elif action == "check_if_running":
        return bg_process.main_function.is_running
    
    else:
        bg_process.main_function.print(socket_index, f"Command not recognized: {action}")