from django.shortcuts import render
from SpotSite import spotMain, output, websocket
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.core import serializers

import json

def main_site(request):
    
    context = {
        "is_running": spotMain.bg_process.main_function.is_running,
    }
    return render(request, 'main_site.html', context)

def do_action(request, action):
    if request.method == "GET":
        spotMain.do_action(action, request.GET["socket_index"])
    return

def start_process(request):
    do_action(request, "start")
    
    return JsonResponse({
        "valid": True, 
    }, status = 200)

def end_process(request):
    do_action(request, "end")    
    return JsonResponse({
        "valid": True, 
    }, status = 200)  

def run_program(request):
    print("RUN")
    do_action(request, "run_program")
    
    return JsonResponse({
        "valid": True, 
    }, status = 200)
    
def run_command(request):
    
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        action = data['Command']
        args = data['Args']
        spotMain.bg_process.main_function.command_queue.append({
            action: action, 
            args: args
        })
        
    return JsonResponse({
        "valid": True,
    }, status = 200)

def get_info(request):
    if request.method == "GET":
        return JsonResponse({
            "valid": True,
            "is_running": spotMain.bg_process.main_function.is_running,
        }, status=200)
        
async def websocket_view(socket):
    socket_index = websocket.websocket_list.add_socket(socket)
    await socket.accept()
    await socket.send_json({
        'type' : "socket_create",
        'socket_index' : socket_index
    })
    await websocket.websocket_list.sockets[socket_index].keep_alive()
