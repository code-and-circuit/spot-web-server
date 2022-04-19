import time, math
from SpotSite import websocket
import spot_logging as l
from pprint import pprint

from bosdyn.api import robot_command_pb2, mobility_command_pb2
from bosdyn.api.spot import robot_command_pb2 as spot_command_pb2
import bosdyn.client.util
import bosdyn.geometry
from bosdyn.client.robot_command import RobotCommandBuilder, blocking_stand
from bosdyn.client.robot_state import RobotStateClient


def clamp(num, min_num, max_num):
    return max(min_num, min(num, max_num))

def dispatch(func, robot_state_client):
        def dispatch_wrapper(*args, **kwargs):
            robot_state = robot_state_client.get_robot_state()
            
            pprint(vars(robot_state))
            
            if self._is_idle:
                return func(*args, **kwargs)
            print(f"Could not execute {func.__name__} because robot is not idle!")
            return False
        
        return dispatch_wrapper

# TODO: Make many commands part of a module so they don't need to be declared here. Would make creating 
# commands less messy. Maybe make the commands work the same as the Scratch commands do so they send a request
# to the server? This would allow for very clean code and a file would only need to import the module and have a single
# line of code for a command

class Spot_Control:
    def __init__(self, cmd_client, s, robot):
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
            obstacle_avoidance_padding = 1, disable_vision_foot_obstacle_avoidance = False, 
            disable_vision_foot_constraint_avoidance = False, disable_vision_body_obstacle_avoidance = False,
            disable_vision_foot_obstacle_body_assist = True, disable_vision_negative_obstacles = False
        )
        
        self._is_rolled_over = False
        self.is_running_command = False
        
        self.robot_state_client = robot.ensure_client(RobotStateClient.default_service_name)

    def print(self, message, all=False, type="output"):
        print(message)
        #websocket.websocket_list.print(self.socket_index, message, all=all, type=type)

    def rotate(self, yaw, roll, pitch):
        # Create rotation command
        rotation = bosdyn.geometry.EulerZXY(yaw=yaw, roll=roll, pitch=pitch)
        cmd = RobotCommandBuilder.synchro_stand_command(footprint_R_body=rotation)
        self.command_client.robot_command(cmd)
        self.print(f'Rotated to yaw: {yaw}, roll: {roll}, pitch: {pitch}')
        
    def stand(self):
        # Stand
        cmd = RobotCommandBuilder.synchro_stand_command()
        
        self.command_client.robot_command(cmd)
        self.print("Stood up")
    
    def sit(self):
        cmd = RobotCommandBuilder.synchro_sit_command()
        self.command_client.robot_command(cmd)
        self.print("Sitting Down")
    
    def self_right(self):
        self.sit()
        time.sleep(1)
        cmd = RobotCommandBuilder.selfright_command()
        self.command_client.robot_command(cmd)
        self.print("Self Righting")
        
    def roll_over(self):
        # Direction(?) d = basic_command_pb2.BatteryChangePoseCommand.Request.HINT_RIGHT
        cmd = RobotCommandBuilder.battery_change_pose_command()
        self.command_client.robot_command(cmd)
        self.print("Rolling OVer")
        self._is_rolled_over = True
    
    def walk(self, x, y, z, t=0, d=0):
        # TODO: Create multiple walk commands if desired walking time exceeds the time allowed by the robot
        # If the desired time is too high, the robot says that the command is too far in the future
        
        # Set the time based off of the desired distance (NOT WORKING PROPERLY - probably need to do vector math)
        if t == 0:
            distance = math.sqrt(x ** 2 + y ** 2 + z ** 2)
            t = d/distance
        
        # Create walk command
        walk = RobotCommandBuilder.synchro_velocity_command(x, y, z)
        walk.synchronized_command.mobility_command.params.CopyFrom(
                        RobotCommandBuilder._to_any(self.collision_avoid_params))    
        self.command_client.robot_command(walk, end_time_secs=time.time() + t)
        self.print(f'Walking at ({x}, {y}, {z})m/s for {t}s')
        # Don't allow any commands until robot is done walking
        time.sleep(t)
    
    def set_stand_height(self, height):
        # Create stand height command
        cmd = RobotCommandBuilder.synchro_stand_command(body_height=height)
        self.command_client.robot_command(cmd)
        self.print(f'Standing at: {height}')

    def keyboard_walk(self, d_x, d_y, d_z):
        walk = RobotCommandBuilder.synchro_velocity_command(
            d_x * self.KEYBOARD_COMMAND_VELOCITY,
            d_y * self.KEYBOARD_COMMAND_VELOCITY,
            d_z * self.KEYBOARD_TURN_VELOCITY
        )
        walk.synchronized_command.mobility_command.params.CopyFrom(
                        RobotCommandBuilder._to_any(self.collision_avoid_params))
        self.command_client.robot_command(walk, end_time_secs=time.time() + self.KEYBOARD_COMMAND_DURATION)

    def keyboard_rotate(self, d_yaw, d_roll, d_pitch):
        self.rotation['yaw'] += d_yaw * self.KEYBOARD_ROTATION_VELOCITY
        self.rotation['yaw'] = clamp(self.rotation['yaw'], -self.YAW_OFFSET_MAX, self.YAW_OFFSET_MAX)
        
        self.rotation['roll'] += d_roll * self.KEYBOARD_ROTATION_VELOCITY
        self.rotation['roll'] = clamp(self.rotation['roll'], -self.ROLL_OFFSET_MAX, self.ROLL_OFFSET_MAX)

        self.rotation['pitch'] += d_pitch * self.KEYBOARD_ROTATION_VELOCITY
        self.rotation['pitch'] = clamp(self.rotation['pitch'], -self.PITCH_OFFSET_MAX, self.PITCH_OFFSET_MAX)
        
        rotation = bosdyn.geometry.EulerZXY(
            yaw = self.rotation['yaw'],
            roll = self.rotation['roll'],
            pitch = self.rotation['pitch']
        )
        cmd = RobotCommandBuilder.synchro_stand_command(footprint_R_body=rotation)
        self.command_client.robot_command(cmd)

    def setup(self):
        self.stand()
        self.rotate(0, 0, 0)
        time.sleep(0.5)

    # Entry point to running a program
    def do_function(self):
        self.setup()