from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView
from django.urls import path
from django.urls import include
from SpotSite import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.main_site),
    path("ws/", views.websocket_view, name="websocket"),
    path('start-process', views.start_process, name='start_process'),
    path('end-process', views.end_process, name="end_process"),
    path('run-program', views.run_program, name='run_program'),
    path('estop', views.estop, name='estop'),
    path('estop_release', views.estop_release, name='estop_release'),
    path('get-info', views.get_info, name='get_info'),
    path('get-server-state', views.get_server_state, name='get_server_state'),
    path('toggle-accept-command', views.toggle_accept_command, name='toggle_accept_command'),
    path('command', views.run_command, name='command'),
    path('program', views.add_program, name='add_program'),
    path('get-programs', views.get_programs, name='get_programs'),
    path('remove-program', views.remove_program, name='remove_program'),
    path('file', views.receive_file, name='file'),
    path('connect', views.connect_to_robot, name='connect'),
    path('disconnect_robot', views.disconnect_robot, name='disconnect_robot'),
    path('clear-estop', views.clear_estop, name='clear_estop'),
    path('clear-lease', views.clear_lease, name='clear_lease'),
    path('lease', views.acquire_lease, name='lease'),
    path('get-estop', views.acquire_estop, name='get_estop'),
    path('clear-queue', views.clear_queue, name="clear_queue"),
    path('toggle-auto-run', views.toggle_auto_run, name='toggle_auto_run'),
    path('step-command', views.step_command, name='step_command'),
    path('execute-file', views.execute_file, name='execute_file'),
    path(
        "favicon.ico",
        RedirectView.as_view(url=staticfiles_storage.url("favicon.ico")),
    ),
    #path('__debug__/', include('debug_toolbar.urls')),
]
