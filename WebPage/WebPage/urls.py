from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView
from django.urls import path
from django.urls import include
import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.main_site),
    path("ws/", views.websocket_view, name="websocket"),
    path('startProcess', views.start_process, name='startProcess'),
    path('endProcess', views.end_process, name="endProcess"),
    path('runProgram', views.run_program, name='runProgram'),
    path('estop', views.estop, name='estop'),
    path('estop_release', views.estop_release, name='estop_release'),
    path('getInfo', views.get_info, name='getInfo'),
    path('get-server-state', views.get_server_state, name='get_server_state'),
    path('toggle-accept-command', views.toggle_accept_command, name='toggle_accept_command'),
    path('command', views.run_command, name='command'),
    path('program', views.add_program, name='add_program'),
    path('get-programs', views.get_programs, name='get_programs'),
    path('remove-program', views.remove_program, name='remove_program'),
    path('file', views.receive_file, name='file'),
    path('connect', views.connect_to_robot, name='connect'),
    path('disconnect_robot', views.disconnect_robot, name='disconnect_robot'),
    path('clear_estop', views.clear_estop, name='clear_estop'),
    path('clear_lease', views.clear_lease, name='clear_lease'),

    path('lease', views.acquire_lease, name='lease'),
    path('get_estop', views.acquire_estop, name='get_estop'),
    path(
        "favicon.ico",
        RedirectView.as_view(url=staticfiles_storage.url("favicon.ico")),
    ),
    #path('__debug__/', include('debug_toolbar.urls')),
]
