# spot-web-server

## Overview
*insert paragraph*

## Installing and Running
There is a known potential issue with image stitching when running the server on a device with no graphical context. Xvfb can be used to create this context virtually, or the issue can be ignored and the server will handle it.
### Installing
Clone the repository, then run ```pip -r install /path/to/repo/WebPage/requirements.txt``` to install python required python modules.

### Running

1. add a file to spot-web-server\WebPage\SpotSite named  ``` secrets.py``` containing 
      ```
      ROBOT_USERNAME = YOUR_ROBOT_USERNAME
      ROBOT_PASSWORD = YOUR_ROBOT_PASSWORD
      SECRET_KEY = YOUR_DJANGO_SECRET_KEY
      ROBOT_IP = YOUR_SPOT_IP
      ```
2. ```cd path/to/spot-web-server/WebPage```
3. ```uvicorn WebPage.asgi:application```

Arguments for command: 
- ```--host [Address]``` (0.0.0.0 to make it publicy accessable)
- ```--reload``` to automatically reload when files are changed
- ```--port [Port]``` to set the port (8000 by default)

## TODO

Make a dedicated website explaining the server

### Important: (in order of importance)

1. Explain the best way to add to/continue developing the server
2. Add a complete description of what the server does, the features, how to use it, and how you could create your own frontend with it
3. Add logging for erorr investigation and usage information
4. Document the information returned from the get_state functions\

### General ToDos

- Rewrite connection.py (it's too complicated, code was hacked together from multiple sources)
- Create multiple walk commands if desired walking time exceeds the time allowed by the robot. If the desired time is too high, the robot says that the command is too far in the future
- Retry connection attempts if first attempt to robot failed
- Add an "alert", or something that briefly displays new console outputs in case client is not looking at the console
- Add ability to change the port 
- Add rate limiting for certain keyboard controls from client (stand/sit commands should only be sent once/second, etc.)
- Add more stuff to the config.json for more customizability
