import time, math
from bosdyn.api import robot_command_pb2, mobility_command_pb2
from bosdyn.api.spot import robot_command_pb2 as spot_command_pb2

import bosdyn.client.util, bosdyn.geometry

from bosdyn.client.robot_command import RobotCommandBuilder, blocking_stand

from SpotSite import websocket

class SpotFunction:
    def __init__(self, cmd_client, s):
        self.command_client = cmd_client
        self.socket_index = s

    def print(self, message, all=False, type="output"):
        assert self.socket_index != -1, print(message)
        websocket.websocket_list.print(self.socket_index, message, all=all, type=type)

    def rotate(self, yaw, roll, pitch):
        rotation = bosdyn.geometry.EulerZXY(yaw=yaw, roll=roll, pitch=pitch)
        cmd = RobotCommandBuilder.synchro_stand_command(footprint_R_body=rotation)
        self.command_client.robot_command(cmd)
        self.print(f'Rotated to yaw: {yaw}, roll: {roll}, pitch: {pitch}')
        
        
    def stand(self):
        
        blocking_stand(self.command_client, timeout_sec = 20)
        self.print("Stood up")
        
    def walk(self, x, y, z, t=0, d=0):
        
        if t == 0:
            distance = math.sqrt(x ** 2 + y ** 2 + z ** 2)
            t = d/distance
        
        m = spot_command_pb2.ObstacleParams(obstacle_avoidance_padding = 1, disable_vision_foot_obstacle_avoidance = False, 
                                            disable_vision_foot_constraint_avoidance = False, disable_vision_body_obstacle_avoidance = False,
                                            disable_vision_foot_obstacle_body_assist = True, disable_vision_negative_obstacles = False)
        
        
        
        walk = RobotCommandBuilder.synchro_velocity_command(x, y, z)
        walk.synchronized_command.mobility_command.params.CopyFrom(
                        RobotCommandBuilder._to_any(m))    
        self.command_client.robot_command(walk, end_time_secs=time.time() + t)
        self.print(f'Walking at ({x}, {y}, {z})m/s for {t}s')
        time.sleep(t)
        
        
    def set_stand_height(self, height):
        cmd = RobotCommandBuilder.synchro_stand_command(body_height=height)
        self.command_client.robot_command(cmd)
        self.print(f'Standing at: {height}')

    def setup(self):
        self.stand(False)
        self.rotate(0, 0, 0)

    def do_function(self):
        self.setup()
        #await walk(-.2, 0, 0, d=1)