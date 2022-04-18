# General system imports
import time 
import sys
import os
import math
import linecache
import hashlib
import cv2
import io
import pathlib
import asyncio
import base64
from threading import Thread
from importlib import reload
import numpy as np
import nest_asyncio
from pil import Image
nest_asyncio.apply()

# Interproject imports
import spot_control
from SpotSite import secrets
from SpotSite import websocket
from spot_logging import log_action
from Stitching import stitch_images

# Boston Dynamics imports
import bosdyn.client
import bosdyn.client.lease
from bosdyn.client.robot_command import RobotCommandClient
from bosdyn.client.estop import EstopEndpoint
from bosdyn.client.estop import EstopKeepAlive
from bosdyn.client.estop import EstopClient
from bosdyn.client.time_sync import TimeSyncClient
from bosdyn.client.time_sync import TimeSyncThread
from bosdyn.client.power import power_off
from bosdyn.client.image import ImageClient

def start_thread(func, args=None):
    thread = Thread(target=func, args=args)
    thread.start()

class Background_Process:
    def __init__(self):
        # Boilerplate
        self._sdk = None
        self.robot = None
        self._robot_control = None
        
        # Clients
        self._command_client = None
        self._lease_client = None
        self._image_client = None
        self._estop_client = None
        self._time_sync_client = None
        
        # Robot control
        self._lease = None
        self._lease_keep_alive = None
        self._estop_keep_alive = None
        self._time_sync_thread = None

        # Server state
        self.is_running = False
        self._is_connecting = False
        self.program_is_running = False
        self.is_running_commands = False
        self.is_handling_keyboard_commands = False
        self.robot_is_estopped = False
        self._show_video_feed = True
        
        self._has_lease = False
        self._has_estop = False
        self._has_time_sync = False
        
        self.keyboard_control_mode = "Walk"
        self.program_name = ""
        self.program_socket_index = 0
        
        self.command_queue = []
        self.programs = {}
        self._keys_up = []
        self._keys_down = []
        
        self.image_stitcher = None
        
    def print(self, socket_index, message, all=False, type="output"):    
        websocket.websocket_list.print(socket_index, message, all=all, type=type)

    def print_exception(self, socket_index):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print("Type: " + exc_type.__name__)
        print("File: ", fname)
        print("Object: ", exc_obj)
        print("Line number: " + str(exc_tb.tb_lineno))
        #self.print(socket_index, str(exc_type) + "; " + str(fname) + "; "  + str(exc_tb.tb_lineno))
        #self.print(socket_index, f'<red<Exception</red> {exc_type} <br>in {fname} line {exc_tb.tb_lineno} <br> {line}')
        
    @log_action
    def turn_on(self, socket_index):
        self.print(socket_index, "Powering On...")
        self.robot.power_on(timeout_sec=20)
        # Checks to make sure that the robot successfully powered on
        if not self.robot.is_powered_on():
            self.print(socket_index, "<red>Robot Power On Failed</red>")
            return False
        else:
            self.print(socket_index, "Powered On")
            return True
        
    @log_action
    def turn_off(self, socket_index):
        self.print(socket_index, "Powering off...")
        self.robot.power_off(cut_immediately=False, timeout_sec=20)
        # Checks to make sure that the robot successfully powered on
        if self.robot.is_powered_on():
            self.print(socket_index, "<red>Robot power off failed</red>")
            return False
        else:
            self.print(socket_index, "Powered Off")
            return True
     
    @log_action
    def _acquire_lease(self, socket_index):
        if self._lease_client is not None:
            self.print(socket_index, "Lease already acquired")
            return True
        
        success = True
        self._is_connecting = True
        
        try:
            if self.robot.is_estopped():
                raise Exception("Robot is estopped. Cannot Acquire Lease.")
            
            self._lease_client = self.robot.ensure_client(bosdyn.client.lease.LeaseClient.default_service_name)
            self._lease = self._lease_client.acquire()
            self._lease_keep_alive = bosdyn.client.lease.LeaseKeepAlive(self._lease_client)
            
            self._has_lease = True
            
        except Exception as e:
            self.print_exception(socket_index)
            self.print(socket_index, "<red>Failed to accquire lease</red>")
            success = False
            self._clear_lease()
            
        finally:
            self._is_connecting = False
        
        return success
        
    @log_action
    def _acquire_estop(self, socket_index):
        if self._estop_client is not None:
            self.print(socket_index, "Estop already acquired")
            return True
        
        success = True
        self._is_connecting = True
        
        try:
            self._estop_client = self.robot.ensure_client(EstopClient.default_service_name)
            ep = EstopEndpoint(self._estop_client, name="cc-estop", estop_timeout=20) 
            ep.force_simple_setup()
            self._estop_keep_alive = EstopKeepAlive(ep)
            self.robot_is_estopped = False
            
            self._has_estop = True
            
        except:
            self.print_exception(socket_index)
            self.print(socket_index, "<red>Failed to accquire Estop</red>")
            success = False
            self._clear_estop()
            
        finally:
            self._is_connecting = False
        
        return success
        
    @log_action
    def _acquire_time_sync(self, socket_index):
        if self._time_sync_client is not None:
            return True
        
        success = True
        self._is_connecting = True
        
        try:
            self._time_sync_client = self.robot.ensure_client(TimeSyncClient.default_service_name)
            self._time_sync_thread = TimeSyncThread(self._time_sync_client)
            self._time_sync_thread.start()
            
            self._has_time_sync = True
            
        except:
            self.print_exception(socket_index)
            self.print(socket_index, "Failed to accquire Time Sync")
            success = False
            self._clear_time_sync()
            
        finally:
            self._is_connecting = False
                
        return success
    
    @log_action
    def _connect_to_robot(self, socket_index):
        if self.robot is not None:
            self.print(socket_index, "Robot is already connected")
            return True
        
        success = True
        self._is_connecting = True
        
        try:
            self._sdk = bosdyn.client.create_standard_sdk('cc-server')
            
            self.robot = self._sdk.create_robot(secrets.ROBOT_IP)
            self.robot.authenticate(secrets.ROBOT_USERNAME, secrets.ROBOT_PASSWORD)
            
            if not self._acquire_time_sync(socket_index): raise
            
            self._image_client = self.robot.ensure_client(ImageClient.default_service_name)
            self._start_video_loop()
            
            self._command_client = self.robot.ensure_client(RobotCommandClient.default_service_name)
            self._robot_control = spot_control.Spot_Control(self._command_client, socket_index, self.robot)
                        
        except:
            self.print_exception(socket_index)
            self.print(socket_index, "<red>Failed to connect to the robot</red>")
            success = False
            self._disconnect_from_robot()
            
        finally:
            self._is_connecting = False
        
        return success

    @log_action
    def _connect_all(self, socket_index):
        self.print(socket_index, "Starting...")
        
        if not self._connect_to_robot(socket_index):
            return False
        
        if not self._acquire_estop(socket_index):
            return False
        
        if not self._acquire_lease(socket_index):
            return False
                
        return True
        
    @log_action
    def estop(self):
        if self._estop_keep_alive and not self.robot.is_estopped():
            self.print(0, "estop", all=True, type="estop")
            self.robot_is_estopped = True
            self._estop_keep_alive.settle_then_cut()
            # Clear command queue so the robot does not execute commands the instant
            # the estop is released
            self.command_queue = []
        
    @log_action    
    def release_estop(self):
        if self._estop_keep_alive and self.robot.is_estopped():
            self.print(0, "estop_release", all=True, type="estop")
            self.robot_is_estopped = False
            self._estop_keep_alive.allow()
        
    @log_action
    def _clear(self, socket_index): 
        
        self._clear_lease()
        self._clear_estop()
        self._clear_time_sync()
        self._disconnect_from_robot()
        
        self.is_running = False
        self._is_connecting = False
        self.program_is_running = False
        self.is_running_commands = False
        self.robot_is_estopped = False
        
        self.keyboard_control_mode = "Walk"
        
        self.command_queue = []
        self.programs = {}
        self.keys = {}
    
    @log_action
    def _clear_lease(self):
        if self._lease_keep_alive and self.robot.is_powered_on():
            self.turn_off(-1)
            
        if self._lease_client and self._lease:
            self._lease_client.return_lease(self._lease)
        
        self._lease_keep_alive.shutdown()
        self._lease_keep_alive = None
        self._lease = None
        self._lease_client = None
        self._has_lease = False
        
    @log_action
    def _clear_estop(self):
        if self._has_lease:
            self._clear_lease()
        
        self._estop_keep_alive.settle_then_cut()
        self._estop_keep_alive.shutdown()
        self._estop_keep_alive = None
        self._estop_client = None
        self._has_estop = False
        
    @log_action
    def _clear_time_sync(self):
        if not self.robot:
            return
        
        if self._time_sync_thread:
            self._time_sync_thread.stop()
        
        self._time_sync_client = None
        self._time_sync_thread = None
        self._has_time_sync = False
        
    @log_action
    def _disconnect_from_robot(self):
        if self._has_lease or self._has_estop:
            self._clear_estop()
        if self._has_time_sync:
            self._clear_time_sync()
        
        self._show_video_feed = False
        self._image_client = None
        
        self._robot_control = None
        self._command_client = None
        self.robot = None
        self._sdk = None
        
    @log_action
    def start(self, socket_index):
        if not self._connect_all(socket_index):
            self.print(socket_index, "<red>Failed to start processes</red>")
            return

        self.print('Connecting...')
        self.print(socket_index, "<green>Connected</green>")
        self.print(socket_index, "start", all=True, type="bg_process")
                
        self._background_loop(socket_index)
        
        self._clear(socket_index)
            
    @log_action
    def _background_loop(self, socket_index):
        try:
            if not self.turn_on(socket_index):
                raise Exception("<red>Failed to turn robot on.</red>")

            self.is_running = True                
            while self.is_running:
                self._keep_robot_on(socket_index)
                self._run_programs(socket_index)
                self._execute_commands(socket_index)
                        
        except:
            self.print_exception(socket_index)

    def _keep_robot_on(self, socket_index):
        if not self.robot.is_powered_on() and not self.robot.is_estopped() and not self._robot_control.is_rolled_over:
            if not self.turn_on(-1):
                raise Exception("Failed to turn robot back on")
            
    def _execute_commands(self, socket_index):
        if self.command_queue:
            self.is_running_commands = True
            self._robot_control.socket_index = -1
            while self.command_queue:
                command = self.command_queue[0]
                try:
                    self._do_command(command)
                except:
                    self.print_exception(socket_index)
                self.command_queue.pop(0) 
            self.is_running_commands = False
        
    def _run_programs(self, socket_index):
        if self.program_is_running:
            try:
                for command in self.programs[self.program_name]:
                    self._do_command(command)
            except:
                self.print_exception(self.program_socket_index)
            self.program_is_running = False
    
    @log_action
    def _start_video_loop(self):
        self._show_video_feed = True

        start_thread(self._video_loop)

    def _video_loop(self):
        self.image_stitcher = stitch_images.Stitcher()
        start_thread(self.image_stitcher.start_glut_loop)
        while self._show_video_feed:
            self._get_images()
            time.sleep(0.2)

    def _stitch_images(self, image1, image2):
        return self.image_stitcher.stitch(image1, image2)
    
    def _encode_base64(self, image):
        if image is None:
            print("Image is none")
            return
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        
        bytes_image = buf.getvalue()
        
        return base64.b64encode(bytes_image).decode("utf8")
        
    def _get_images(self):
        self._get_image("front")
        
    def _get_image(self, camera_name):
        if camera_name == "front":
            front_right = self._image_client.get_image_from_sources(["frontright_fisheye_image"])[0]
            front_left = self._image_client.get_image_from_sources(["frontleft_fisheye_image"])[0]
            
            image = self._stitch_images(front_right, front_left)
        
        self.print(-1, self._encode_base64(image), all=True, type=("@" + camera_name))

    @log_action
    def _do_command(self, command):
        # Executes commands from the queue
        action = command['Command']
        
        if action == 'stand':
            self._robot_control.stand()
        
        if action == 'sit':
            self._robot_control.sit()
            
        if action == 'wait':
            time.sleep(command['Args']['time'])
            
        if action == 'rotate':
            args = command['Args']
            pitch = float(args['pitch'])
            yaw = float(args['yaw'])
            roll = float(args['roll'])
            
            self._robot_control.rotate(math.radians(yaw), math.radians(roll), math.radians(pitch))
        
        if action == 'move':
            args= command['Args']
            x = float(args['x'])
            y = float(args['y'])
            z = float(args['z'])
            
            self._robot_control.walk(x, y, z, d=1)
    
    def key_up(self, key):
        return key in self._keys_up
    
    def key_down(self, key):
        return key in self._keys_down
    
    def _set_keys(self, keys_changed):
        self._keys_down = keys_changed[0]
        self._keys_up = keys_changed[1]
    
    def _do_keyboard_commands(self):
        if self.key_up('space'):
            self.keyboard_control_mode = "Walk" if self.keyboard_control_mode == "Stand" else "Stand"
            return self._robot_control.stand()
 
        if self.key_down('x'):
            return self._robot_control.roll_over()
        
        if self.key_down('z'):
            return self._robot_control.self_right()
            
        if self.key_down('r'):
            return self._robot_control.stand()
            
        if self.key_down('f'):
            return self._robot_control.sit()
        
        # Takes advantage of fact that True == 1 and False == 0. 
        # True - True = 0; True - False = 1; False - True = 0
        dx = self.key_down('w') - self.key_down('s')
        dy = self.key_down('a') - self.key_down('d')
        dz = self.key_down('q') - self.key_down('e')
        
        if self.keyboard_control_mode == "Walk":
            self._robot_control.keyboard_walk(dx, dy * 0.5,dz)
        elif self.keyboard_control_mode == "Stand":
            self._robot_control.keyboard_rotate(dy, -dz, dx)
            
    def keyboard(self, keys_changed):
        self._set_keys(keys_changed)
        
        if self.program_is_running or self.is_running_commands or not self._robot_control or not self.robot.is_powered_on():
           return
    
        self._do_keyboard_commands()
        self.print(-1, self.keyboard_control_mode, all=True, type="control_mode")
            
    @log_action
    def start_bg_process(self, socket_index):
         # Create a thread so the background process can be run in the background
        start_thread(self.start, args=(socket_index))
        
    @log_action
    def end_bg_process(self):
        self.is_running = False
        self._show_video_feed = False
        
    @log_action
    def add_program(self, name, program):
        self.programs[name] = program
        self.print(-1, self.programs, all=True, type="programs")    
        
    @log_action
    def set_program_to_run(self, name):
        if not self.programs[name]: return
        
        self.program_is_running = True
        self.program_name = name
            
# Creates an instance of the background_process class used for interacting with the background process connected to the robot
# Don't like declaring it globally in this way but not sure how else to do it
bg_process = Background_Process()

# Handles actions from the client
@log_action
def do_action(action, socket_index, args=None):
    if action == "start":
        # Makes sure that the background process is not already running before it starts it
        if bg_process.is_running:
            bg_process.print(socket_index,
            "Cannot start background process because background process is already running")
            return

        if bg_process._is_connecting:
            bg_process.print(socket_index, "Robot is already connecting!")
            return
        
        bg_process.start_bg_process(socket_index)      
            
    elif action == "end":
        # Makes sure that the background process is running before it ends it
        if not bg_process.is_running:
            bg_process.print(socket_index, 
            "Cannot end background process because background process is not running")
            return

        bg_process.end_bg_process()
        bg_process.print(socket_index, "Background process ended")
            
    elif action == "run_program":
        # Makes sure that the background process is running (robot is connected) before it tries to run a program
        bg_process.program_name = args
        if not bg_process.is_running:
            bg_process.print(socket_index, 
            "Cannot run program because background process is not running")
            return
        # Makes sure that a program is not already running before it runs one
        if bg_process.program_is_running:
            bg_process.print(socket_index, 
            "Cannot run program because a program is already running")
            return

        bg_process.program_socket_index = socket_index
        bg_process.set_program_to_run(args)
        bg_process.print(socket_index, "Running Program")
            
    elif action == "remove_program":
        bg_process.programs.pop(args, None)      
        bg_process.print(-1, bg_process.programs, all=True, type="programs")  
            
    elif action == "estop":
        bg_process.estop()
        
    elif action == "estop_release":
        
        bg_process.release_estop()
        
    elif action == "connect":
        if bg_process._is_connecting:
            bg_process.print(socket_index, "Robot is already connecting!")
            return
        start_thread(bg_process._connect_to_robot, args=(socket_index))
        
    elif action == "acquire_estop":
        if bg_process._is_connecting:
            bg_process.print(socket_index, "Robot is already connecting!")
            return
        if not bg_process.robot:
            bg_process.print(socket_index, "Cannot acquire Estop because robot is not connected!")
            return
        start_thread(bg_process._acquire_estop, args=(socket_index))
        
    elif action == "acquire_lease":
        if bg_process._is_connecting:
            bg_process.print(socket_index, "Robot is already connecting!")
            return
        if not bg_process.robot:
            bg_process.print(socket_index, "Cannot acquire lease because robot is not connected!")
            return
        if not bg_process._estop_client:
            bg_process.print(socket_index, "Cannot acquire lease because Estop has not been acquired!")
            return
        start_thread(bg_process._acquire_lease, args=(socket_index))
    
    elif action == "check_if_running":
        return bg_process.is_running
    
    else:
        bg_process.print(socket_index, f"Command not recognized: {action}")