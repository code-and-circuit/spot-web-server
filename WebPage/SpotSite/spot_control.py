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
import os
from SpotSite import websocket
from SpotSite.spot_logging import log
from bosdyn.client import ResponseError

from bosdyn.api import robot_command_pb2, mobility_command_pb2
from bosdyn.api.spot import robot_command_pb2 as spot_command_pb2
import bosdyn.client.util
import bosdyn.geometry
from bosdyn.client.robot_command import RobotCommandBuilder, blocking_stand
from bosdyn.client.robot_state import RobotStateClient
from bosdyn.api.basic_command_pb2 import RobotCommandFeedbackStatus
from bosdyn.client import math_helpers
from bosdyn.client.frame_helpers import (BODY_FRAME_NAME, ODOM_FRAME_NAME, VISION_FRAME_NAME,
                                         get_se2_a_tform_b)
from bosdyn.api import geometry_pb2
from bosdyn.client.license import LicenseClient
from bosdyn.choreography.client.choreography import (ChoreographyClient,
                                                     load_choreography_sequence_from_txt_file)
from bosdyn.client.exceptions import UnauthenticatedError





def clamp(num: any, min_num: any, max_num: any) -> any:
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
            websocket.websocket_list.print(-1, f"<red>Robot is unable to run this command: {func.__name__}.</red> <b>Try sitting</b>.", all=True)
        except Exception as e:
            websocket.websocket_list.print(-1, f"<red>ERROR</red>: {e}", all=True)
            
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
    def __init__(self, cmd_client: bosdyn.client.robot_command.RobotCommandClient, s: any, robot: bosdyn.client.robot):
        log("Initialized Spot Control")
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
        
        self.HEIGHT_OFFSET_MIN = -2
        self.HEIGHT_OFFSET_MAX = 1
        self.height = 0

        self.collision_avoid_params = spot_command_pb2.ObstacleParams(
            obstacle_avoidance_padding=1, disable_vision_foot_obstacle_avoidance=True,
            disable_vision_foot_constraint_avoidance=True, disable_vision_body_obstacle_avoidance=True,
            disable_vision_foot_obstacle_body_assist=True, disable_vision_negative_obstacles=True
        )
        self.locomotion_hint = spot_command_pb2.HINT_AUTO

        self._is_rolled_over = False
        self.is_running_command = False

        self.robot_state_client = robot.ensure_client(
            RobotStateClient.default_service_name)
        
        self.choreography_client = None
        
        license_client = robot.ensure_client(LicenseClient.default_service_name)
        if not license_client.get_feature_enabled([ChoreographyClient.license_name
                                              ])[ChoreographyClient.license_name]:
            print("This robot is not licensed for choreography.")
        else:
            self.choreography_client = robot.ensure_client(ChoreographyClient.default_service_name)

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
        self.rotation['yaw'] = yaw
        self.rotation['roll'] = roll
        self.rotation['pitch'] = pitch
        cmd = RobotCommandBuilder.synchro_stand_command(
            footprint_R_body=rotation, body_height = self.height)
        self.command_client.robot_command(cmd)
        log(f"Rotating Spot\n\tyaw: {yaw}\n\troll: {roll}\n\tpitch: {pitch}")
        # I know the line is long. I'm lazy.
        #self.print(f'Rotated to yaw: {round(yaw, 2)}({round(math.degrees(yaw), 2)}°), roll: {round(roll, 2)}({round(math.degrees(roll), 2)}°), pitch: {round(pitch, 2)}({round(math.degrees(pitch), 2)}°)')

    @dispatch
    def stand(self) -> None:
        """
        Stands the robot
        """        
        cmd = RobotCommandBuilder.synchro_stand_command(body_height = self.height)
        self.command_client.robot_command(cmd)
        log("Standing Spot")

    def sit(self) -> None:
        """
        Sits the robot
        """        
        cmd = RobotCommandBuilder.synchro_sit_command()
        log("Sitting Spot")
        try:
            self.command_client.robot_command(cmd)
        except Exception as e:
            print(type(e))
            if type(e) == bosdyn.client.robot_command.BehaviorFaultError:
                websocket.websocket_list.print(-1, "<red>Robot is unable to sit.</red> Try <b>self-righting</b>.", all=True)

    def self_right(self) -> None:
        """
        Self-rights the robot
        """        
        self.sit()
        time.sleep(1)
        cmd = RobotCommandBuilder.selfright_command()
        log('Self-righting Spot')
        try:
            self.command_client.robot_command(cmd)
        except Exception as e:
            if type(e) == bosdyn.client.robot_command.BehaviorFaultError:
                websocket.websocket_list.print(-1, "<red>Robot is unable to self-right.</red> You <b>must</b> turn the \
                    robot motors off, and back on again. Press 'End Main Loop`, wait for the motors to turn off, \
                        and press 'Start All'. Self-right before attemtping to sit or stand.", all=True)


    @dispatch
    def roll_over(self) -> None:
        """
        Rolls the robot over (to take out battery)
        """
        log("Rolling over Spot")
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
        self.print(f"Setting body height to: {self.height}")
        walk = RobotCommandBuilder.synchro_velocity_command(x, y, z, body_height = self.height, locomotion_hint=self.locomotion_hint)
        '''
        walk.synchronized_command.mobility_command.params.CopyFrom(
            RobotCommandBuilder._to_any(self.collision_avoid_params))
        '''
        self.command_client.robot_command(walk, end_time_secs=time.time() + t)
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
        log(f"Walking Spot\n\tx: {x}\n\ty: {y}\n\tz: {z}\n\ttime: {t}\n\tdistance: {d}")

        # Set the time based off of the desired distance (NOT WORKING PROPERLY - probably need to do vector math)
        if t == 0:
            distance = math.sqrt(x ** 2 + y ** 2 + z ** 2)
            t = d/distance

        # Splits commands up if specified turn value is too high. Works, but can probably be improved
        self._send_walk_command(x, y, z, t = t)

    @dispatch
    def move(self, x, y, z, max_vel=0.5):

        '''
        if self.locomotion_hint == spot_command_pb2.HINT_JOG or self.locomotion_hint == spot_command_pb2.HINT_HOP:
            self.walk(x,y,z, t=1)
            return
        '''

        x = float(x)
        y = float(y)

        z *= math.pi / 180
        
        robot_state_client = self.robot.ensure_client(RobotStateClient.default_service_name)
        transforms = robot_state_client.get_robot_state().kinematic_state.transforms_snapshot

        frame_name = ODOM_FRAME_NAME

        # Build the transform for where we want the robot to be relative to where the body currently is.
        body_tform_goal = math_helpers.SE2Pose(x=x, y=y, angle=z)
        # We do not want to command this goal in body frame because the body will move, thus shifting
        # our goal. Instead, we transform this offset to get the goal position in the output frame
        # (which will be either odom or vision).
        out_tform_body = get_se2_a_tform_b(transforms, frame_name, BODY_FRAME_NAME)
        out_tform_goal = out_tform_body * body_tform_goal

        max_vel = 0.5

        vel_limit = geometry_pb2.SE2VelocityLimit(max_vel=geometry_pb2.SE2Velocity(linear=geometry_pb2.Vec2(x=max_vel, y=max_vel),angular=0.5))

        params = RobotCommandBuilder.mobility_params(locomotion_hint=self.locomotion_hint, body_height=self.height)
        params.vel_limit.CopyFrom(vel_limit)        

        # Command the robot to go to the goal point in the specified frame. The command will stop at the
        # new position.
        robot_cmd = RobotCommandBuilder.synchro_se2_trajectory_point_command(
            goal_x=out_tform_goal.x, goal_y=out_tform_goal.y, goal_heading=out_tform_goal.angle,
            frame_name=frame_name, params=params)
        
        turn_time = abs(z) / 0.5

        print(f"turn_time: {turn_time}")
        print(f"x: {x}, y: {y}")

        end_time = max(max(abs(x), abs(y)) / max_vel,  turn_time)

        print(f"end_time: {end_time}")

        cmd_id = self.command_client.robot_command(lease=None, command=robot_cmd,
                                                    end_time_secs=time.time() + end_time)
        # Wait until the robot has reached the goal.
        while True:
            feedback = self.command_client.robot_command_feedback(cmd_id)
            mobility_feedback = feedback.feedback.synchronized_feedback.mobility_command_feedback
            if mobility_feedback.status != RobotCommandFeedbackStatus.STATUS_PROCESSING:
                print("Failed to reach the goal")
                return False
            traj_feedback = mobility_feedback.se2_trajectory_feedback
            if (traj_feedback.status == traj_feedback.STATUS_AT_GOAL and
                    traj_feedback.body_movement_status == traj_feedback.BODY_STATUS_SETTLED):
                print("Arrived at the goal.")
                return True
            time.sleep(1)

    @dispatch
    def set_height(self, height: float) -> None:
        """
        Sets the stand height of the robot

        Args:
            height (float): The height
        """        
        # Create stand height command
        self.height = clamp(height, self.HEIGHT_OFFSET_MIN, self.HEIGHT_OFFSET_MAX)
        cmd = RobotCommandBuilder.synchro_stand_command(body_height=self.height)
        self.command_client.robot_command(cmd)
        self.print(f'Standing at: {height}')
        log(f"Standing Spot at: {self.height}")

    def set_locomotion_hint(self, hint: str):
        if hint == "auto":
            self.locomotion_hint = spot_command_pb2.HINT_AUTO
        if hint == "trot":
            self.locomotion_hint = spot_command_pb2.HINT_TROT
        if hint == "crawl":
            self.locomotion_hint = spot_command_pb2.HINT_CRAWL
        if hint == "jog":
            self.locomotion_hint = spot_command_pb2.HINT_JOG
        if hint == "hop":
            self.locomotion_hint = spot_command_pb2.HINT_HOP
    


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
            dz * self.KEYBOARD_TURN_VELOCITY,
            body_height = self.height
        )
        '''
        walk.synchronized_command.mobility_command.params.CopyFrom(
            RobotCommandBuilder._to_any(self.collision_avoid_params))
        '''
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
            footprint_R_body=rotation, body_height = self.height)
        self.command_client.robot_command(cmd)

    
    @dispatch
    def do_dance_sequence(self, sequence_filename: str):
        default_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), ("Dance Moves/" + sequence_filename))
        choreography = load_choreography_sequence_from_txt_file(default_filepath)
        try:
            upload_response = self.choreography_client.upload_choreography(choreography, non_strict_parsing=True)
        except UnauthenticatedError as err:
            print(
                "The robot license must contain 'choreography' permissions to upload and execute dances. "
                "Please contact Boston Dynamics Support to get the appropriate license file. ")
            return True
        except ResponseError as err:
            # Check if the ChoreographyService considers the uploaded routine as valid. If not, then the warnings must be
            # addressed before the routine can be executed on robot.
            error_msg = "Choreography sequence upload failed. The following warnings were produced: "
            for warn in err.response.warnings:
                error_msg += warn
            print(error_msg)
            return
        
        cmd = RobotCommandBuilder.synchro_stand_command(body_height = 0)
        self.command_client.robot_command(cmd)
        routine_name = choreography.name
        # Then, set a start time five seconds after the current time.
        client_start_time = time.time() + 1
        # Specify the starting slice of the choreography. We will set this to slice=0 so that the routine begins at
        # the very beginning.
        start_slice = 0
        # Issue the command to the robot's choreography service.
        self.choreography_client.execute_choreography(choreography_name=routine_name,
                                                client_start_time=client_start_time,
                                                choreography_starting_slice=start_slice)

        # Estimate how long the choreographed sequence will take, and sleep that long.
        total_choreography_slices = 0
        for move in choreography.moves:
            total_choreography_slices += move.requested_slices
        estimated_time_seconds = total_choreography_slices / choreography.slices_per_minute * 60.0
        time.sleep(estimated_time_seconds + 2)


    @dispatch
    def setup(self) -> None:
        """
        Stands and resets the robot's orientation
        """        
        self.stand()
        self.rotate(0, 0, 0)
        time.sleep(0.5)
