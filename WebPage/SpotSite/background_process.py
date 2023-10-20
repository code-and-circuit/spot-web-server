# General system imports
import time
import math
import json

# Interproject imports
from SpotSite import spot_control
from SpotSite import secrets
from SpotSite.spot_logging import log
from SpotSite.utils import output_to_socket, print_exception, start_thread, read_json
from SpotSite.sql_stuff import SqliteConnection
from SpotSite.spot_images.image_handler import Image_Handler
from SpotSite.scratch_handling import scratch_handler

# Boston Dynamics imports
import bosdyn.client
import bosdyn.client.lease
from bosdyn.client.robot_command import RobotCommandClient
from bosdyn.client.estop import EstopEndpoint
from bosdyn.client.estop import EstopKeepAlive
from bosdyn.client.estop import EstopClient
from bosdyn.client.image import ImageClient
from bosdyn.choreography.client.choreography import ChoreographyClient


def close():
    bg_process.is_running = False
    while bg_process._is_shutting_down:
        pass
    print("\033[92m" + "    Background" +
          "\033[0m" + ": Disconnecting from robot")


class Background_Process:

    def __init__(self):
        log("Initializing background process")
        # Boilerplate
        self._sdk = None
        self.robot = None
        self._robot_control = None

        # Clients
        self._command_client = None
        self._lease_client = None
        self._image_client = None
        self._estop_client = None

        # Robot control
        self._lease = None
        self._lease_keep_alive = None
        self._estop_keep_alive = None

        # Server state
        self.is_running = False
        self._is_connecting = False
        self.program_is_running = False
        self.is_running_commands = False
        self.is_handling_keyboard_commands = False
        self.robot_is_estopped = False
        self.image_handler = Image_Handler(
            self.update_robot_state, self._image_client)
        self._is_shutting_down = False

        self._has_lease = False
        self._has_estop = False

        self.keyboard_control_mode = "Walk"
        self.active_program_name = ""
        self.program_socket_index = ""

        self._is_accepting_commands = False
        self._will_immediately_run_commands = False
        self._should_run_commands = False
        self.command_queue = []
        self._keys_up = []
        self._keys_down = []

        self._program_database = SqliteConnection()

        self.default_data = self._load_defaults()

    def _load_defaults(self, filepath="./SpotSite/config.json") -> dict:
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
        log(f"Loaded default data: {data}")
        return data

    # TODO: variable for if the robot is in the process of powering on

    def turn_on(self, socket_index: any) -> bool:
        """
        Attempts to turn on Spot

        Args:
            socket_index any: The index of the socket to display information to

        Returns:
            bool: Whether the action was successful
        """
        output_to_socket(socket_index, "Powering On...")
        try:
            self.robot.power_on(timeout_sec=20)
        except bosdyn.client.power.OverriddenError:
            output_to_socket(socket_index, "Command overidden? Trying again.")
            try:
                self.robot.power_on(timeout_sec=20)
            except Exception as e:
                print_exception(socket_index)
        except Exception as e:
            print_exception(socket_index)
        # Checks to make sure that Spot successfully powered on
        robot_is_powered_on = False
        try:
            robot_is_powered_on = self.robot.is_powered_on()
        except:
            pass
        if not robot_is_powered_on:
            output_to_socket(socket_index, "<red>Robot Power On Failed</red>")
            log("Failed to turn on robot")
            return False
        else:
            output_to_socket(socket_index, "Powered On")
            log("Turned on robot")
            return True

    def turn_off(self, socket_index: any) -> bool:
        """
        Attempts to turn off Spot

        Args:
            socket_index any: The index of the socket to display information to

        Returns:
            bool: Whether the action was successful
        """
        output_to_socket(socket_index, "Powering off...")
        try:
            self.robot.power_off(cut_immediately=False, timeout_sec=20)
        except bosdyn.client.robot_command.NoTimeSyncError:
            print("No time sync!")
        except:
            print_exception(socket_index)
        is_powered_on = False
        try:
            is_powered_on = self.robot.is_powered_on()
        except AttributeError:
            pass
        # Checks to make sure that Spot successfully powered off
        if is_powered_on:
            output_to_socket(socket_index, "<red>Robot power off failed</red>")
            log("Failed to turn off robot")
            return False
        else:
            output_to_socket(socket_index, "Powered Off")
            log("Turned off robot")
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
            output_to_socket(socket_index, "Lease already acquired")
            return True

        success = True
        self._is_connecting = True

        try:
            if self.robot.is_estopped():
                raise Exception("Robot is estopped. Cannot Acquire Lease.")

            output_to_socket(socket_index, "Acquiring Lease...")
            self._lease_client = self.robot.ensure_client(
                bosdyn.client.lease.LeaseClient.default_service_name)
            self._lease = self._lease_client.take()
            self._lease_keep_alive = bosdyn.client.lease.LeaseKeepAlive(
                self._lease_client)

            self._has_lease = True
            output_to_socket(socket_index, "<green>Acquired Lease</green>")
            output_to_socket(-1, "acquire", all=True, type="lease_toggle")

        except Exception as e:
            print_exception(socket_index)
            output_to_socket(
                socket_index, "<red>Failed to accquire lease</red>")
            success = False
            self._clear_lease()

        finally:
            self._is_connecting = False

        log(f"Attempted to acquire lease. Result: {success} ")

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
            output_to_socket(socket_index, "Estop already acquired")
            return True

        success = True
        self._is_connecting = True

        try:
            output_to_socket(socket_index, "Acquiring Estop...")

            self._estop_client = self.robot.ensure_client(
                EstopClient.default_service_name)
            ep = EstopEndpoint(self._estop_client,
                               name="cc-estop", estop_timeout=20)
            ep.force_simple_setup()
            self._estop_keep_alive = EstopKeepAlive(ep)
            self.robot_is_estopped = False

            self._has_estop = True

            if (self._has_estop):
                output_to_socket(socket_index, "<green>Acquired Estop</green>")
                output_to_socket(-1, "acquire", all=True, type="estop_toggle")
            else:
                raise Exception("No Estop!!")

        except:
            print_exception(socket_index)
            output_to_socket(
                socket_index, "<red>Failed to accquire Estop</red>")
            success = False
            self._clear_estop()

        finally:
            self._is_connecting = False

        log(f"Attempted to acquire estop. Result: {success} ")
        return success

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
            output_to_socket(socket_index, "Robot is already connected")
            return True

        output_to_socket(socket_index, "Connecting to robot...")

        success = True
        self._is_connecting = True

        try:
            self._sdk = bosdyn.client.create_standard_sdk('cc-server')
            self._sdk.register_service_client(ChoreographyClient)

            self.robot = self._sdk.create_robot(secrets.ROBOT_IP)
            self.robot.authenticate(
                secrets.ROBOT_USERNAME, secrets.ROBOT_PASSWORD)

            self._image_client = self.robot.ensure_client(
                ImageClient.default_service_name)

            self._command_client = self.robot.ensure_client(
                RobotCommandClient.default_service_name)
            self._robot_control = spot_control.Spot_Control(
                self._command_client, socket_index, self.robot)

            self.image_handler._start_video_loop(
                self.update_robot_state, self._image_client)

            output_to_socket(-1, "acquire", all=True, type="robot_toggle")
            output_to_socket(socket_index, "<green>Connected to robot</green>")

        except:
            print_exception(socket_index)
            output_to_socket(
                socket_index, "<red>Failed to connect to Spot</red>")
            success = False
            self._disconnect_from_robot()

        finally:
            self._is_connecting = False

        log(f"Attempted to connect to robot. Result: {success} ")
        return success

    def _connect_all(self, socket_index: any) -> bool:
        """
        Attempts to connect to Spot, acquire an estop, and acquire a lease

        Args:
            socket_index any: The socket of the index to output to

        Returns:
            bool: Whether all actions were successful
        """
        output_to_socket(socket_index, "Starting...")

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
            output_to_socket(-1, "Estop Not Acquired", all=True)
            return
        if self._estop_keep_alive and not self.robot.is_estopped():
            output_to_socket(0, "estop", all=True, type="estop")
            self.robot_is_estopped = True
            self._estop_keep_alive.settle_then_cut()
            self._is_accepting_commands = False
            # Clear command queue so Spot does not execute commands the instant
            # the estop is released
            self.command_queue = []
            log("Estopped robot")

    def release_estop(self) -> None:
        """
        Releases any active Estop on Spot
        """
        if not self._has_estop:
            return
        if self._estop_keep_alive and self.robot.is_estopped():
            output_to_socket(0, "estop_release", all=True, type="estop")
            self.robot_is_estopped = False
            self._estop_keep_alive.allow()
            log("Released robot estop")

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
        self.image_handler.set_show_video_feed(False)
        self._clear_lease()
        self._clear_estop()
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

        log("Disconnected and cleared lease")
        output_to_socket(-1, "clear", all=True, type="lease_toggle")

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

        log("Disconnected and cleared estop")
        output_to_socket(-1, "clear", all=True, type="estop_toggle")

    def _disconnect_from_robot(self) -> None:
        """
        Disconnects from Spot
        """
        if self._has_lease or self._has_estop:
            self._clear_estop()

        self.image_handler.set_show_video_feed(False)
        self._image_client = None

        self._robot_control = None
        self._command_client = None
        self.robot = None
        self._sdk = None

        output_to_socket(-1, "clear", all=True, type="robot_toggle")
        log("Disconnected from robot")

    def start(self, socket_index: any) -> None:
        """
        Attempts to start the main background process, including connecting all services

        Args:
            socket_index any: The index of the socket to output to
        """
        output_to_socket(socket_index, 'Connecting...')

        if not self._connect_all(socket_index):
            output_to_socket(
                socket_index, "<red>Failed to start processes</red>")
            return

        output_to_socket(socket_index, "<green>Connected</green>")
        output_to_socket(socket_index, "start", all=True, type="bg_process")
        self.update_robot_state()
        self._background_loop(socket_index)
        log("Clearing after background loop ended")
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
            log("Started background loop")
            while self.is_running:
                self._keep_robot_on(socket_index)
                self._run_programs(socket_index)
                self._execute_commands(socket_index)

        except:
            print_exception(socket_index)
            log("Background loop ended due to exception")

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
                    output_to_socket(socket_index, "Command List is empty!")
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
                    output_to_socket(socket_index, "Command List is empty!")
                self._update_command_queue()
        self.is_running_commands = False
        self._should_run_commands = False

    def _update_command_queue(self):
        output_to_socket(-1, json.dumps(self.command_queue),
                         all=True, type="command_queue")

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
            program = self._program_database.get_program(
                self.active_program_name)
            log(f"Running program: {self.active_program_name}")
            try:
                for command in program:
                    self._do_command(command)
            except:
                print_exception(self.program_socket_index)
            self.program_is_running = False

    def toggle_auto_run(self):
        self._will_immediately_run_commands = not self._will_immediately_run_commands
        output_to_socket(-1, self._will_immediately_run_commands,
                         all=True, type="toggle_auto_run")

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
        output_to_socket(-1, battery_percentage, all=True,
                         type="battery_percentage")
        output_to_socket(-1, battery_runtime, all=True, type="battery_runtime")

    def _do_command(self, command: object) -> None:
        """
        Executes a command from the queue

        Args:
            command (object): The command
        """
        log(f"Running command: {command}")
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

            self._robot_control.keyboard_rotate(math.radians(
                yaw) / mult, math.radians(roll) / mult, math.radians(pitch) / mult)

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
            
            self._robot_control.move(x, y, z)

        if action == 'set_locomotion_hint':
            self._robot_control.set_locomotion_hint(command['Args']['hint'])
        
        if action == 'bow':
            self._robot_control.do_dance_sequence("bow.csq")

        if action == 'twerk':
            self._robot_control.do_dance_sequence("twerk.csq")

        if action == 'butt_circle':
            self._robot_control.do_dance_sequence("butt_circle.csq")
        if action == 'breathe':
            self._robot_control.do_dance_sequence("breathe.csq")

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

        elif self.key_down('x'):
            self._robot_control.roll_over()

        elif self.key_down('z'):
            self._robot_control.self_right()

        elif self.key_down('r'):
            self._robot_control.rotation = {"pitch": 0, "yaw": 0, "roll": 0}
            self._robot_control.stand()

        elif self.key_down('f'):
            self._robot_control.sit()

        else:
            # Takes advantage of fact that True == 1 and False == 0.
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
        output_to_socket(-1, self.keyboard_control_mode,
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
        self.image_handler.set_show_video_feed(False)
        log("Ending background process")

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
        output_to_socket(-1, self.get_programs(), all=True, type="programs")

    def remove_program(self, name: str) -> None:
        """
        Removes a program from the database

        Args:
            name (str): The name of the program
        """
        self._program_database.delete_program(name)
        output_to_socket(-1, self.get_programs(), all=True, type="programs")

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
            'robot_is_connected': self._has_estop,
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
            'command_queue': self.command_queue,
            'scratch_clients': scratch_handler.get_client_list(),
            'scratch_controller': (scratch_handler.get_allowed_client_name(), scratch_handler.allowed_ip)
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
