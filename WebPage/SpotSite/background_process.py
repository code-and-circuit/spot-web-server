"""
    Main server file

    Classes:
        
        SqliteConnection
        Background_Process
        
    Functions:

        start_thread(func, args)
        close()
        socket_print(socket_index, message, all, type)
        print_exception(socket_index)
        is_primitive(obj) -> bool
        is_not_special_function(obj) -> bool
        get_name(obj, lower) -> str
        is_jsonable(x) -> bool
        get_members(obj, depth) -> dict
        lock_until_finished(func) -> function
        read_json(filepath) -> json
        do_action(action, socket_index, args)
        
    Misc. variables:

        bg_process
        invalid_keywords
        max_depth
        lock
"""
# General system imports
import re
import time
import ctypes
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
import json
from threading import Thread
import threading
from importlib import reload
from pprint import pprint
import inspect
import types
import numpy as np
#import keyboard
import sqlite3
from pathlib import Path
import os
from PIL import Image
from io import BytesIO

# Interproject imports
from SpotSite import spot_control
from SpotSite import secrets
from SpotSite import websocket
from SpotSite.spot_logging import log_action
from SpotSite.Stitching import stitch_images

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

invalid_keywords = [
    'cert',
    'logger'
]

max_depth = 5

lock = threading.Lock()

def start_thread(func, args: tuple = ()):
    """Starts a new thread from the given function to

    Args:
        func (_type_): the function
        args (tuple, optional): any arguments passed to the function. Defaults to ().
    """
    thread = Thread(target=func, args=args)
    thread.start()

def close():
    """
    Helper function to help close the server properly. 
    
    """    
    bg_process.is_running = False
    while bg_process._is_shutting_down:
        pass
    print("\033[92m" + "    Background" +
          "\033[0m" + ": Disconnecting from robot")

def socket_print(socket_index: any, message: str, all: bool = False, type: str ="output"):
    """
    Outputs information to a given socket

    Args:
        socket_index any: the index of the socket object
        message (str): the information being sent
        all (bool, optional): whether all sockets should receive the information. Defaults to False.
        type (str, optional): what kind of information is being sent. Defaults to "output".
    """    
    websocket.websocket_list.print(
        socket_index, message, all=all, type=type)

def print_exception(socket_index: any):
    """
    Prints an exception with relevant information to a given socket

    Args:
        socket_index any: the index of the socket
    """
    # ")

    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    message = ""
    if (exc_type == bosdyn.client.lease.ResourceAlreadyClaimedError):
        message = "<red><b>Error:</b></red> A different device may have a lease,\
                      or the robot may not be fully turned on."
    elif (exc_type == bosdyn.client.exceptions.UnableToConnectToRobotError):
        message = "<red><b>Error:</b></red> Unable to connect to the robot. Is it turned on and connected\
            to the right WiFi?"
    elif (exc_type == bosdyn.client.estop.MotorsOnError):
        message = "<red><b>Error:</b></red> Unable to acquire Estop while the motors are turned on."
    elif (exc_type == bosdyn.client.power.EstoppedError):
        message = "<red><b>Error:</b></red> Robot cannot turn on while estopped."
    elif (exc_type == bosdyn.client.lease.NoSuchLease):
        message = "<red><b>Error:</b></red> Cannot perform this action: no lease for it has been acquired."
    elif (exc_type == bosdyn.client.lease.NotActiveLeaseError):
        print(f"Exception: {exc_obj} in {fname} line {exc_tb.tb_lineno}")
        return
    elif exc_type == bosdyn.client.exceptions.RpcError:
        message = "<red><b>Error:</b></red> Could not perform this action"
    elif exc_type == bosdyn.client.estop.InvalidIdError:
        print(f"Exception: {exc_obj} in {fname} line {exc_tb.tb_lineno}")
        return
    elif exc_type == bosdyn.client.exceptions.LeaseUseError:
        print(f"Exception: {exc_obj} in {fname} line {exc_tb.tb_lineno}")
        return
    elif exc_type == bosdyn.client.estop.EndpointUnknownError:
        print(f"Exception: {exc_obj} in {fname} line {exc_tb.tb_lineno}")
        return
    elif exc_type == bosdyn.client.power.CommandTimedOutError:
        print(f"Exception: {exc_obj} in {fname} line {exc_tb.tb_lineno}")
        return
    elif (exc_type == AttributeError):
        print(f"Exception: {exc_obj} in {fname} line {exc_tb.tb_lineno}")        
        return
    elif (exc_type == Exception):
        print(f"Exception: {exc_obj} in {fname} line {exc_tb.tb_lineno}")
        return
    else:
        message = f"<red><b>Exception</b></red><br>{exc_type}: {exc_obj}<br>&emsp; in <u>{fname}</u> line <red>{exc_tb.tb_lineno}</red>"
    
    if message == "":
        print(f"{exc_type}, line {exc_tb.tb_lineno}")
    else:
        socket_print(socket_index, message, all=(socket_index==-1))

def is_primitive(obj: object) -> bool:
    """
    Tells whether an object is of a primitive type

    Args:
        obj (object): The object

    Returns:
        bool: Whether the object type is primitive
    """    
    return not hasattr(obj, '__dict__')

def is_not_special_function(obj: object) -> bool:
    """
    Helper function to determine whether an object is a dunder method

    Args:
        obj (object): the object

    Returns:
        bool: Whether or not the object is a dunder method
    """    
    return not(obj[0].startswith("__") and obj[0].endswith("__"))

def get_name(obj: object, lower: bool = True) -> str:
    """
    Gets the name of an object

    Args:
        obj (object): The object
        lower (bool, optional): Whether or not the returned string should be lowercase. Defaults to True.

    Returns:
        str: The name of the object
    """    
    name = obj.__name__ if hasattr(obj, '__name__') else type(obj).__name__

    return name.lower() if lower else name

def is_jsonable(x: object) -> bool:
    """
    Tests whether an object can be passed in a JSON request

    Args:
        x (object): The object

    Returns:
        bool: Whether the object can be passed through a JSON request
    """    
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False

def get_members(obj: object, depth: int = 0) -> dict:
    """
    Recursively gets attributes of an object

    Args:
        obj (object): The targrt object
        depth (int, optional): The recursion depth. Defaults to 0.

    Returns:
        dict: A nested dictionary containing all attributes of objects
    """    
    # This is all a single-line return statement. 
    # Did it just for fun, it was boring with multiple lines
    
    return ({
        ((key.__name__ if 
          hasattr(key, '__name__') else 
            type(key).__name__).lower() if hasattr(key, '__dict__') else key):
        get_members(value, depth=depth+1) if (
            hasattr(value, '__dict__') and
            True not in [s.lower() in (value.__name__ if 
                                       hasattr(value, '__name__') else 
                                       type(value).__name__).lower() or 
                         s.lower() in str(key).lower() for s in invalid_keywords]
        ) else (
            [get_members(item) for item in value] if isinstance(value, list) else (
                "function" if type(value) == types.LambdaType else (
                    (value.__name__ if 
                     hasattr(value, '__name__') else 
                        type(value).__name__) if hasattr(value, '__dict__') else (
                        get_members(value, depth=depth+1) if isinstance(value, dict) else (
                            value if (is_jsonable(value)) else (
                                'Not JSONable'
                            )
                        )
                    )
                )
            )
        ) if True not in [s.lower() in (value.__name__ if 
                                        hasattr(value, '__name__') else 
                                        type(value).__name__).lower() or 
                          s.lower() in str(key).lower() for s in invalid_keywords] else (
            (value.__name__ if 
                hasattr(value, '__name__') 
                    else type(value).__name__)
        )
        for key, value in (obj.__dict__.items() if hasattr(obj, '__dict__') else obj.items())
    } if hasattr(obj, '__dict__') or isinstance(obj, dict) else obj) if depth < max_depth else "MAX RECURSION"

def lock_until_finished(func):
    """
    Locks the thread until a function is finished executing
    
    Necessary for using SQL in an asynchronous context

    Args:
        func (callable): The function
    """    
    def wrapper(*args, **kwargs):
        lock.acquire(True)
        val = func(*args, **kwargs)
        lock.release()
        return val
    return wrapper

def read_json(filepath: str) -> dict:
    """
    Reads json fron a file and returns the data

    Args:
        filepath (str): The filepath (from the parent directory)

    Returns:
        dict: the json data
    """    
    path = Path(__file__).resolve().parent.parent
    path = os.path.join(path, filepath)
    file = open(str(path))
    data = json.load(file)
    file.close()
    return data

class SqliteConnection:
    """
    A class to manage the connection to the SQL database containing programs
    
    Attributes:
        _connection (sqlite3.Connection): the connection to the database
        _cursor (sqlite3.Cursor): the cursor used to interact with the database
        
    Methods:
        _name_exists(name):
            Tells whether a program already exists with the given name
        write_program(name, program):
            Writes a program to the database
        delete_program(name):
            Deletes a program from the database
        get_program(name):
            Returns a program with a given name
        get_all_programs():
            Returns all programs in the database
        close()
            Closes the cursor and the database connection
    """    
    @lock_until_finished
    def __init__(self):
        path = Path(__file__).resolve().parent.parent
        path = os.path.join(path, 'db.sqlite3')
        self._connection = sqlite3.connect(path, check_same_thread = False)
        self._cursor = self._connection.cursor()
        
        self._cursor.execute('CREATE TABLE IF NOT EXISTS Programs (name TEXT, program TEXT)')
    
    def _name_exists(self, name: str) -> bool:
        """Tells whether a program already exists with the given name

        Args:
            name (str): the name of the program

        Returns:
            bool: whether the program exists
        """        
        query = self._cursor.execute("SELECT EXISTS (SELECT 1 FROM Programs WHERE name=? COLLATE NOCASE) LIMIT 1", (name,))
        return query.fetchone()[0]
    
    @lock_until_finished
    def write_program(self, name: str, program: tuple):
        """
        Writes a program to the database

        Args:
            name (str): the name of the database
            program (tuple, list): the program
        """        
        if self._name_exists(name):
            self._cursor.execute('UPDATE Programs SET program = ? WHERE name = ?', (program, name))
        else:
            self._cursor.execute('INSERT INTO Programs VALUES (?, ?)', (name, program))
        self._connection.commit()
    
    @lock_until_finished  
    def delete_program(self, name: str):
        """
        Deletes a program from the database

        Args:
            name (str): the name of the program
        """        
        self._cursor.execute("DELETE FROM Programs WHERE name=?", (name,))
        self._connection.commit()
        
    @lock_until_finished
    def get_program(self, name: str) -> tuple:
        """
        Returns a program with a given name

        Args:
            name (str): the name of the program

        Returns:
            tuple: the program
        """        
        query = self._cursor.execute("SELECT program FROM Programs WHERE name = ?", (name,))
        command_string = ''.join(query.fetchone()[0])
        return json.loads(command_string)
    
    @lock_until_finished
    def get_all_programs(self) -> tuple:
        """
        Returns all programs in the database

        Returns:
            tuple: The list of programs
        """        
        query = self._cursor.execute("SELECT name, program FROM Programs").fetchall()
        return query

    @lock_until_finished
    def close(self):
        """
        Closes the cursor and the database connection
        """        
        self._cursor.close()
        self._connection.close()

class Background_Process:
    """
    The main class to manage a connection with Spot and perform tasks
    
    Attributes:
        _sdk(bosdyn.client.sdk.Sdk): The Boston Dynamics sdk object
        robot(bosdyn.client.robot.Robot): The Boston Dynamics robot object
        _robot_control(spot_control.Spot_Control): The object used to send motor commands to Spot
        
        _command_client(bosdyn.client.robot_command.RobotCommandClient): The Boston Dynamics command client object
        _lease_client(bosdyn.client.lease.LeaseClient): The Boston Dynamics lease client object
        _image_client(bosdyn.client.image.ImageClient): The Boston Dynamics image client object
        _estop_client(bosdyn.client.estop.EstopClient): The Boston Dyanmics estop client object
        _time_sync_client(bosdyn.client.time_sync.TimeSyncClient): The Boston Dynamics time sync client 
        
        _lease(bosdyn.client.lease.Lease): The Boston Dynamics lease object
        _lease_keep_alive(bosdyn.client.lease.LeaseKeepAlive): The Boston Dynamics object to keep the active lease alive
        _estop_keep_alive(bosdyn.client.estop.EstopKeepAlive): The Boston Dynamics object to keep the active estop alive
        _time_sync_thread(bosdyn.client.time_sync.TimeSyncThread): The Boston Dyanmics object for maintaining a time sync with Spot
        
        is_running(bool): Whether the main background process is running
        _is_connecting(bool): Whether the server is currently connecting a service
        program_is_running(bool): Whether a program is currently running
        is_running_commands(bool): Whether the server is currently running commands from the command queue
        is_handling_keyboard_commands(bool): Whether the server is currently handling commands from the keyboard
        robot_is_estopped(bool): Whether Spot is currently estopped
        _show_video_feed(bool): Whether video feed should be displayed and active
        _is_shutting_down(bool): Whether the server is in the process of shutting down
        _has_lease(bool): Whether the server has an active lease with Spot
        _has_estop(bool): Whether the server has active estop cut authority with Spot
        _has_time_sync(bool): Whether the server has an active time sync with Spot
        keyboard_control_mode(str): Which keyboard control mode is active ```"Walk" or "Stand"```
        active_program_name(str): The name of the program currently being executed
        program_socket_index(str): The index of the socket that send the command to execute the currently executing program
        is_accepting_commands(bool): Whether the server is currenly accepting robot commands
        command_queue(list): The queue of commands to be sent to Spot
        _keys_up(list): The list of keyups in the last frame from the socket with keyboard control authority
        _keys_down(list): The list of keypresses in the last frame from the socket with keyboard control authority
        image_stitcher(stitch_images.Stitcher): The object used to stitch the right and left front camera images    
        _program_database(SqliteConnection): The object used to maintain a connection with and perform tasks on the SQL database
        
    Methods:
        _load_defaults(filepath):
            loads default settings
        turn_on(socket_index):
            Attempts to turn on Spot
        turn_off(socket_index):
            Attempts to turn off Spot
        _acquire_lease(socket_index):
            Attemps to acquire a lease from Spot
        _acquire_estop(socket_index):
            Attempts to acquire estop cut authority from Spot
        _acquire_time_sync(socket_index):
            Attempts to acquire a time sync with 
        _robot_is_on_wifi(ip):
            Tells whether Spot is detected at a particular IP address on the wifi
        _connect_to_robot(socket_index):
            Attempts to connect to Spot
        _connect_all(socket_index):
            Attempts to connect to Spot, acquire an estop, and acquire a lease
        estop():
            Estops Spot
        release_estop():
            Releases any active Estop on Spot
        toggle_estop():
            Toggles the estop on Spot
        _clear(socket_index):
            Disconnects all services and resets all information
        _clear_lease():
            Returns and clears any active lease with Spot
        _clear_estop():
            Returns and clears any active estop authority with Spot
        _clear_time_sync():
            Returns and clears any active time sync with Spot
        _disconnect_from_robot():
            Disconnects from Spot
        start(socket_index):
            Attempts to start the main background process, including connecting all services
        _background_loop(socket_index):
            Starts and houses the main background loop
        _keep_robot_on(socket_index):
            Turns Spot back on if it turns off for no discernable reason
        _execute_commands(socket_index):
            Executes commands in the command queue
        _run_program(socket_index):
            Runs the program corresponding to the name of the active program being executed
        _start_video_loop():
            Creates a thread to start the main video loop
        _video_loop():
            Houses and runs the main video feed loop
        get_robot_state():
            Returns the state of Spot (Boston Dyanmics RobotState object)
        update_robot_state():
            Updates clients with the most recent robot state information
        _stitch_images(image1, image2):
            Sttiches the right and left from camera images
        _encode_base64(image):
            Encodes an image in base64
        _get_images():
            Gets and displays all relevant images for the video feed
        _get_image(camera_name):
            Gets and updates the client with an image
        _do_command(command):
            Executes a command from the queue
        key_up(key):
            Returns whether a keyup event happened for a specific key in the last frame
        key_down(key):
            Returns whether a keydown event happened for a specific key in the last frame
        _set_keys(keys_changed):
            Sets object attributes to the most recent keyboard events to be used in other methods
        _do_keyboard_commands():
            Executes a command based on which keys were pressed in the last frame
        keyboard(keys_changed):
            Updates the keys changed, runs keyboard commands, and updates client with the control mode (Walk or Stand)
        start_bg_process(socket_index):
            Creates a thread so the background process can be run in the background
        end_bg_process():
            Updates the server with information to shut down
        get_programs():
            Returns a list of all programs in the database
        add_program(name, program):
            Adds a program to the database
        remove_program(name):
            Removes a program from the database
        set_program_to_run(name):
            Sets a program to run
        get_state_of_everything():
            Returns a nested dictionary of the state of all attributes of the main background process class
        get_keyboard_control_state():
            Returns information about the keyboard control state
        get_internal_state():
            Returns information about the internal state of the server
        get_server_state():
            Returns the internal state and the keyboard control state

        
        
    """    
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
        self._is_shutting_down = False

        self._has_lease = False
        self._has_estop = False
        self._has_time_sync = False

        self.keyboard_control_mode = "Walk"
        self.active_program_name = ""
        self.program_socket_index = ""

        self._is_accepting_commands = False
        self._will_immediately_run_commands = False
        self._should_run_commands = False
        self.command_queue = []
        self._keys_up = []
        self._keys_down = []

        self.image_stitcher = None
        self._program_database = SqliteConnection()

        self.default_data = self._load_defaults()

    def _load_defaults(self, filepath = "./SpotSite/config.json") -> dict:
        """
        Loads default settings for the server

        Args:
            filepath (str, optional): the filepath(from the parent directory). Defaults to "/SpotSite/config.json".
        
        Returns:
            dict: the default data
        """        
        data = read_json(filepath)["defaults"]
        self._is_accepting_commands = data['accept_commands']
        self._will_immediately_run_commands = data['immediately_run_commands']
        return data

        
    def turn_on(self, socket_index: any) -> bool:
        """
        Attempts to turn on Spot

        Args:
            socket_index any: The index of the socket to display information to

        Returns:
            bool: Whether the action was successful
        """        
        socket_print(socket_index, "Powering On...")
        try:
            self.robot.power_on(timeout_sec=20)
        except Exception as e:
            print_exception(socket_index)
        # Checks to make sure that Spot successfully powered on
        robot_is_powered_on = False
        try:
            robot_is_powered_on = self.robot.is_powered_on()
        except:
            pass
        if not robot_is_powered_on:
            socket_print(socket_index, "<red>Robot Power On Failed</red>")
            return False
        else:
            socket_print(socket_index, "Powered On")
            return True

    def turn_off(self, socket_index: any) -> bool:
        """
        Attempts to turn off Spot

        Args:
            socket_index any: The index of the socket to display information to

        Returns:
            bool: Whether the action was successful
        """        
        socket_print(socket_index, "Powering off...")
        try:
            self.robot.power_off(cut_immediately=False, timeout_sec=20)
        except:
            print_exception(socket)
        # Checks to make sure that Spot successfully powered off
        if self.robot.is_powered_on():
            socket_print(socket_index, "<red>Robot power off failed</red>")
            return False
        else:
            socket_print(socket_index, "Powered Off")
            return True

    def _acquire_lease(self, socket_index: any) -> bool:
        """
        Attempts to acquire a lease from Spot

        Args:
            socket_index any: The index of the socket to display information to

        Raises:
            Exception: Raises if Spot is estopped

        Returns:
            bool: Whether the action was successful
        """        
        if self._lease_client is not None:
            socket_print(socket_index, "Lease already acquired")
            return True

        success = True
        self._is_connecting = True

        try:
            # if self.robot.is_estopped():
            #     raise Exception("Robot is estopped. Cannot Acquire Lease.")
            socket_print(socket_index, "Acquiring Lease...")
            self._lease_client = self.robot.ensure_client(
                bosdyn.client.lease.LeaseClient.default_service_name)
            self._lease = self._lease_client.acquire()
            self._lease_keep_alive = bosdyn.client.lease.LeaseKeepAlive(
                self._lease_client)

            self._has_lease = True
            socket_print(socket_index, "<green>Acquired Lease</green>")
            socket_print(-1, "acquire", all=True, type="lease_toggle")

        except Exception as e:
            print_exception(socket_index)
            socket_print(socket_index, "<red>Failed to accquire lease</red>")
            success = False
            self._clear_lease()

        finally:
            self._is_connecting = False

        return success

    def _acquire_estop(self, socket_index: any) -> bool:
        """
        Attempts to acquire estop cut authority from Spot

        Args:
            socket_index any: The index of the socket to display information to

        Returns:
            bool: Whether the action was successful
        """        
        
        if self._estop_client is not None:
            socket_print(socket_index, "Estop already acquired")
            return True

        success = True
        self._is_connecting = True

        try:
            socket_print(socket_index, "Acquiring Estop...")
            self._estop_client = self.robot.ensure_client(
                EstopClient.default_service_name)
            ep = EstopEndpoint(self._estop_client,
                               name="cc-estop", estop_timeout=20)
            ep.force_simple_setup()
            self._estop_keep_alive = EstopKeepAlive(ep)
            self.robot_is_estopped = False

            self._has_estop = True
            socket_print(socket_index, "<green>Acquired Estop</green>")
            socket_print(-1, "acquire", all=True, type="estop_toggle")

        except:
            print_exception(socket_index)
            socket_print(socket_index, "<red>Failed to accquire Estop</red>")
            success = False
            self._clear_estop()

        finally:
            self._is_connecting = False

        return success

    def _acquire_time_sync(self, socket_index: any) -> bool:
        """
        Attempts to acquire a time sync with Spot

        Args:
            socket_index any: The socket of the index to display information to

        Returns:
            bool: Whether the action was successful
        """        
        if self._time_sync_client is not None:
            return True

        success = True
        self._is_connecting = True

        try:
            self._time_sync_client = self.robot.ensure_client(
                TimeSyncClient.default_service_name)
            self._time_sync_thread = TimeSyncThread(self._time_sync_client)
            self._time_sync_thread.start()

            self._has_time_sync = True

        except:
            print_exception(socket_index)
            socket_print(socket_index, "Failed to accquire Time Sync")
            success = False
            self._clear_time_sync()

        finally:
            self._is_connecting = False

        return success

    def _robot_is_on_wifi(self, ip: str = secrets.ROBOT_IP) -> bool:
        """
        Tells whether Spot is detected at a particular IP address on the wifi

        Args:
            ip (str, optional): The ip of Spot. Defaults to secrets.ROBOT_IP.

        Returns:
            bool: Whether a ping was successful
        """        
        try:
            is_admin = os.getuid() == 0
        except AttributeError:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if is_admin:
            response = os.system(f"ping {ip} -c 1")
            return True if response == 0 else False
        else:
            return True


    def _connect_to_robot(self, socket_index: any) -> bool:
        """
        Attempts to connect to Spot
        
        Acquires clients and creates necessary objects for communication and interation with Spot

        Args:
            socket_index any: The socket of the index to display information to

        Raises:
            Exception: Raises if a time sync could not be acquired with Spot

        Returns:
            bool: Whether the action was successful
        """        
        
        if self.robot is not None:
            socket_print(socket_index, "Robot is already connected")
            return True

        socket_print(socket_index, "Connecting to robot...")
        if not self._robot_is_on_wifi():
            socket_print(socket_index, "<red><b>Robot is not at the specified address!</b></red> Is it on the wifi?")
            return False

        success = True
        self._is_connecting = True
    
        try:
            self._sdk = bosdyn.client.create_standard_sdk('cc-server')

            self.robot = self._sdk.create_robot(secrets.ROBOT_IP)
            self.robot.authenticate(
                secrets.ROBOT_USERNAME, secrets.ROBOT_PASSWORD)

            if not self._acquire_time_sync(socket_index):
                raise Exception("Could not acquire time sync with Spot")

            self._image_client = self.robot.ensure_client(
                ImageClient.default_service_name)
            self._start_video_loop()

            self._command_client = self.robot.ensure_client(
                RobotCommandClient.default_service_name)
            self._robot_control = spot_control.Spot_Control(
                self._command_client, socket_index, self.robot)
            
            socket_print(-1, "acquire", all=True, type="robot_toggle")
            socket_print(socket_index, "<green>Connected to robot</green>")

        except:
            print_exception(socket_index)
            socket_print(
                socket_index, "<red>Failed to connect to Spot</red>")
            success = False
            self._disconnect_from_robot()

        finally:
            self._is_connecting = False

        return success

    def _connect_all(self, socket_index: any) -> bool:
        """
        Attempts to connect to Spot, acquire an estop, and acquire a lease

        Args:
            socket_index any: The socket of the index to output to

        Returns:
            bool: Whether all actions were successful
        """    
        socket_print(socket_index, "Starting...")

        if not self._connect_to_robot(socket_index):
            return False

        if not self._acquire_estop(socket_index):
            return False

        if not self._acquire_lease(socket_index):
            return False

        return True

    def estop(self) -> None:
        """
        Estops Spot
        """        
        if not self._has_estop:
            socket_print(-1, "Estop Not Acquired", all=True)
            return
        if self._estop_keep_alive and not self.robot.is_estopped():
            socket_print(0, "estop", all=True, type="estop")
            self.robot_is_estopped = True
            self._estop_keep_alive.settle_then_cut()
            self._is_accepting_commands = False
            # Clear command queue so Spot does not execute commands the instant
            # the estop is released
            self.command_queue = []

    def release_estop(self) -> None:
        """
        Releases any active Estop on Spot
        """        
        if not self._has_estop:
            return
        if self._estop_keep_alive and self.robot.is_estopped():
            socket_print(0, "estop_release", all=True, type="estop")
            self.robot_is_estopped = False
            self._estop_keep_alive.allow()

    def toggle_estop(self) -> None:
        """
        Toggles the estop on Spot
        """       
        if not self._has_estop:
            return

        if self.robot.is_estopped():
            self.release_estop()
        else:
            self.estop()

    def _clear(self, socket_index: any) -> None:
        """
        Disconnects all services and resets all information

        Args:
            socket_index any: The index of the socket to output to
        """        
        self._is_shutting_down = True
        self._show_video_feed = False
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
        self._is_shutting_down = False

        # pprint(self.get_state_of_everything())

    def _clear_lease(self) -> None:
        """
        Returns and clears any active lease with Spot
        """        
        self._has_lease = False
        if self.robot:
            if self._lease_keep_alive and self.robot.is_powered_on():
                self.turn_off(-1)
                while self.robot.is_powered_on():
                    pass

        if self._lease_client and self._lease:
            try:
                self._lease_client.return_lease(self._lease)
            except:
                print_exception(-1)

        if self._lease_keep_alive:
            self._lease_keep_alive.shutdown()

        self._lease_keep_alive = None
        self._lease = None
        self._lease_client = None
        
        socket_print(-1, "clear", all=True, type="lease_toggle")

    def _clear_estop(self) -> None:
        """
        Returns and clears any active estop authority with Spot
        """        
        if self._has_lease:
            self._clear_lease()

        if self._estop_keep_alive:
            self._estop_keep_alive.settle_then_cut()
            try:
                self._estop_keep_alive.shutdown()
            except AttributeError:
                pass

        self._estop_keep_alive = None
        self._estop_client = None
        self._has_estop = False
        
        socket_print(-1, "clear", all=True, type="estop_toggle")

    def _clear_time_sync(self) -> None:
        """
        Returns and clears any active time sync with Spot
        """        
        if not self.robot:
            return

        if self._time_sync_thread:
            self._time_sync_thread.stop()

        self._time_sync_client = None
        self._time_sync_thread = None
        self._has_time_sync = False

    def _disconnect_from_robot(self) -> None:
        """
        Disconnects from Spot
        """        
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
        
        socket_print(-1, "clear", all=True, type="robot_toggle")

    def start(self, socket_index: any) -> None:
        """
        Attempts to start the main background process, including connecting all services

        Args:
            socket_index any: The index of the socket to output to
        """        
        socket_print(socket_index, 'Connecting...')

        if not self._connect_all(socket_index):
            socket_print(socket_index, "<red>Failed to start processes</red>")
            return

        socket_print(socket_index, "<green>Connected</green>")
        socket_print(socket_index, "start", all=True, type="bg_process")
        self.update_robot_state()
        self._background_loop(socket_index)

        self._clear(socket_index)

    def _background_loop(self, socket_index: any) -> None:
        """
        Starts and houses the main background loop

        Args:
            socket_index any: The index of the socket to output to

        Raises:
            Exception: Raises if Spot fails to turn on
        """        
        if not self.turn_on(socket_index):
            return
        try:
            self.is_running = True
            while self.is_running:
                self._keep_robot_on(socket_index)
                self._run_programs(socket_index)
                self._execute_commands(socket_index)

        except:
            print_exception(socket_index)

    def _keep_robot_on(self, socket_index: any) -> None:
        """
        Turns Spot back on if it turns off for no discernable reason

        Args:
            socket_index any: The index of the socket to output to

        Raises:
            Exception: Raises if Spot fails to turn on
        """        
        if self.robot is None:
            self.is_running = False
            return
        if not self.robot.is_powered_on() and not self.robot.is_estopped()\
            and not self._robot_control._is_rolled_over and self._has_lease:
            if not self.turn_on(-1):
                raise Exception("Failed to turn robot back on")

    def _execute_commands(self, socket_index: any) -> None:
        """
        Executes commands in the command queue

        Args:
            socket_index any: The index of the socket to output to
        """        
        if self.command_queue:
            self.is_running_commands = True
            self._robot_control.socket_index = -1
            if self._should_run_commands:
                command = self.command_queue[0]
                try:
                    self._do_command(command)
                except:
                    print_exception(socket_index)
                try:
                    self.command_queue.pop(0)
                except IndexError:
                    socket_print(socket_index, "Command List is empty!")
                self._should_run_commands = False
                self._update_command_queue()

            while self.command_queue and self._will_immediately_run_commands:
                command = self.command_queue[0]
                try:
                    self._do_command(command)
                except:
                    print_exception(socket_index)
                try:
                    self.command_queue.pop(0)
                except IndexError:
                    socket_print(socket_index, "Command List is empty!")
                self._update_command_queue()
        self.is_running_commands = False
        self._should_run_commands = False

    def _update_command_queue(self):
        socket_print(-1, json.dumps(self.command_queue), all=True, type="command_queue")

    def add_command(self, data):
        self.command_queue.append(data)
        self._update_command_queue()

    def _run_programs(self, socket_index: any) -> None:
        """
        Runs the program corresponding to the name of the active program being executed

        Args:
            socket_index any: The index of the socket to output to
        """        
        if self.program_is_running:
            program = self._program_database.get_program(self.active_program_name)
            try:
                for command in program:
                    self._do_command(command)
            except:
                print_exception(self.program_socket_index)
            self.program_is_running = False

    def toggle_auto_run(self):
        self._will_immediately_run_commands = not self._will_immediately_run_commands
        socket_print(-1, self._will_immediately_run_commands, all=True, type="toggle_auto_run")

    def _start_video_loop(self) -> None:
        """
        Creates a thread to start the main video loop
        """        
        self._show_video_feed = True

        start_thread(self._video_loop)

    def _video_loop(self) -> None:
        """
        Houses and runs the main video feed loop
        """        
        self.image_stitcher = stitch_images.Stitcher()
        start_thread(self.image_stitcher.start_glfw_loop)
        while self._show_video_feed:
            self._get_images()
            self.update_robot_state()
            
    def get_robot_state(self) -> object:
        """
        Returns the state of Spot (Boston Dyanmics RobotState object)

        Returns:
            object: The object containing Spot state
        """        
        if self._robot_control is not None:
            return self._robot_control.get_robot_state()
    
    def update_robot_state(self) -> None:
        """
        Updates clients with the most recent robot state information
        """        
        state = self.get_robot_state()
        if state == None:
            return
        power_state = state.power_state
        battery_percentage = power_state.locomotion_charge_percentage.value
        battery_runtime = power_state.locomotion_estimated_runtime.seconds
        socket_print(-1, battery_percentage, all=True, type="battery_percentage")
        socket_print(-1, battery_runtime, all=True, type="battery_runtime")

    def _stitch_images(self, image1: bosdyn.client.image, image2: bosdyn.client.image) -> Image:
        """
        Sttiches the right and left from camera images

        Args:
            image1 (bosdyn.client.image): The right camera image
            image2 (bosdyn.client.image): The left camera image

        Returns:
            Image: The stitched image
        """        
        try:
            return self.image_stitcher.stitch(image1, image2)
        except bosdyn.client.frame_helpers.ValidateFrameTreeError:
            socket_print(-1, "<red><bold>Issue with cameras, robot must be rebooted</bold></red>", all=True)

    def _encode_base64(self, image: Image) -> str:
        """
        Encodes an image in base64

        Args:
            image (Image): The image

        Returns:
            str: The image bytes encoded in base64
        """        
        if image is None:
            return
        buf = io.BytesIO()
        image.save(buf, format='JPEG')

        bytes_image = buf.getvalue()

        return base64.b64encode(bytes_image).decode("utf8")

    def _get_images(self) -> None:
        """
        Gets and displays all relevant images for the video feed
        """        
        try:
            self._get_image("front")
            self._get_image("back")
        except Exception as e:
            socket_print(-1, e, all=True)

    def _stitched_or_stamped(self, image: Image, front_right, front_left) -> str:
        if image is not None:
            return self._encode_base64(image)
        front_right =front_right.shot.image.data
        front_left = front_left.shot.image.data

        img_file = BytesIO(front_right)
        front_right = Image.open(img_file)
        front_right = front_right.rotate(-90)

        img_file = BytesIO(front_left)
        front_left = Image.open(img_file)
        front_left = front_left.rotate(-90)

        full_image = Image.new("RGB", (1280, 480), "white")
        full_image.paste(front_left, (640, 0))
        full_image.paste(front_right, (0, 0))

        return self._encode_base64(full_image)


    def _get_image(self, camera_name: str) -> None:
        """
        Gets and updates the client with an image

        Args:
            camera_name (str): The name of the desired image
        """        
        if camera_name == "front":
            front_right = self._image_client.get_image_from_sources(
                ["frontright_fisheye_image"])[0]
            front_left = self._image_client.get_image_from_sources(
                ["frontleft_fisheye_image"])[0]
            image = self._stitch_images(front_right, front_left)
            image = self._stitched_or_stamped(image, front_right, front_left)
        if camera_name == "back":
            back = self._image_client.get_image_from_sources(
                ["back_fisheye_image"])[0].shot.image.data
            image = base64.b64encode(back).decode("utf8")
            
        if camera_name == "left":
            left = self._image_client.get_image_from_sources(["left_fisheye_image"])[0].shot.image.data
            image = base64.b64encode(left).decode("utf8")

        socket_print(-1,image,
                    all=True, type=("@" + camera_name))

    def _do_command(self, command: object) -> None:
        """
        Executes a command from the queue

        Args:
            command (object): The command
        """        
        action = command['Command']

        if action == 'stand':
            self._robot_control.stand()

        if action == 'sit':
            self._robot_control.sit()

        if action == 'wait':
            time.sleep(command['Args']['time'])

        if action == 'rotate_by':
            args = command['Args']
            mult = self._robot_control.KEYBOARD_ROTATION_VELOCITY

            pitch = float(args['pitch'])
            yaw = float(args['yaw'])
            roll = float(args['roll'])

            self._robot_control.keyboard_rotate(math.radians(yaw) / mult, math.radians(roll) / mult, math.radians(pitch) / mult)

        if action == 'rotate':
            args = command['Args']
            pitch = float(args['pitch'])
            yaw = float(args['yaw'])
            roll = float(args['roll'])

            self._robot_control.rotate(math.radians(
                yaw), math.radians(roll), math.radians(pitch))

        if action == 'set_height':
            args = command['Args']
            height = float(args['height'])

            self._robot_control.set_height(height)

        if action == 'move':
            MAX_SPEED = 0.5
            args = command['Args']
            x = float(args['x'])
            y = float(args['y'])
            z = float(args['z'])

            l = math.sqrt(x * x + y * y)

            if (l < 1):
                self._robot_control.walk(x, y, math.radians(z), t=1)
            else:
                x /= l
                y /= l
                z /= l

                self._robot_control.walk(x, y, math.radians(z), t=l)

    def key_up(self, key: str) -> bool:
        """
        Returns whether a keyup event happened for a specific key in the last frame

        Args:
            key (str): The string representation of the key

        Returns:
            bool: Whether a keyup event occurred
        """        
        return key in self._keys_up

    def key_down(self, key: str) -> bool:
        """
        Returns whether a keydown event happened for a specific key in the last frame
        

        Args:
            key (str): The string representation of the key

        Returns:
            bool: Whether a keydown event occured
        """        
        return key in self._keys_down

    def _set_keys(self, keys_changed: list) -> None:
        """
        Sets object attributes to the most recent keyboard events to be used in other methods

        Args:
            keys_changed (list): the list containing both keyup and keydown events
        """        
        self._keys_down = keys_changed[0]
        self._keys_up = keys_changed[1]

    def _do_keyboard_commands(self) -> None:
        """
        Executes a command based on which keys were pressed in the last frame
        """        
        if self.key_up('space'):
            self.keyboard_control_mode = "Walk" if self.keyboard_control_mode == "Stand" else "Stand"
            self._robot_control.stand()
            return 
            self._robot_control.rotation = {"pitch": 0, "yaw": 0, "roll": 0}

        if self.key_down('x'):
            self._robot_control.roll_over()
            return 

        if self.key_down('z'):
            self._robot_control.self_right()
            return 

        if self.key_down('r'):
            self._robot_control.rotation = {"pitch": 0, "yaw": 0, "roll": 0}
            self._robot_control.stand()
            return 

        if self.key_down('f'):
            self._robot_control.sit()
            return 

        # Takes advantage of fact that True == 1 and False == 0.
        # True - True = 0; True - False = 1; False - True = 0
        dx = self.key_down('w') - self.key_down('s')
        dy = self.key_down('a') - self.key_down('d')
        dz = self.key_down('q') - self.key_down('e')

        if self.keyboard_control_mode == "Walk":
            self._robot_control.keyboard_walk(dx, dy * 0.5, dz)
        elif self.keyboard_control_mode == "Stand":
            self._robot_control.keyboard_rotate(dy, -dz, dx)

    def keyboard(self, keys_changed: list) -> None:
        """
        Updates the keys changed, runs keyboard commands, and updates client with the control mode (Walk or Stand)

        Args:
            keys_changed (list): The list of keyboard events in the last frame
        """        
        self._set_keys(keys_changed)

        if self.program_is_running or self.is_running_commands or not self._robot_control or not self.robot.is_powered_on():
            return

        self._do_keyboard_commands()
        socket_print(-1, self.keyboard_control_mode,
                     all=True, type="control_mode")

    def start_bg_process(self, socket_index: any) -> None:
        """
        Creates a thread so the background process can be run in the background

        Args:
            socket_index any: The index of the socket to output to
        """ 
        start_thread(self.start, args=(socket_index, ))

    def end_bg_process(self) -> None:
        """
        Updates the server with information to shut down
        """        
        self.is_running = False
        self._show_video_feed = False

    def get_programs(self) -> list:
        """
        Returns a list of all programs in the database

        Returns:
            list: The list of programs
        """        
        programs = self._program_database.get_all_programs()
        programs = {p[0]: json.loads(p[1]) for p in programs}
        
        return programs

    def add_program(self, name: str, program: list) -> None:
        """
        Adds a program to the database

        Args:
            name (str): The name of the program
            program (list): The program content
        """        
        self._program_database.write_program(name, json.dumps(program))
        socket_print(-1, self.get_programs(), all=True, type="programs")
        
    def remove_program(self, name: str) -> None:
        """
        Removes a program from the database

        Args:
            name (str): The name of the program
        """        
        self._program_database.delete_program(name)
        socket_print(-1, self.get_programs(), all=True, type="programs")

    def set_program_to_run(self, name: str) -> None:
        """
        Sets a program to run

        Args:
            name (str): The name of the program
        """        
        if not self._program_database._name_exists(name):
            return

        self.program_is_running = True
        self.active_program_name = name

    def get_state_of_everything(self) -> dict:
        """
        Returns a nested dictionary of the state of all attributes of the main background process class

        Returns:
            dict: The dictionary with the state of everything
        """        
        return get_members(self)
    
    def get_keyboard_control_state(self) -> dict:
        """
        Returns information about the keyboard control state

        Returns:
            dict: The information
        """        
        return {
            'is_handling_keyboard_commands': self.is_handling_keyboard_commands,
            'keyboard_control_name': self.keyboard_control_mode,
            'keys_up': self._keys_up,
            'keys_down': self._keys_down,
        }
        
    def get_internal_state(self) -> dict:
        """
        Returns information about the internal state of the server

        Returns:
            dict: The information
        """        
        return {
            'robot_is_connected': self._has_time_sync,
            'server_has_estop': self._has_estop,
            'server_has_lease': self._has_lease,
            'background_is_running': self.is_running,
            'is_connecting_service': self._is_connecting,
            'is_running_commands': self.is_running_commands,
            'active_program_name': self.active_program_name,
            'program_socket_index': self.program_socket_index,
            'command_queue': self.command_queue,
            'is_accepting_commands': self._is_accepting_commands,
            'will_auto_run_commands': self._will_immediately_run_commands,
            'should_run_commands': self._should_run_commands,
            'command_queue': self.command_queue
        }
        
    def get_server_state(self) -> dict:
        """
        Returns the internal state and the keyboard control state

        Returns:
            dict: The information
        """        
        state = self.get_internal_state()
        state.update(self.get_keyboard_control_state())
        return state


# Creates an instance of the background_process class used for interacting with the background process connected to Spot
bg_process = Background_Process()

def do_action(action: str, socket_index: any, args: any = None) -> any:
    """
    Handles actions from the client


    Args:
        action (str): The name of the action
        socket_index any: The index of the socket to display to
        args (any, optional): Any arguments. Defaults to None.

    Returns:
        any: Requested information
    """    
    if action == "start":
        # Makes sure that the background process is not already running before it starts it
        if bg_process.is_running:
            socket_print(socket_index,
                         "Cannot start background process because background process is already running")
            return

        if bg_process._is_connecting:
            socket_print(socket_index, "Robot is already connecting!")
            return

        bg_process.start_bg_process(socket_index)

    elif action == "end":
        # Makes sure that the background process is running before it ends it
        if not bg_process.is_running:
            socket_print(socket_index,
                         "Cannot end main loop because main loop is not running")
            return

        bg_process.end_bg_process()
        socket_print(socket_index, "Main loop ended")

    elif action == "toggle_accept_command":
        bg_process._is_accepting_commands = not bg_process._is_accepting_commands
            
        
        socket_print(-1, bg_process._is_accepting_commands, type="toggle_accept_command", all=True)
            
    elif action == "run_program":
        # Makes sure that the background process is running (robot is connected) before it tries to run a program
        bg_process.active_program_name = args
        
        if not bg_process.is_running:
            socket_print(socket_index,
                         "Cannot run program because background process is not running")
            return
        # Makes sure that a program is not already running before it runs one
        if bg_process.program_is_running:
            socket_print(socket_index,
                         "Cannot run program because a program is already running")
            return
        
        bg_process.program_socket_index = socket_index
        bg_process.set_program_to_run(args)
        socket_print(socket_index, "Running Program")

    elif action == "remove_program":
        bg_process.remove_program(args)

    elif action == "estop":
        bg_process.estop()

    elif action == "estop_release":

        bg_process.release_estop()

    elif action == "connect":
        if bg_process._is_connecting:
            socket_print(socket_index, "Robot is already connecting!")
            return
        start_thread(bg_process._connect_to_robot, args=(socket_index))

    elif action == "disconnect_robot":
        bg_process._disconnect_from_robot()
        
    elif action == "clear_estop":
        bg_process._clear_estop()
        
    elif action == "clear_lease":
        bg_process._clear_lease()

    elif action == "acquire_estop":
        if bg_process._is_connecting:
            socket_print(socket_index, "Robot is already connecting!")
            return
        if not bg_process.robot:
            socket_print(
                socket_index, "Cannot acquire Estop because robot is not connected!")
            return
        start_thread(bg_process._acquire_estop, args=(socket_index))

    elif action == "acquire_lease":
        if bg_process._is_connecting:
            socket_print(socket_index, "Robot is already connecting!")
            return
        if not bg_process.robot:
            socket_print(
                socket_index, "Cannot acquire lease because robot is not connected!")
            return
        if not bg_process._estop_client:
            socket_print(
                socket_index, "Cannot acquire lease because Estop has not been acquired!")
            return
        start_thread(bg_process._acquire_lease, args=(socket_index))

    elif action == "check_if_running":
        return bg_process.is_running

    elif action == "toggle_auto_run":
        bg_process.toggle_auto_run()

    elif action == "step_command":
        if not bg_process.is_running:
            socket_print(socket_index, "Background process is not running!")
            return
        if bg_process._will_immediately_run_commands or bg_process.is_running_commands:
            socket_print(socket_index, "Already running commands!")
            return
        bg_process._should_run_commands = True


    else:
        socket_print(socket_index, f"Command not recognized: {action}")
