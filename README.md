# spot-web-server

**To Run**

- add a file to spot-web-server\WebPage\SpotSite named 
  ```
  secrets.py
  ```
  containing 
  ```
  ROBOT_USERNAME = YOUR_ROBOT_USERNAME
  ROBOT_PASSWORD = YOUR_ROBOT_PASSWORD
  SECRET_KEY = YOUR_DJANGO_SECRET_KEY
  ROBOT_IP = YOUR_SPOT_IP (192.168.80.3 by default)
  ```
- ```cd path/to/spot-web-server/WebPage```
- run ```uvicorn WebPage.asgi:application``` or ```python -m uvicorn WebPage.asgi:application``` or ```python3 -m uvicorn WebPage.asgi:application``` depending on your environment configuration.

Arguments for run command: 
- ```--host [Address]``` (0.0.0.0 to make it publicy accessable)
- ```--reload``` to automatically reload when files are changed
- ```--port [Port]``` to set the port (8000 by default)

**TODO**
- Document the information returned from the get_state functions
- Rewrite or credit the creator of connection.py
- Add a complete description of what the server does, the features, how to uses it, and how you could create your own frontend with it
- Potentially rework how ```do_action``` in ```background_process.py``` works
- Clean up ```background_process.py``` (separate into more files, etc.) 
- Clean up ```background_process.Background_Process._get_image``` when images cannot be stitched
- Tell if the robot is executing a motor command and block or hold other commands until it is done
- Create multiple walk commands if desired walking time exceeds the time allowed by the robot. If the desired time is too high, the robot says that the command is too far in the future
- How to install and run
- Explain the best way to add to/continue developing the server
- Retry connection attempts if first attempt to robot failed
- Ability to run a single command at a time from the queue (step through one-by-one)
- Ability to set a constant wait period between commands
