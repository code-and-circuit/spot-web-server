from importlib import reload
import time 
import sys
import math
import linecache
import hashlib

from SpotSite import spot_control, secrets, websocket

import bosdyn.client, bosdyn.client.lease
from bosdyn.client.robot_command import RobotCommandClient
from bosdyn.client.estop import EstopEndpoint, EstopKeepAlive, EstopClient
from bosdyn.client.power import power_off

class Background_Process:
    def __init__(self):
        # Tells if background program is running (if it's connected to the robot)
        self.is_running = False
        # Tells if a program is being run from a file
        self.program_is_running = False
        # Tells if commands from scratch are being run
        self.is_running_scratch_commands = False
        # Tells if someone is controlling the robot with the keyboard
        self.is_handling_keyboard_commands = False
        # Tells what mode the keyboard control is in (walk or stand)
        self.keyboard_control_mode = "Walk"
        # The class needed to send motor commands to the robot (sit, stand, walk, etc.)
        self.robot_control = None
        # Needed to send commands to the robot
        self.command_client = None
        self.lease_client = None
        self.command_queue = []
        self.estop_keep_alive = None
        self.robot_is_estopped = False
        self.robot = None
        self.lease = None
        # The index of the socket that sent the command to run a program. Used to output
        # any information to the right client
        self.program_socket_index = 0
        
    def print(self, socket_index, message, all=False, type="output"):
        # If socket index == -1, then the command came from Scratch, so there is no websocket to output to
        if socket_index == -1: 
            print(message)
        else:
            websocket.websocket_list.print(socket_index, message, all=all, type=type)
            
        if socket_index == -1 and all:
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
        
    def turn_on(self, socket_index):
        self.print(socket_index, "Powering On...")
        self.robot.power_on(timeout_sec=20)
        if not self.robot.is_powered_on():
            self.print(socket_index, "<red>Robot Power On Failed</red>")
            return False
        else:
            self.print(socket_index, "Powered On")
            return True
        
    def turn_off(self, socket_index):
        self.print(socket_index, "Powering off...")
        self.robot.power_off(cut_immediately=False, timeout_sec=20)
        if self.robot.is_powered_on():
            self.print(socket_index, "<red>Robot power off failed</red>")
            return False
        else:
            self.print(socket_index, "Powered Off")
            return True
        
    def estop(self):
        if self.estop_keep_alive and not self.robot.is_estopped():
            self.print(0, "estop", all=True, type="estop")
            self.robot_is_estopped = True
            self.estop_keep_alive.stop()
            self.command_queue = []
            
    def release_estop(self):
        if self.estop_keep_alive and self.robot.is_estopped():
            self.print(0, "estop_release", all=True, type="estop")
            self.robot_is_estopped = False
            self.estop_keep_alive.allow()
            
    def get_checksum(self):
        # Used to detect file changes for hot reload (not currently used)
        with open("spot_control.py", "rb") as f:
            newCheckSum = hashlib.md5(f.read()).hexdigest()
        return newCheckSum
    
    def acquire_lease(self, socket_index):
        # Connects to the robot and acquires a lease
        # TODO: Handle lease acquisition better. Sometimes if the server attempts to connect to quickly after being disconnected,
        # errors with lease acquisition occur
        try:
            sdk = bosdyn.client.create_standard_sdk('server_spot_client')
            
            self.robot = sdk.create_robot('192.168.80.3')
            self.robot.authenticate(secrets.username, secrets.password)
            self.robot.time_sync.wait_for_sync()
            
            if self.robot.is_estopped():
                self.print(socket_index, "Robot is estopped. Cannot connect.")
                return False
            
            self.lease_client = self.robot.ensure_client(bosdyn.client.lease.LeaseClient.default_service_name)
            self.lease = self.lease_client.acquire()
            return True
        except Exception as e:
            self.robot = None
            self.print_exception(socket_index)
            self.print(socket_index, "<red>Failed to accquire lease</red>")
            self.clear_values(-1)
            return False
        
    def acquire_estop(self, socket_index):
        try:
            estop_client = self.robot.ensure_client(EstopClient.default_service_name)
            ep = EstopEndpoint(estop_client, name="will-estop", estop_timeout=20) 
            ep.force_simple_setup()
            self.estop_keep_alive = EstopKeepAlive(ep)
            return True
        except Exception as e:  
            self.print_exception(socket_index)
            self.print(socket_index, "<red>Failed to accquire Estop</red>")
            self.clear_values(-1)
            return False
        
    def clear_values(self, socket_index):
            if self.estop_keep_alive:
                self.estop_keep_alive.shutdown()
                
            if self.robot:
                self.turn_off(socket_index)
                
            if self.lease_client:
                self.lease_client.return_lease(self.lease)
                
            self.estop_keep_alive = None
            self.robot = None    
            self.lease_client = None
            self.command_client = None
            self.robot_is_estopped = False
            self.is_running = False
            self.program_is_running = False
            self.is_handling_keyboard_commands = False
            self.is_running_scratch_commands = False
            self.command_queue = []
            
            self.print(socket_index, "end", all=True, type="bg_process")

    def start(self, socket_index):
        # Starts the background process / connects to robot and stays connected
                
        self.print(socket_index, "Connecting...")
        
        if not self.acquire_lease(socket_index):
            return
        
        self.robot_is_estopped = False

        '''
        if not self.acquire_estop(socket_index):
            return
        '''
        
        self.print(socket_index, "<green>Connected</green>")
        self.print(socket_index, "Background process started from device " + socket_index, all=True)
        self.print(socket_index, "start", all=True, type="bg_process")
        
        # TODO: Automatically reconnect to the robot if it powers off by itself
        try:
            with bosdyn.client.lease.LeaseKeepAlive(self.lease_client):
                if not self.turn_on(socket_index):
                    raise Exception("Failed to turn robot back on.")
                # Command client necessary for sending motor commands to the robot
                self.command_client = self.robot.ensure_client(RobotCommandClient.default_service_name)
                self.robot_control = spot_control.Spot_Control(self.command_client, -1)
                                                        
                self.is_running = True
                while self.is_running:
                    '''
                    if self.robot_is_estopped != self.robot_is_estopped:
                        self.print(socket_index, "Robot Estop status does not match internal Estop status", all=True)
                        self.is_running = False
                    '''
                        
                    if not self.robot.is_powered_on():
                        self.clear_values(-1)
                        if not self.acquire_lease(-1):
                            raise Exception("Failed to reacquire lease")
                        '''
                        if not self.acquire_estop(socket_index):
                            raise Exception("Failed to reacquire estop")
                        '''
                        if not self.turn_on(socket_index):
                            raise Exception("Failed to turn robot on")
                    # If the program is not already running and if no instance of spot function exists, run the program.
                    # An instance of a spot function can exist without the program being run if commands are being sent from Scratch
                    if self.program_is_running:
                        # Reload the file to allow for changes
                        time.sleep(0.2)
                        reload(spot_control)
                        time.sleep(0.2)
                        try:
                            self.robot_control.socket_index = self.program_socket_index
                            self.robot_control.do_function()
                        except:
                            self.print_exception(self.program_socket_index)
                            
                        self.program_is_running = False
                    # If there are commands in the queue from Scratch and no program is already running, run the commands
                    # from the queue. All commands in the queue will be executed before anything else is allowed to happen.
                    # Currently, all commands from Scratch are executed by the same instance of the Spot_Control class. Since
                    # feedback cannot be sent back to Scratch, there is no reason to create a new instance every time
                    # TODO: Allow queued command execution to halt or pause based on user input or a special command type. Maybe a chunk
                    # of code from a single source could be run at a time, and then the next chunk does not run until further user input?
                    elif self.command_queue:
                        self.is_running_scratch_commands = True
                        self.robot_control.socket_index = -1
                        while self.command_queue:
                            command = self.command_queue[0]
                            try:
                                self.do_command(command)
                            except:
                                self.print_exception(socket_index)
                            self.command_queue.pop(0) 
                        self.is_running_scratch_commands = False
                        
        finally:
            # IMPORTANT: turn of the robot and return the lease
            # TODO: Do this automatically when the server shuts off or something fails. The robot should do it automatically
            # but it's good practice to do it from the client side
            self.clear_values(-1)
            
    def do_command(self, command):
        # Executes commands from the queue
        action = command['Command']
        
        if action == 'stand':
            self.robot_control.stand()
        
        if action == 'sit':
            self.robot_control.sit()
            
        if action == 'rotate':
            args = command['Args']
            pitch = float(args['pitch'])
            yaw = float(args['yaw'])
            roll = float(args['roll'])
            
            self.robot_control.rotate(math.radians(yaw), math.radians(roll), math.radians(pitch))
        
        if action == 'move':
            args= command['Args']
            x = float(args['x'])
            y = float(args['y'])
            z = float(args['z'])
            
            self.robot_control.walk(x, y, z, d=1)
            
    def do_keyboard_commands(self, keys_pressed):
        if keys_pressed['space']:
            self.keyboard_control_mode = "Walk" if self.keyboard_control_mode == "Stand" else "Stand"
            return
        if self.program_is_running or self.is_running_scratch_commands or not self.robot_control:
            return
        
        self.robot_control.socket_index = -1
        
        if keys_pressed['space']:
            self.robot_control.stand()
            return
        
        d_x = 0
        d_y = 0
        d_z = 0
                
        if keys_pressed['w']:
            d_x += 1
        if keys_pressed['s']:
            d_x -= 1
            
        if keys_pressed['a']:
            d_y += 1
        if keys_pressed['d']:
            d_y -= 1
            
        if keys_pressed['q']:
            d_z += 1
        if keys_pressed['e']:
            d_z -= 1
            
        if keys_pressed['r']:
            self.robot_control.stand()
        elif keys_pressed['f']:
            self.robot_control.sit()
        else:
            if self.keyboard_control_mode == "Walk":
                self.robot_control.keyboard_walk(d_x, d_y * 0.5, d_z)
            elif self.keyboard_control_mode == "Stand":
                self.robot_control.keyboard_rotate(d_y, -d_z, d_x)
        
    def start_bg_process(self, socket_index):
         # Create a thread so the background process can be run in the background
        from threading import Thread
        thread = Thread(target=self.start, args=(socket_index))
        thread.start()
        
    def end_bg_process(self):
        self.is_running = False
        
    def run_program(self):
        self.program_is_running = True
            
# Creates an instance of the background_process class used for interacting with the background process connected to the robot
# Don't like declaring it globally in this way but not sure how else to do it
bg_process = Background_Process()
    
# Handles actions from the client
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
            bg_process.end_bg_process()
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
            bg_process.program_socket_index = socket_index
            bg_process.run_program()
            bg_process.print(socket_index, "Running Program")
            
    elif action == "estop":
        bg_process.estop()
    elif action == "estop_release":
        bg_process.release_estop()
    
    elif action == "check_if_running":
        return bg_process.is_running
    
    else:
        bg_process.print(socket_index, f"Command not recognized: {action}")