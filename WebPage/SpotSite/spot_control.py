"""
    Handles sending motor commands to Spot
    
    Classes:
    
        Spot_Control
        
    Methods:
    
        clamp(num, min_num, max_num) -> (float, int)
        dispatch(func) -> callable
        
            
"""
import time
import math
from SpotSite import websocket
from SpotSite import spot_logging as l
from pprint import pprint

from bosdyn.api import robot_command_pb2, mobility_command_pb2
from bosdyn.api.spot import robot_command_pb2 as spot_command_pb2
import bosdyn.client.util
import bosdyn.geometry
from bosdyn.client.robot_command import RobotCommandBuilder, blocking_stand
from bosdyn.client.robot_state import RobotStateClient


def clamp(num: (float, int), min_num: (float, int), max_num: (float, int)) -> (float, int):
    """
    Clamps a number between 2 values

    Args:
        num (float, int): The number to be clamped
        min_num (float, int): The maximum number
        max_num (float, int): The minimum number

    Returns:
        _type_: The clamped number
    """    
    return max(min_num, min(num, max_num))

def dispatch(func: callable):
    """
    Dispatches a function and handles callable BehaviorFaultErrors

    Args:
        func (callable): The function
    """    
    def dispatch_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except bosdyn.client.robot_command.BehaviorFaultError:
            websocket.websocket_list.print(-1, f"<red>Robot has uncleared behavior faults!</red>:{func.__name__}", all=True)
        except Exception as e:
            websocket.socket_list.print(-1, f"<red>ERROR</red>: {e}", all=True)
            
    return dispatch_wrapper


class Spot_Control:
    """
    A class to handle sending motor commands to spot
    
    Attributes:
        command_client (bosdyn.client.robot_command.RobotCommandClient): The Boston Dynamics command client object
        socket_index (str): The index of the socket to output to
        robot (bosdyn.client.robot.Sobot)
        
        KEYBOARD_COMMAND_DURATION (float): The duration of keyboard commands
        KEYBOARD_COMMAND_VELOCITY (float): The velocity that keyboard commands are sent with
        KEYBOARD_TURN_VELOCITY (float): The velocity that the robot turns at, from keyboard commands
        KEYBOARD_ROTATION_VELOCITY (float): The velocity that the robot rotates at, from keyboard commands
        
        ROLL_OFFSET_MAX (float): The maximum roll angle
        YAW_OFFSET_MAX (float): The maximum yaw angle
        PITCH_OFFSET_MAX (float): The maximum pitch angle
        rotation (dict): The current pitch, yaw, and roll of the robot
        collision_avoid_params (spot_command_pb2.ObstacleParams): The obstable avoidance parameters
        _is_rolled_over (bool): Whether the robot has recently rolled over
        is_running_command (bool): Whether a command is currently being executed
        robot_state_client (bosdyn.client.robot_state.RobotStateClient): The Boston Dynamics robot state client
        
    Methods:
        print(message, all, type):
            Outputs information to a websocket
        get_robot_state():
            Returns the robot state
        rotate(raw, roll, pitch):
            Rotates the robot
        stand():
            Stands the robot
        sit()
            Sits the robot
        self_right():
            Self-rights the robot
        roll_over()
            Rolls the robot over (to take out battery)
        _send_walk_command(x, y, z, t):
            Sends a walk command
        walk(x, y, z, t, d):
            Splits up and dispatches walk commands
        set_stand_height(height):
            Sets the stand height of the robot
        keyboard_walk(dx, dy, dz):
            Sends a walk command from keyboard control
        keyboard_rotate(dyaw, droll, dpitch):
            Rotates the robot from keyboard control
        setup():
            Stands and resets the robot's ortientation
    """
    def __init__(self, cmd_client: bosdyn.client.robot_command.RobotCommandClient, s: (int, str), robot: bosdyn.client.robot):
        self.command_client = cmd_client
        self.socket_index = s
        self.robot = robot

        self.KEYBOARD_COMMAND_DURATION = 0.5
        self.KEYBOARD_COMMAND_VELOCITY = 0.5
        self.KEYBOARD_TURN_VELOCITY = 0.5
        self.KEYBOARD_ROTATION_VELOCITY = 0.2

        # Constants taken from 'xbox_controller.py' python example in spot-sdk
        self.ROLL_OFFSET_MAX = 0.4
        self.YAW_OFFSET_MAX = 0.7805
        self.PITCH_OFFSET_MAX = 0.7805
        self.rotation = {"pitch": 0, "yaw": 0, "roll": 0}

        self.collision_avoid_params = spot_command_pb2.ObstacleParams(
            obstacle_avoidance_padding=1, disable_vision_foot_obstacle_avoidance=False,
            disable_vision_foot_constraint_avoidance=False, disable_vision_body_obstacle_avoidance=False,
            disable_vision_foot_obstacle_body_assist=True, disable_vision_negative_obstacles=False
        )

        self._is_rolled_over = False
        self.is_running_command = False

        self.robot_state_client = robot.ensure_client(
            RobotStateClient.default_service_name)

    def print(self, message: str, all=False, type="output"):
        """
        Outputs information to a websocket

        Args:
            message (str): The message
            all (bool, optional): Whether all sockets should receive the information. Defaults to False.
            type (str, optional): The type of information. Defaults to "output".
        """        
        websocket.websocket_list.print(-1, message, all=True, type=type)
        
    def get_robot_state(self) -> object:
        """
        Returns the robot state

        Returns:
            object: The RobotState object
        """        
        return self.robot_state_client.get_robot_state()

    @dispatch
    def rotate(self, yaw: float, roll: float, pitch: float) -> None:
        """
        Rotates the robot

        Args:
            yaw (float): Desired yaw angle
            roll (float): Desired roll angle
            pitch (float): Desired pitch angle
        """        
        # Create rotation command
        rotation = bosdyn.geometry.EulerZXY(yaw=yaw, roll=roll, pitch=pitch)
        cmd = RobotCommandBuilder.synchro_stand_command(
            footprint_R_body=rotation)
        self.command_client.robot_command(cmd)
        # I know the line is long. I'm lazy.
        self.print(f'Rotated to yaw: {round(yaw, 2)}({round(math.degrees(yaw), 2)}°), roll: {round(roll, 2)}({round(math.degrees(roll), 2)}°), pitch: {round(pitch, 2)}({round(math.degrees(pitch), 2)}°)')

    @dispatch
    def stand(self) -> None:
        """
        Stands the robot
        """        
        cmd = RobotCommandBuilder.synchro_stand_command()
        self.command_client.robot_command(cmd)

    def sit(self) -> None:
        """
        Sits the robot
        """        
        cmd = RobotCommandBuilder.synchro_sit_command()
        self.command_client.robot_command(cmd)

    @dispatch
    def self_right(self) -> None:
        """
        Self-rights the robot
        """        
        self.sit()
        time.sleep(1)
        cmd = RobotCommandBuilder.selfright_command()
        self.command_client.robot_command(cmd)

    @dispatch
    def roll_over(self) -> None:
        """
        Rolls the robot over (to take out battery)
        """        
        # Direction(?) d = basic_command_pb2.BatteryChangePoseCommand.Request.HINT_RIGHT
        cmd = RobotCommandBuilder.battery_change_pose_command()
        self.command_client.robot_command(cmd)
        self._is_rolled_over = True
        
    def _send_walk_command(self, x: float, y: float, z: float, t: float = 1) -> None:
        """
        Sends a walk command

        Args:
            x (float): The x-speed
            y (float): The y-speed
            z (float): The turn speed
            t (float, optional): The duration of the command. Defaults to 1.
        """        
        walk = RobotCommandBuilder.synchro_velocity_command(x, y, z)
        walk.synchronized_command.mobility_command.params.CopyFrom(
            RobotCommandBuilder._to_any(self.collision_avoid_params))
        self.command_client.robot_command(walk, end_time_secs=time.time() + t)
        self.print(f'Walking at ({x}, {y}, {z})m/s for {t}s')
        # Don't allow callable commands until robot is done walking
        time.sleep(t)
        
    @dispatch
    def walk(self, x: float, y: float, z: float, t: float = 0, d: float = 0) -> None:
        """
        Splits up and dispatches walk commands

        Args:
            x (float): The x-speed
            y (float): The y-speed
            z (float): The turn speed
            t (float, optional): The duration of the command. Defaults to 0.
            d (float, optional): The total distance the command should run. Defaults to 0.
        """        

        # Set the time based off of the desired distance (NOT WORKING PROPERLY - probably need to do vector math)
        if t == 0:
            distance = math.sqrt(x ** 2 + y ** 2 + z ** 2)
            t = d/distance

        # Splits commands up if specified turn value is too high. Works, but can probably be improved
        if abs(z) >= 1.5:
            num_steps = int(abs(z) / 1.5)
            leftover_x = x % num_steps
            leftover_y = y % num_steps
            leftover_z = 1.5 - z % 1.5
            print(leftover_z)
            for _ in range(num_steps):
                self._send_walk_command(x/num_steps, y/num_steps, 1.5 if z > 0 else -1.5)
            self._send_walk_command(leftover_x, leftover_y, leftover_z if z > 0 else -leftover_z)
        else:
            self._send_walk_command(x, y, z, t = t)
        

    @dispatch
    def set_stand_height(self, height: float) -> None:
        """
        Sets the stand height of the robot

        Args:
            height (float): The height
        """        
        # Create stand height command
        cmd = RobotCommandBuilder.synchro_stand_command(body_height=height)
        self.command_client.robot_command(cmd)
        self.print(f'Standing at: {height}')

    @dispatch
    def keyboard_walk(self, dx: float, dy: float, dz: float) -> None:
        """
        Sends a walk command from keyboard control

        Args:
            dx (float): the change in x
            dy (float): the change in x
            dz (float): the change in body rotation
        """        
        walk = RobotCommandBuilder.synchro_velocity_command(
            dx * self.KEYBOARD_COMMAND_VELOCITY,
            dy * self.KEYBOARD_COMMAND_VELOCITY,
            dz * self.KEYBOARD_TURN_VELOCITY
        )
        walk.synchronized_command.mobility_command.params.CopyFrom(
            RobotCommandBuilder._to_any(self.collision_avoid_params))
        self.command_client.robot_command(
            walk, end_time_secs=time.time() + self.KEYBOARD_COMMAND_DURATION)

    @dispatch
    def keyboard_rotate(self, dyaw: float, droll: float, dpitch: float) -> None:
        """
        Rotates the robot from keyboard control

        Args:
            dyaw (float): The change in yaw angle
            droll (float): The change in roll angle
            dpitch (float): The change in pitch angle
        """        
        self.rotation['yaw'] += dyaw * self.KEYBOARD_ROTATION_VELOCITY
        self.rotation['yaw'] = clamp(
            self.rotation['yaw'], -self.YAW_OFFSET_MAX, self.YAW_OFFSET_MAX)

        self.rotation['roll'] += droll * self.KEYBOARD_ROTATION_VELOCITY
        self.rotation['roll'] = clamp(
            self.rotation['roll'], -self.ROLL_OFFSET_MAX, self.ROLL_OFFSET_MAX)

        self.rotation['pitch'] += dpitch * self.KEYBOARD_ROTATION_VELOCITY
        self.rotation['pitch'] = clamp(
            self.rotation['pitch'], -self.PITCH_OFFSET_MAX, self.PITCH_OFFSET_MAX)

        rotation = bosdyn.geometry.EulerZXY(
            yaw=self.rotation['yaw'],
            roll=self.rotation['roll'],
            pitch=self.rotation['pitch']
        )
        cmd = RobotCommandBuilder.synchro_stand_command(
            footprint_R_body=rotation)
        self.command_client.robot_command(cmd)

    @dispatch
    def setup(self) -> None:
        """
        Stands and resets the robot's ortientation
        """        
        self.stand()
        self.rotate(0, 0, 0)
        time.sleep(0.5)
