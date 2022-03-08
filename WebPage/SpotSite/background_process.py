from importlib import reload
import time, sys, math, linecache, hashlib

from SpotSite import spot_control, secrets, websocket

import bosdyn.client, bosdyn.client.lease
from bosdyn.client.robot_command import RobotCommandClient
from bosdyn.client.power import power_off

# TODO: Make code cleaner, possibly remove the need for the background_process class
# -- Should be done, just need to check to make sure it runs properly when connected to the robot --

class Background_Process:
    def __init__(self):
        # Tells if background program is running (if it's connected to the robot)
        self.is_running = False
        # Tells if a program is being run from a file
        self.program_is_running = False
        # The class needed to send motor commands to the robot (sit, stand, walk, etc.)
        self.spot_control_class = None
        self.scratch_spot_control_class = spot_control.Spot_Control(self.command_client, -1)
        self.command_client = None
        self.command_queue = []
        # The index of the socket that sent the command to run a program. Used to output
        # any information to the right client
        self.socket_index_program_start = 0
        
    def print(self, socket_index, message, all=False, type="output"):
        # If socket index == -1, then the command came from Scratch, so there is no websocket to output to
        if socket_index == -1: 
            print(message)
        else:
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
        if not robot.is_powered_on():
            self.print(socket_index, "<red>Robot Power On Failed</red>")
        else:
            self.print(socket_index, "Powered On")
        
    def turn_off(self, robot, socket_index):
        self.print(socket_index, "Powering off...")
        robot.power_off(cut_immediately=False, timeout_sec=20)
        if robot.is_powered_on():
            self.print(socket_index, "<red>Robot power off failed</red>")
        else:
            self.print(socket_index, "Powered Off")
        
    def get_checksum(self):
        # Used to detect file changes for hot reload (not currently used)
        with open("spot_control.py", "rb") as f:
            newCheckSum = hashlib.md5(f.read()).hexdigest()
        return newCheckSum

    def start(self, socket_index):
        # Starts the background process / connects to robot and stays connected
                
        self.print(socket_index, "Connecting...")
        
        try:
            # Connects to the robot and acquires a lease
            # TODO: Handle lease acquisition better. Sometimes if the server attempts to connect to quickly after being disconnected,
            # errors with lease acquisition occur
            sdk = bosdyn.client.create_standard_sdk('server_spot_client')
            
            robot = sdk.create_robot('192.168.80.3')
            robot.authenticate(secrets.username, secrets.password)
            robot.time_sync.wait_for_sync()
            
            if robot.is_estopped():
                self.print(socket_index, "Robot is estopped. The program will now exit.")
                return
            
            lease_client = robot.ensure_client(bosdyn.client.lease.LeaseClient.default_service_name)
            lease = lease_client.acquire()
        except Exception as e:
            self.print_exception(socket_index)
            self.print(socket_index, "<red>Connection Failed</red>")
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
                    if self.program_is_running and not self.spot_control_class:
                        # Reload the function to allow for changes
                        time.sleep(0.2)
                        reload(spot_control)
                        time.sleep(0.2)
                        try:
                            self.spot_control_class = spot_control.Spot_Control(self.command_client, self.socket_index_program_start)
                            self.spot_control_class.do_function()
                        except:
                            self.print_exception(self.socket_index_program_start)
                            
                        self.program_is_running = False
                        self.spot_control_class = None
                    # If there are commands in the queue from Scratch and no program is already running, run the commands
                    # from the queue. All commands in the queue will be executed before anything else is allowed to happen.
                    # Currently, all commands from Scratch are executed by the same instance of the Spot_Control class. Since
                    # feedback cannot be sent back to Scratch, there is no reason to create a new instance every time
                    # TODO: Allow queued command execution to halt or pause based on user input or a special command type. Maybe a chunk
                    # of code from a single source could be run at a time, and then the next chunk does not run until further user input?
                    elif self.command_queue:
                        while self.command_queue:
                            command = self.command_queue[0]
                            try:
                                do_command(command)
                            except:
                                self.print_exception(socket_index)
                            self.command_queue.pop(0) 
                        self.spot_control_class = None
                        
        finally:
            # IMPORTANT: turn of the robot and return the lease
            # TODO: Do this automatically when the server shuts off or something fails. The robot should do it automatically
            # but it's good practice to do it from the client side
            self.turn_off(robot, socket_index)
            lease_client.return_lease(lease)
            
    def do_command(command):
        # Executes commands from the queue
        action = command['action']
        args = command['args']
        
        if action == 'stand':
            self.scratch_spot_control_class.stand()
            
        
            
    def start_bg_process(self, socket_index):
         # Create a thread so the background process can be run in the background
        from threading import Thread
        thread = Thread(target=self.start, args=(socket_index))
        thread.start()
        
    def end_bg_process(self):
        self.is_running = False
        
    def run_program(self):
        self.program_is_running = True
            

# Can potentially be removed but is nice for readability in code handling actions from the client
# -- UNUSED --
class background_process:
    def __init__(self):
        self.main_function = Background_Process()
        
    def start(self, socket_index):
        self.main_function.start(socket_index)
        
    def run_program(self):
        self.main_function.program_is_running = True
        
    def end(self):
        self.main_function.is_running = False
        
    def start_bg_process(self, socket_index):
        # Create a thread so the background process can be run in the background
        from threading import Thread
        thread = Thread(target=self.start, args=(socket_index))
        thread.start()
    
# Creates an instance of the background_process class used for interacting with the background process connected to the robot
# Don't like declaring it globally in this way but not sure how else to do it
bg_process = Background_Process()
    
# Handles actions from the client
# background_process class helps with readability here
def do_action(action, socket_index, args=None):
    if action == "start":
        # Makes sure that the background process is not already running before it starts it
        if bg_process.is_running:
            bg_process.print(socket_index,
            "Cannot start background process because background process is already running") 
        else:
            bg_process.start_bg_process(socket_index)      
            
    elif action == "end":
        # Makes sure that the background process is running before it ends it
        if not bg_process.is_running:
            bg_process.print(socket_index, 
            "Cannot end background process because background process is not running")
        else:
            bg_process.end()
            bg_process.print(socket_index, "Background process ended")
            
    elif action == "run_program":
        # Makes sure that the background process is running (robot is connected) before it tries to run a program
        if not bg_process.is_running:
            bg_process.print(socket_index, 
            "Cannot run program because background process is not running")
        # Makes sure that a program is not already running before it runs one
        elif bg_process.program_is_running:
            bg_process.print(socket_index, 
            "Cannot run program because program is already running")
        else:
            bg_process.socket_index_program_start = socket_index
            bg_process.run_program()
            bg_process.print(socket_index, "Running Program")
    
    elif action == "check_if_running":
        return bg_process.is_running
    
    else:
        bg_process.print(socket_index, f"Command not recognized: {action}")