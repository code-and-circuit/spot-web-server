from django.shortcuts import render
from SpotSite import background_process, websocket
from django.http import HttpResponseRedirect, JsonResponse
from django.core import serializers

import json

# Renders the main site
def main_site(request):
    print("WEBSITE!?")
    # Is the background process running or not? 
    # Reflected in the yellow text output at top of webpage
    context = {
        "is_running": background_process.bg_process.is_running,
    }
    return render(request, 'main_site.html', context)

# Relays action information
def do_action(request, action):
    if request.method == "GET":
        background_process.do_action(action, request.GET["socket_index"])

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

# Runs the program in the file
def run_program(request):
    do_action(request, "run_program")
    
    return JsonResponse({
        "valid": True, 
    }, status = 200)
    
# Handles and relays commands sent from Scratch to be executed by the robot
def run_command(request):
    if request.method == "POST":
        # Obtains data from the json file
        data = json.loads(request.body.decode("utf-8"))
        action = data['Command']
        args = data['Args']
        # Adds the command to the queue of commands
        background_process.bg_process.command_queue.append({
            action: action, 
            args: args
        })
        
    return JsonResponse({
        "valid": True,
    }, status = 200)

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
    print("WEB SOCKET??")
    socket_index = websocket.websocket_list.add_socket(socket)
    await socket.accept()
    await socket.send_json({
        'type' : "socket_create",
        'socket_index' : socket_index
    })
    await websocket.websocket_list.sockets[socket_index].keep_alive()
