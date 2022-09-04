# Code & Circuit's Spot Web Server
Created and maintained by Will Scheirey and the [Code & Circuit](https://codeandcircuit.org/) team

### Sections
- [Overview](https://github.com/code-and-circuit/spot-web-server#overview)
- [Querying and Websockets](https://github.com/code-and-circuit/spot-web-server#querying-and-websockets)
- [Installing and Running](https://github.com/code-and-circuit/spot-web-server#installing-and-running)
- [Developing](https://github.com/code-and-circuit/spot-web-server#developing)
- [Using the Server](https://github.com/code-and-circuit/spot-web-server#using-the-server)

## Overview

### Sections
- [Thesis](https://github.com/code-and-circuit/spot-web-server#thesis)
- [The Server](https://github.com/code-and-circuit/spot-web-server#code--circuits-spot-web-server-1)
- [Coding Spot](https://github.com/code-and-circuit/spot-web-server#coding-spot)
- [Making Custom Frontends](https://github.com/code-and-circuit/spot-web-server#making-custom-frontends)

### Thesis

Spot is an incredible tool for companies and organizations to use when they have specific purposes and missions for the robot to carry out and people with experience or knowledge using Spot, whether that be through the tablet or through the Spot SDK. The tools that are given to owners of Spot allow for many different uses of the robot, but do not very well support the use of Spot in a collaborative environemnt. Further, the Spot SDK is mainly only accessible to people with experience programming. This is completely fine and expected, as Boston Dynammics is more focused on creating robots, and allowing them to be used by people with experience in the field, than on teaching people how to program or learn how to use robots in general. 

A tool that would allow inexperienced people to control and program Spot would expand Spot's accessibility and outreach. It could not only be used by organizations with specific needs in mind, but as a teaching tool to allow students and inexperienced programmers to understand how robots work, and learn programming through controlling Spot. Many beginner programmers often get frustrated by a lack of results, and young programmers often do not see the use or potential in learning to program, as their results are often guided and/or not applicable in the real world. Learning to program using Spot, however, would give programmers immediate results and feedback, and allow them to get a better understanding of the potential of programming. With Spot being such an expensive robot and a household name, it could be a powerful tool to draw in people looking to get into programming. 

Being a single and very complicated robot, Spot, on its own, is not the best tool for many people to be programming at the same time. It is not made for a collaborative environment. Programmers must authenticate with and connect to Spot, connect and acquire each of Spot's services, and turn on Spot's motors each time they want to test and run a program. When the program is finished, they must wait for Spot's motors to turn off, and repeat the process to run a new program. When multiple people want to control Spot at the same time, such as in a classroom, this gets messy and there is much unecessary downtime betweeen when each person can run and test their program. A tool that would manage connections to the robot and allow programmers in a collaborative environment to control Spot without the need to worry about connecting, services, or turning on/off Spot's motors could create a much more streamlined process for people in such an environment to run their code.

With the right tools, Spot could be a vessel through which people learn to program and get involed in the field of programming and robotics in a collaborative environment.

### Code & Circuit's Spot Web Server

Code & Circuit's Spot Web Server was built with these ideas in mind. Not only does it provide a web interface for those wishing to control Spot without the tablet that comes with the robot, but it also provides the ability to control Spot using various forms of programming to suit a programmer's experience.

The web server is what connects to Spot and manages connections and services with the robot. A centralized place for such things to be managed means that people wishing to control Spot do not need to worry about them, but it also means that there is no downtime between when a program can be run. The server stays connected with Spot continuously so multiple programs can be run, edited, and rerun by multiple different people without ever having to turn Spot off or disconnect from the robot. Even for those wishing to code using the Spot SDK directly, the same is true.

The website connected to the server provides means to control Spot with the keyboard. These controls include basic motor controls in both stand mode and walk mode. Spot can also be self-righted and rolled over for battery change from the website. The website displays Spot's remaining battery percentage, as well as the estimated amount of remaining runtime. There is a live feed of Spot's front and back visual cameras. The views from the two front cameras are stitched together to make it easier to understand where Spot is. A realtime output console is also included for feedback relating to controlling Spot, as well as receiving potential errors when running code. 

### Coding Spot
There are three main ways to control Spot using Code & Circuit's Spot Web Server. Regardless of which way is chosen, any errors are caught and handled by the server as to prevent them from crashing the entire server when there is an error in the code. Errors and potential helpful feedback for them are displayed in the website's output console for easy debugging. 

The three ways to control Spot, in order from least to most complex are as follows
1. Scratch. A Scratch extension allows beginner programmers to control Spot without the need to manually write code. The Scratch extension communicates with the server and allows for bidirectional communication. Code & Circuit's fork of Scratch, and an overview of the extension, can be found [here](https://github.com/kaspesla/scratch-vm). Commands are sent one by one and executed by the server. 

2. Python Module. A python module allows intermediate programmers to control Spot by writing Python code. The module works similarly to the Scratch extension. Programs are packaged, sent to the server, and stored in a database, allowing them to be viewed and run at any time. This is especially useful in a classroom settings, where multiple students can write code and send it to the server at the same time. The module and an overview of it can be found [here](https://github.com/code-and-circuit/cc-python-spot-control).

3. Spot SDK. The Spot SDK can still be used to control Spot. The web server allows for files or entire folders to be uploaded and run. A filename and entry function name must be provided. Necessary services to control Spot can be imported from the existing server files so that Spot can be controlled without the need to register or connect new services. This allows more advanced programmers to still use the Spot SDK, but without the need to worry about connecting, authenticating, or registering basic services.

When commands are sent to the server from Scratch or the pre-packaged python scripts, they are added to a command queue. These commands are executed at the server's leisure. The commands in the queue are visible on the connected website. The website also provides the ability to not accept commands at all, to accept them and not run them, and to step through commands in the queue one-by-one. There are a variety of use cases for these options.

Programs that are packaged and sent from the Python module are saved to a database and can be viewed from the website. The website lists all programs and their names, and provides the ability to run the programs or delete them from the database. When a program is selected, it is displayed on the website so that the code can be reviewed before running.

Short overviews of using the Scratch extension and Python module from the connected website can be found [here](https://github.com/code-and-circuit/spot-web-server#using-the-scratch-extension).

Since the server accepts programs and commands through http requests, Spot could in theory be controlled by any language that supports making such requests. Video feed and some relevant information is provided through a websocket, so this information could be received and displayed using any language supporting websockets.

### Making Custom Frontends
Since the Spot Web Server operates using websockets and http requests, custom frontends can be made to display all existing information. The server can be queried for information, which can then be displayed on custom websites. The server will also periodically send some information through connected websockets, which allows for the website to be updated realtime without the need to reload. Information that can be queried for and is sent through websockets is specified in the next section.

## Querying and Websockets
*insert information*

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

# Using the Server
### Sections
- [Connecting and Main Panel](https://github.com/code-and-circuit/spot-web-server#connecting-and-main-panel)
- [Keyboard Controls](https://github.com/code-and-circuit/spot-web-server#keyboard-controls)
- [Programs and Commands](https://github.com/code-and-circuit/spot-web-server#programs-and-commands)
- [Using the Scratch Extension](https://github.com/code-and-circuit/spot-web-server#using-the-scratch-extension)
- [Python Programs](https://github.com/code-and-circuit/spot-web-server#python-programs)
## Connecting and Main Panel
To connect the server to the robot, press “Connect to Robot”. This will start the live video feed, as well as show the battery with the number of minutes remaining

To acquire the estop, press “Acquire Estop”. This will give you the ability to use the emergency stop. The robot can be emergency stopped by pressing “ESTOP” (button only shows up when the estop has been acquired).

To acquire a lease, press “Acquire Lease”. This will give the server the ability to send mobility commands to control Spot’s movement. If another device already has a lease (like the remote controller), the website will tell you that another device already has a lease. To fix this, return the lease on the device that has it (to do this on the controller, open the Spot app, press on the power icon in the top middle, and choose “give up control” ).

Pressing “Start Main Loop” will do all three previous actions for you, as well as turn on Spot’s motors and enable the ability for mobility commands to be sent to Spot (such as from Scratch). This button must be pressed in order to send such commands.

Pressing “Stop Main Loop” will turn off Spot’s motors and disconnect all services. It’s a good idea to do this before physically turning off the robot, if the server is connected to the robot. 

The 3 services (Robot Connection, Estop, Lease) can each be manually released by pressing their corresponding “Clear” button (only available once the service has been acquired).

### Keyboard Controls
The robot can be controlled with the keyboard once “Start Main Loop” has been pressed and the robot has successfully turned on. To access keyboard controls, click on “keyboard control” in the top left. 

Keyboard controls will only be sent if the keyboard control box is selected (denoted by the yellow border around it). You can click outside of this box to deselect in and click inside of it to select it again.

## Keys
- ```space``` toggle between Stand Mode(for rotating the body while standing) and Walk Mode(for moving Spot).

- ```r``` stand up
- ```f``` sit down
- ```z``` self right (if Spot has fallen over or is otherwise not in his sitting position)
- ```x``` roll over (for changing the battery)

### Stand Mode
- ```w``` rotate pitch towards the ground
- ```s``` rotate pitch away from the ground
- ```a``` rotate yaw to the left
- ```d``` rotate yaw to the right
- ```q``` rotate roll counterclockwise
- ```e``` rotate roll clockwise
		
### Walk Mode
- ```w``` walk forwards
- ```s``` walk backwards
- ```a``` strafe left
- ```d``` strafe right
- ```q``` turn counterclockwise
- ```e``` turn clockwise


## Programs and Commands
Once “Start Main Loop” has been pressed, commands from Scratch can be sent to Spot. By default, all commands coming from Scratch will be accepted and immediately run, but this can be changed.

Whether or not the server is accepting commands from Scratch can be toggled by pressing on the box to the left of “Accept commands”.

Whether or not the server will immediately run commands from Scratch can be toggled by pressing on the box to the left of “Run commands”. 

When commands are accepted from Scratch, they are added to a queue of commands to run. When the server immediately runs commands, this queue is generally kept empty. If commands are not immediately run, they will still be added to the queue. The queue will show up in the second box from the left (after the Programs and Commands header). 

If there are commands in the queue that you want to step through one by one, you can press “step command”. This will run the command at the top of the queue, remove it from the queue, and then wait for the next action. 

If there are commands in the queue and “Run commands” is toggled on, the commands will be immediately executed.

If you want to clear the commands in the queue, press “Clear Command Queue” at the top of the screen.

## Using The Scratch Extension

Video feed is enabled by default and will be shown in the stage. There are Scratch blocks inside of the Spot extension to disable and enable the video feed. 

All Scratch blocks and what they do should be fairly intuitive. Blocks telling Spot to walk will force the program to wait for 1 second to prevent commands from being sent too quickly. Blocks telling Spot to rotate his body in a specific way do not force the program to wait, to “wait” block (in the “control” section) must be used to force the program to wait.

Any errors with commands sent to Spot from Scratch will be outputted on the server website. An example of this would be telling Spot to move forward, but leaving the amount blank. This will not crash anything, but it will show up on the website so you can know what went wrong. 

At the moment, the server does not differentiate what computer is sending Scratch commands, so it is important that only one computer sends them at a time. If multiple computers send commands at a time, they may build up in the queue and Spot may execute commands well after they stop being sent. You can always press “ESTOP”, or toggle off accepting commands and clear the queue if this happens.

## Python Programs
There is a python module for sending programs to Scratch that can be found in Code & Circuit’s organization on Github. There are example programs that should outline how to use it.

When programs are sent, they are saved to a database on the server and can be chosen, viewed, run, or deleted, in the two panels on the right side of the screen under the header “Programs and Commands”.

# TODO

Make a dedicated website explaining the server

## Important 
### in order of importance:
1. Add a complete description of what the server does, the features, how to use it, and how you could create your own frontend with it
2. Document the information returned from the get_state functions\

## General ToDos

- Rewrite connection.py (it's too complicated, code was hacked together from multiple sources)
- Create multiple walk commands if desired walking time exceeds the time allowed by the robot. If the desired time is too high, the robot says that the command is too far in the future
- Retry connection attempts if first attempt to robot failed
- Add ability to change the port 
- Add rate limiting for certain keyboard controls from client (stand/sit commands should only be sent once/second, etc.)
- Add more stuff to the config.json for more customizability
- Potentially add more logging info




