# spot-web-server

**NEEDED TO RUN**
add a file to spot-web-server\WebPage\SpotSite named 
```
secrets.py
```
containing 
```
username = YOUR_ROBOT_USERNAME
password = YOUR_ROBOT_PASSWORD
SECRET_KEY = YOUR_DJANGO_SECRET_KEY
```

**To Run**
run commands:
```
cd path/to/WebPage
uvicorn WebPage.asgi:application
```
Arguments: 
- ```--host 0.0.0.0``` to make it publicy accessable
- ```--reload``` to automatically reload when files are changed

**TODO**
- File to hold default starting configuration (ex. whether the server is accepting commands)
- Option to automatically connect to the robot on server startup
- Ability to end program execution or clear the command queue without estopping the robot
- Ability to accept commands but not execute them (toggle whether commands are executed immediately)
- Document the information returned from the get_state functions
- Rewrite or credit the creator of connection.py
- Add a complete description of what the server does, the features, how to uses it, and how you could create your own frontend with it
- Potentially rework how ```do_action``` in ```background_process.py``` works
- Clean up ```background_process.py``` (separate into more files, etc.) 
- Clean up ```background_process.Background_Process._get_image``` when images cannot be stitched
- Tell if the robot is executing a motor command and block or hold other commands until it is done
- Create multiple walk commands if desired walking time exceeds the time allowed by the robot. If the desired time is too high, the robot says that the command is too far in the future
- How to install and run
