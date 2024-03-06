import bosdyn.client
import bosdyn.client.lease
from bosdyn.api import robot_command_pb2, mobility_command_pb2
from bosdyn.api.spot import robot_command_pb2 as spot_command_pb2
import bosdyn.client.util
import bosdyn.geometry
from bosdyn.client.robot_command import RobotCommandBuilder, blocking_stand

from bosdyn.choreography.client.choreography import (ChoreographyClient,
                                                     load_choreography_sequence_from_txt_file)
from bosdyn.client import ResponseError, RpcError, create_standard_sdk
from bosdyn.client.exceptions import UnauthenticatedError
from bosdyn.client.lease import LeaseClient, LeaseKeepAlive
from bosdyn.client.license import LicenseClient
from bosdyn.api.basic_command_pb2 import RobotCommandFeedbackStatus
from bosdyn.client import math_helpers
from bosdyn.client.frame_helpers import (BODY_FRAME_NAME, ODOM_FRAME_NAME, VISION_FRAME_NAME,
                                         get_se2_a_tform_b)
from bosdyn.client.robot_state import RobotStateClient

from bosdyn.api import geometry_pb2




import os, time

def main(robot, command_client):
    # blocking_stand(command_client)

    
    
    license_client = robot.ensure_client(LicenseClient.default_service_name)
    if not license_client.get_feature_enabled([ChoreographyClient.license_name
                                              ])[ChoreographyClient.license_name]:
        print("This robot is not licensed for choreography.")
        exit()

    choreography_client = robot.ensure_client(ChoreographyClient.default_service_name)

    sequences_on_robot = choreography_client.list_all_moves().move_param_config
    print(sequences_on_robot)
    # return


    DEFAULT_DANCE = "test_dance.csq"
    default_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), DEFAULT_DANCE)
    choreography = load_choreography_sequence_from_txt_file(default_filepath)
    try:
        upload_response = choreography_client.upload_choreography(choreography, non_strict_parsing=True)
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
    command_client.robot_command(cmd)
    routine_name = choreography.name
    # Then, set a start time five seconds after the current time.
    client_start_time = time.time() + 1
    # Specify the starting slice of the choreography. We will set this to slice=0 so that the routine begins at
    # the very beginning.
    start_slice = 0
    # Issue the command to the robot's choreography service.
    choreography_client.execute_choreography(choreography_name=routine_name,
                                             client_start_time=client_start_time,
                                             choreography_starting_slice=start_slice)

    # Estimate how long the choreographed sequence will take, and sleep that long.
    total_choreography_slices = 0
    for move in choreography.moves:
        total_choreography_slices += move.requested_slices
    estimated_time_seconds = total_choreography_slices / choreography.slices_per_minute * 60.0
    time.sleep(estimated_time_seconds + 2)
