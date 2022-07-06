import re
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.http import HttpResponse, HttpRequest
"""
Handles requests sent to the server

See urls.py to see which functions correspond to which urls

Functions:

    main_site(request) -> HttpResponse:
    do_action(request, action, method_check)
    start_process(request) -> JsonResponse
    end_process(request) -> JsonResponse
    connect_to_robot(reqest) -> JsonResponse
    disconnect_robot(request) -> JsonResponse
    acquire_estop(request) -> JsonResponse
    clear_estop(request) -> JsonResponse
    acquire_lease(request) -> JsonResponse
    clear_lease(request) -> JsonResponse
    run_program(request) -> JsonResponse
    remove_program(request) -> JsonResponse
    estop(request) -> JsonResponse
    estop_release(request) -> JsonResponse
    toggle_accept_command(request) -> JsonResponse
    run_command(request) -> JsonResponse
    add_program(request) -> JsonResponse
    get_programs(request) -> JsonResponse
    write_file(object)
    receive_file(request) -> JsonResponse
    get_info(request) -> JsonResponse
    get_state_of_everything(request) -> JsonResponse
    get_server_state(request) -> JsonResponse
    get_internal_state(request) -> JsonResponse
    get_keyboard_control_state(request) -> JsonResponse
    websocket_view(object)
"""

from django.http import JsonResponse
from django.core import serializers
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from SpotSite import background_process
from SpotSite import websocket
from SpotSite.spot_logging import log_action
from SpotSite.spot_logging import log

import pathlib
import json
import os
import time

# Renders the main site
def main_site(request: HttpRequest) -> HttpResponse:
    """
    Renders the main site

    Args:
        request (HttpRequest): the request

    Returns:
        HttpResponse: the rendered site
    """

    return render(request, 'main_site.html')

# Utility function to relay action information. method_check allows post requests to be passed if parameter is true
def do_action(request: HttpRequest, action: str, method_check: bool = False):
    """
    Relays action information to background_process.py
    
    See background_process.py.do_action for the handling of the actions

    Args:
        request (HttpRequest): the request
        action (str): the action
        method_check (bool, optional): whether POST reqeusts are allowed. Defaults to False.
    """
    if request.method == "GET" or method_check == True:
        selected_program = None
        if "selected_program" in request.GET:
            selected_program = request.GET["selected_program"]
        background_process.do_action(
            action, request.GET["socket_index"], selected_program)

def start_process(request: HttpRequest) -> JsonResponse:
    """
    Starts the main background process

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "start")

    return JsonResponse({
        "valid": True,
    }, status=200)

def end_process(request: HttpRequest) -> JsonResponse:
    """
    Ends the main background process

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "end")
    return JsonResponse({
        "valid": True,
    }, status=200)

def connect_to_robot(request: HttpRequest) -> JsonResponse:
    """
    Attemps to connect the server to the robot

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "connect")
    return JsonResponse({
        "valid": True,
    }, status=200)

def disconnect_robot(request: HttpRequest) -> JsonResponse:
    """
    Attemps to disconnect the server from the robot to

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "disconnect_robot")
    return JsonResponse({
        "valid": True,
    }, status=200)
    
def acquire_estop(request: HttpRequest) -> JsonResponse:
    """
    Attemps to acquire the estop from the robot to

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "acquire_estop")
    return JsonResponse({
        "valid": True,
    }, status=200)

def clear_estop(request: HttpRequest) -> JsonResponse:
    """
    Clears and returns the estop

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "clear_estop")
    return JsonResponse({
        "valid": True,
    }, status=200)

def acquire_lease(request: HttpRequest) -> JsonResponse:
    """
    Attemps to acquire the lease from the robot

    Args:
        request (HttpRequest): the requesting

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "acquire_lease")
    return JsonResponse({
        "valid": True,
    }, status=200)

def clear_lease(request: HttpRequest) -> JsonResponse:
    """
    Clears and returns the lease

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "clear_lease")
    return JsonResponse({
        "valid": True,
    }, status=200)

def run_program(request: HttpRequest) -> JsonResponse:
    """
    Runs a selected program

    Args:
        request (HttpRequest): the request containing the name of the selected program in the field ```selected_program```

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "run_program")

    return JsonResponse({
        "valid": True,
    }, status=200)

def remove_program(request: HttpRequest) -> JsonResponse:
    """
    Removes a program with a given name

    Args:
        request (HttpRequest): the request containing the name of the selected program in the field ```selected_program```

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "remove_program")

    return JsonResponse({
        "valid": True
    }, status=200)

def estop(request: HttpRequest) -> JsonResponse:
    """
    Attempts to estop the robot

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "estop")

    return JsonResponse({
        "valid": True
    }, status=200)

def estop_release(request: HttpRequest) -> JsonResponse:
    """
    Attempts to release the estop

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "estop_release")

    return JsonResponse({
        "valid": True
    }, status=200)

def toggle_accept_command(request: HttpRequest) -> JsonResponse:
    """
    Toggles whether the server is accepting robot commands

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    do_action(request, "toggle_accept_command")
        
    return JsonResponse({
                "valid": True,
            }, status=200)

# Handles and relays commands sent from Scratch to be executed by the robot
def run_command(request: HttpRequest) -> JsonResponse:
    """
    Runs a robot command

    Args:
        request (HttpRequest): the request containing the command information

    Returns:
        JsonResponse: Valid response returned, also tells whether the command was successfully added to the queue
            If the request method is POST, returns whether the connection to the server was valid
                (if the client is allowed to send commands). Not implemented, but could
                be used to implement a lease-like system with the Scratch plugin
    """
    if request.method == "POST":
        # Obtains data from the json file
        data = json.loads(request.body.decode("utf-8"))
        if background_process.bg_process.is_running and not background_process.bg_process.robot.is_estopped() and \
            background_process.bg_process._is_accepting_commands:
            # Adds the command to the queue of commands
            background_process.bg_process.command_queue.append(data)
            return JsonResponse({
                "valid": True,
                "command_sent": True
            }, status=200)

            
    elif request.method == "GET":
        return JsonResponse({
            'connection_valid': True
        }, status=200)

    print(background_process.bg_process.is_accepting_commands)
    
    return JsonResponse({
                "valid": True,
                "command_sent": False
            }, status=200)

def add_program(request: HttpRequest) -> JsonResponse:
    """
    Adds a program to the database

    Args:
        request (HttpRequest): the request containing the program name and command list

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    if request.method == "POST":
        # Obtains data from the json file
        data = json.loads(request.body.decode("utf-8"))
        background_process.bg_process.add_program(
            data['name'], data['commands'])

        return JsonResponse({
            "valid": True,
        }, status=200)

    return JsonResponse({
        "valid": False,
    }, status=200)

def get_programs(request: HttpRequest) -> JsonResponse:
    """
    Returns all program information in the database.

    Args:
        request (HttpRequest): the resut

    Returns:
        JsonResponse: All program information
    """
    return JsonResponse({
        "valid": True,
        "programs": background_process.bg_process.get_programs()
    }, status=200)

def write_file(file: object) -> None:
    """
    Writes a file to the folder ```files_to_run\```

    Args:
        file (object): The file to be written
    """
    path = str(pathlib.Path(__file__).parent.resolve()) + \
        "\\files_to_run\\" + file.name
    if os.path.exists(path):
        os.remove(path)
    default_storage.save(path, ContentFile(file.read()))

# Allows entire files to be sent and run. 
# ---> NOT GOOD FOR SECURITY <---
def receive_file(request: HttpRequest) -> JsonResponse:
    """
    Receives a file or list of files and writes them to a folder.

    Args:
        request (HttpRequest): the request containing all files

    Returns:
        JsonResponse: Valid response returned if action was successful
    """
    valid = True
    main_name = request.POST['main']
    if request.method == "POST":
        try:
            files = request.FILES
            for file in files:
                write_file(files[file])

            import importlib.util
            path = str(pathlib.Path(__file__).parent.resolve()) + \
                "\\files_to_run\\" + main_name
            spec = importlib.util.spec_from_file_location("main", path)
            main_file = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_file)
            main_file.main()

        except Exception as e:
            print(e)
            valid = False

    return JsonResponse({
        "valid": valid,
    }, status=200)

# 
def get_info(request: HttpRequest) -> JsonResponse:
    """
    Gets information about the state of the server
        Currently only used to tell if the background process is running

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Server state information
    """
    if request.method == "GET":
        return JsonResponse({
            "valid": True,
            "is_running": background_process.bg_process.is_running,
        }, status=200)

def get_state_of_everything(request: HttpRequest) -> JsonResponse:
    """
    Returns an object containing state information about every attribute of background_process.bg_process
        Uses the one-line return statement (mainly for fun)

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Server state information
    """
    if request.method == "GET":
        state = background_process.bg_process.get_state_of_everything()
        try:
            return JsonResponse(state, status=200)
        except Exception as e:
            return JsonResponse({}, status=500)
        
def get_server_state(request: HttpRequest) -> JsonResponse:
    """
    Returns helpful information about the state of the server

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Server state information
    """
    if request.method == "GET":
        state = background_process.bg_process.get_server_state()
        try:
            return JsonResponse(state, status=200)
        except Exception as e:
            print(e)
            return JsonResponse({}, status=500)
        
def get_internal_state(request: HttpRequest) -> JsonResponse:
    """
    Returns the internal state of the server

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Internal state information

    """
    if request.method == "GET":
        state = background_process.bg_process.get_internal_state()
        try:
            return JsonResponse(state, status=200)
        except Exception:
            return JsonResponse({}, status=500)
        
def get_keyboard_control_state(request: HttpRequest) -> JsonResponse:
    """
    Returns information about the keyboard control state

    Args:
        request (HttpRequest): the request

    Returns:
        JsonResponse: Keyboard control state information
    """
    if request.method == "GET":
        state = background_process.bg_process.get_keyboard_control_state()
        try:
            return JsonResponse(state, status=200)
        except Exception:
            return JsonResponse({}, status=500)

def clear_queue(request: HttpRequest) -> JsonResponse:
    background_process.bg_process.command_queue = []

    return JsonResponse({}, status=200)

def toggle_auto_run(request: HttpRequest) -> JsonResponse:
    do_action(request, "toggle_auto_run");

    return JsonResponse({}, status=200)

def step_command(request: HttpRequest) -> JsonResponse:
    do_action(request, "step_command")
    return JsonResponse({}, status=200)
        
async def websocket_view(socket: object) -> None:
    """
    Handles new websockets and adds them to a list of active sockets. Then keeps the socket alive forever (until it closes itself)

    Args:
        socket (object): the websocket object
    """
    socket_index = websocket.websocket_list.add_socket(socket)
    
    await socket.accept()
    await socket.send_json({
        'type': "socket_create",
        'socket_index': socket_index
    })
    await websocket.websocket_list.sockets[socket_index].keep_alive()
