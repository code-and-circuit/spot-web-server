# Code & Circuit's Spot Web Server
Created and maintained by Will Scheirey and the [Code & Circuit](https://codeandcircuit.org/) team

## Overview

### Thesis

Spot is an incredible tool for companies and organizations to use when they have specific purposes and missions for the robot to carry out and people with experience or knowledge using Spot, whether that be through the tablet or through the Spot SDK. The tools that are given to owners of Spot allow for many different uses of the robot, but do not very well support the use of Spot in a collaborative environemnt. Further, the Spot SDK is mainly only accessible to people with experience programming. This is completely fine and expected, as Boston Dynammics is more focused on creating robots, and allowing them to be used by people with experience in the field, than on teaching people how to program or learn how to use robots in general. 

A tool that would allow inexperienced people to control and program Spot would expand Spot's accessibility and outreach. It could not only be used by organizations with specific needs in mind, but as a teaching tool to allow students and inexperienced programmers to understand how robots work, and learn programming through controlling Spot. Many beginner programmers often get frustrated by a lack of results, and young programmers often do not see the use or potential in learning to program, as their results are often guided and/or not applicable in the real world. Learning to program using Spot, however, would give programmers immediate results and feedback, and allow them to get a better understanding of the potential of programming. With Spot being such an expensive robot and a household name, it could be a powerful tool to draw in people looking to get into programming. 

Being a single and very complicated robot, Spot, on its own, is not the best tool for many people to be programming at the same time. It is not made for a collaborative environment. Programmers must authenticate with and connect to Spot, connect and acquire each of Spot's services, and turn on Spot's motors each time they want to test and run a program. When the program is finished, they must wait for Spot's motors to turn off, and repeat the process to run a new program. When multiple people want to control Spot at the same time, such as in a classroom, this gets messy and there is much unecessary downtime betweeen when each person can run and test their program. A tool that would manage connections to the robot and allow programmers in a collaborative environment to control Spot without the need to worry about connecting, services, or turning on/off Spot's motors could create a much more streamlined process for people in such an environment to run their code.

With the right tools, Spot could be a vessel through which people learn to program and get involed in the field of programming and robotics in a collaborative environment.

### Code & Circuit's Spot Web Server

Code & Circuit's Spot Web Server was built with these ideas in mind. Not only does it provide a web interface for those wishing to control Spot without the tablet that comes with the robot, but it also provides the ability to control Spot using various forms of programming to suit a programmer's experience.

The web server is what connects to Spot and manages connections and services with the robot. A centralized place for such things to be managed means that people wishing to control Spot do not need to worry about them, but it also means that there is no downtime between when a program can be run. The server stays connected with Spot continuously so multiple programs can be run, edited, and rerun by multiple different people without ever having to turn Spot off or disconnect from the robot. Even for those wishing to code using the Spot SDK directly, the same is true.

*more details to follow*

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
3. ```python3 -m uvicorn WebPage.asgi:application```

Arguments for command: 
- ```--host [Address]``` (0.0.0.0 to make it publicy accessable)
- ```--reload``` to automatically reload when files are changed
- ```--port [Port]``` to set the port (8000 by default)

## Developing
While making changes directly on the dedicated server and simply restarted the corresponding service is good for quick fixes, this method is not good for debugging or automatic reload of the server. 

To develop, debug, and automatically reload the server, it is best to stop the corresponding service and run it manually in the terminal with the command ```python3 -m uvicorn WebPage.asgi:application --host 0.0.0.0 --reload```. 

**On a server without a graphical context, such as Code & Circuit's server, run** ```xvfb-run python3 -m uvicorn WebPage.asgi:application --host 0.0.0.0 --reload``` **for image stitching** (xvfb must be configured and set up).

The flag ```--host 0.0.0.0``` will allow the developer to access the client website from a separate device, and the flag ```--reload``` will allow the server to automatically reload when changes are made. This is good for testing changes without having to manually stop and restart the server. Running this command manually in the terminal will allow the developer to see all outputs from the server, as well as print information to the console and get feedback realtime (running the server as a service does not allow for realtime debugging with the console).

The other option is to connect to Spot's wifi (or connect Spot to wifi with internet), and run the server from the device being used to make changes. This is not much different from the first option and would require the changes to be pulled on the dedicated server, which would not be required if changes were made directly on the server.

For people on Code & Circuit Spot/Pro Team wanting to continue developing the server, contact me and I will give you permissions to make changes.

## TODO

Make a dedicated website explaining the server

### Important 
**in order of importance**:
1. Explain the best way to add to/continue developing the server
2. Add a complete description of what the server does, the features, how to use it, and how you could create your own frontend with it
3. Document the information returned from the get_state functions\

### General ToDos

- Rewrite connection.py (it's too complicated, code was hacked together from multiple sources)
- Create multiple walk commands if desired walking time exceeds the time allowed by the robot. If the desired time is too high, the robot says that the command is too far in the future
- Retry connection attempts if first attempt to robot failed
- Add ability to change the port 
- Add rate limiting for certain keyboard controls from client (stand/sit commands should only be sent once/second, etc.)
- Add more stuff to the config.json for more customizability
- Potentially add more logging info
