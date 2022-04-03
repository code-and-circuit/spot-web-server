from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.core import serializers
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

import background_process
from SpotSite import websocket

import pathlib
import json
import os

# Renders the main site
def main_site(request):
    # Is the background process running or not? 
    # Reflected in the yellow text output at top of webpage
    context = {
        "is_running": background_process.bg_process.is_running,
        "programs": background_process.bg_process.programs
    }
    return render(request, 'main_site.html', context)

# Relays action information
def do_action(request, action):
    if request.method == "GET":
        background_process.do_action(action, request.GET["socket_index"], request.GET["selected_program"])

# Starts the background process
def start_process(request):
    do_action(request, "start")
    
    return JsonResponse({
        "valid": True, 
    }, status = 200)

# Ends the background process
def end_process(request):
    do_action(request, "end")    
    return JsonResponse({
        "valid": True, 
    }, status = 200) 
    
def connect_to_robot(request):
    do_action(request, "connect")
    return JsonResponse({
        "valid": True, 
    }, status = 200)
    
def acquire_lease(request):
    do_action(request, "acquire_lease")
    return JsonResponse({
        "valid": True, 
    }, status = 200)
    
def acquire_estop(request):
    do_action(request, "acquire_estop")
    return JsonResponse({
        "valid": True, 
    }, status = 200)

# Runs the program in the file
def run_program(request):
    do_action(request, "run_program")
    
    return JsonResponse({
        "valid": True, 
    }, status = 200)
    
def remove_program(request):
    do_action(request, "remove_program")
    
    return JsonResponse({
        "valid": True
    }, status = 200)
    
def estop(request):
    do_action(request, "estop")
    
    return JsonResponse({
        "valid": True
    }, status = 200)
    
def estop_release(request):
    do_action(request, "estop_release")
    
    return JsonResponse({
        "valid": True
    }, status = 200)
    
# Handles and relays commands sent from Scratch to be executed by the robot
def run_command(request):
    if request.method == "POST":
        # Obtains data from the json file
        data = json.loads(request.body.decode("utf-8"))
                
        if background_process.bg_process.is_running and not background_process.bg_process.robot.is_estopped():
            # Adds the command to the queue of commands
            background_process.bg_process.command_queue.append(data)
            return JsonResponse({
                "valid": True,
            }, status = 200)
    return JsonResponse({
                "valid": False,
            }, status = 200)
    
def add_program(request):
    if request.method == "POST":
        # Obtains data from the json file
        data = json.loads(request.body.decode("utf-8"))
    
        background_process.bg_process.add_program(data['name'], data['commands'])
        # Adds the command to the queue of commands
        return JsonResponse({
            "valid": True,
        }, status = 200)
        
    return JsonResponse({
        "valid": False,
    }, status = 200)
    
def get_programs(request):
    return JsonResponse({
        "valid": True,
        "programs": background_process.bg_process.programs
    }, status=200)
    
def write_file(file):
    path = str(pathlib.Path(__file__).parent.resolve()) + "\\files_to_run\\" + file.name
    if os.path.exists(path):
        os.remove(path)
    default_storage.save(path, ContentFile(file.read()))
    
def receive_file(request):
    valid = True
    main_name = request.POST['main']
    if request.method == "POST":
        try:
            files = request.FILES
            for file in files:
                write_file(files[file])
                
            import importlib.util
            path = str(pathlib.Path(__file__).parent.resolve()) + "\\files_to_run\\" + main_name
            spec=importlib.util.spec_from_file_location("main",path)
            main_file = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_file)
            main_file.main()

        except Exception as e:
            print(e)
            valid = False
            
    return JsonResponse({
        "valid": valid,
    }, status=200)

# Gets information about the state of the server
# Currently only used to tell if the background process is running
def get_info(request):
    if request.method == "GET":
        return JsonResponse({
            "valid": True,
            "is_running": background_process.bg_process.is_running,
        }, status=200)
        
# Handles new websockets and adds them to a list of active sockets. Then keeps the socket alive forever (until it closes itself)
async def websocket_view(socket):
    socket_index = websocket.websocket_list.add_socket(socket)
    await socket.accept()
    await socket.send_json({
        'type' : "socket_create",
        'socket_index' : socket_index
    })
    try:
        await websocket.websocket_list.sockets[socket_index].keep_alive()
    except Exception as e:
        print("ERROR: ", e)
        websocket.websocket_list.remove_key(socket_index)
