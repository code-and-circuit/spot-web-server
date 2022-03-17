from django.contrib import admin
from django.urls import path, include
from SpotSite import views

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
    path('command', views.run_command, name='command'),
    #path('__debug__/', include('debug_toolbar.urls')),
]