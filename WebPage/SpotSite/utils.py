import time
import json
import os
import sys
from threading import Thread
from pathlib import Path

import bosdyn

from SpotSite import websocket
from SpotSite.spot_logging import log


def with_retries(func, number_retries=10, time_between_sec=3, *args, **kwargs):
    for _ in range(0, number_retries):
        socket_print(-1, f"Retrying: #{_} ", all=True)
        try:
            func(args, kwargs)
        except:
            pass
        time.sleep(time_between_sec)


def start_thread(func, args: tuple = ()):
    """Starts a new thread from the given function to

    Args:
        func (_type_): the function
        args (tuple, optional): any arguments passed to the function. Defaults to ().
    """
    thread = Thread(target=func, args=args)
    thread.start()


def socket_print(socket_index: any, message: str, all: bool = False, type: str = "output"):
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

    log(f"Exception\n\ttype: {exc_type}\n\tobject: {exc_obj}\n\tfilename: {fname}\n\tline: {exc_tb.tb_lineno}")
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
        socket_print(socket_index, message, all=(socket_index == -1))


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
