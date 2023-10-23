## Prerequisites

1. Install [Python](https://www.python.org/downloads/).
	- Insure that pip is install by running `pip3 --version` from the terminal.
2. Install [Node](https://nodejs.org/en/download).
3. Install [GitHub Desktop](https://desktop.github.com/). This will install Git as well.
	- Alternatively, you can install Git from [git-scm.com](https://git-scm.com/downloads) and run commands from the terminal if you wish to do so.

Follow this step-by-step guide, or run the shell scripts. Instructions for this are as follows:
1. Locate the files in Finder.
2. Open the Terminal app.
3. Type `sh ` (make sure to include a single space after the "sh").
4. Drag and drop `install.sh` into the Terminal window and press "enter". If it asks for your password, enter your password and press "enter".
5. The installation may take some time, but when it is done, it should open up a file called `secrets.py` in which you can specify necessary information. Make sure to save your changes.
6. Type `sh ` into the Terminal again. Drag and drop `run.sh` into the Terminal window and press "enter". After a minute or so, everything should be running. You can access the Web Server at the url `localhost:8000` and Scratch at `localhost:8601`.

## Step-By-Step Setup

### Clone the Repositories
1. Clone Code & Circuit's Spot Web Server
	- Open GitHub Desktop and go through the (short) onboarding process.
	- Click on "Add Repository" and choose to clone from a URL. The "Add Repository" button may be under the "Current Repository" section (the button in the top left).
	- Paste in this url: https://github.com/code-and-circuit/spot-web-server.git.
	- I recommend cloning the repository into a folder called GitHub inside of your local Documents folder. The path to my GitHub folder looks like this: `/Users/will/Documents/GitHub`. (This is the "Local Path" field in the cloning interface).
	- Click "Clone" to download the code.
2.  Clone Code & Circuit's forks of the Scratch GUI and the Scratch VM.
	1. Clone the Scratch GUI.
		- Open GitHub Desktop and choose to add a new repository by cloning from a URL. The "Add Repository" button may be under the "Current Repository" section (the button in the top left).
		- Paste in this url: https://github.com/kaspesla/scratch-gui.git.
		- Choose a value for the "Local Path" field, I would recommend using the same value that you used for the previous step (this value should be saved for you by GitHub Desktop).
		- Click "Clone".
	2. Clone the Scratch VM.
		- Repeat the previous step for cloning the Scratch GUI, but use this url instead: https://github.com/kaspesla/scratch-vm.git.
		- Make sure that the "Local Path" field matches the field for the Scratch GUI. **This is important**. While the Web Server does not have to be in the same parent folder as the Scratch repositories, the Scratch repositories **must** be siblings of each other in their parent directory.

### Run the Web Server
1. Open the Web Server repository in GitHub Desktop by clicking on the "Current Repository" button in the top left and choosing `spot-web-server` from the list.
2. Install python modules.
	- From the menu on the top bar of your window/screen in GitHub Desktop, choose `Repository > Open in Terminal`.
	- Type `pip3 install -r WebPage/requirements.txt` to install the python modules.
	- Keep this window open, you will use it in Step 4.
3. Create `secrets.py` and enter in the required constants
	- From the menu on the top bar of your window/screen in GitHub Desktop, choose `Repository > Show in Finder`.
	- Navigate to spot-web-server/WebPage/SpotSite.
	- Create a file called `secrets.py` and enter in the required information (you can copy and paste this, but replace `[YOUR SPOT USERNAME]`, `[YOUR SPOT PASSWORD]`, and `[YOUR ROBOT IP]` with the values that match your setup) :
```python
ROBOT_USERNAME = "[YOUR SPOT USERNAME]"

ROBOT_PASSWORD = "[YOUR SPOT PASSWORD]"

SECRET_KEY = "dummy-secret-key" # This does not have to be changed

ROBOT_IP = "[YOUR ROBOT IP]"
```
4. Start up the server
	- Using the terminal that you opened in Step 2, run the command 
``` sh
cd WebPage && python3 -m uvicorn WebPage.asgi:application --host 0.0.0.0
```
5. You should see something that says `INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)`. This means that the server is running!

### Install Node Modules and Link Scratch
1. Install node modules for the Scratch GUI and the Scratch VM
	- Open the Scratch GUI repository in GitHub Desktop by clicking on the "Current Repository" button in the top left and choosing `scratch-gui` from the list.
	- From the menu on the top bar of your window/screen in GitHub Desktop, choose `Repository > Open in Terminal`.
	- Run the command `npm install --legacy-peer-deps` to install the node modules.
	- Once the modules have finished, keep the terminal open for linking (next step).
	- Repeat this process for the Scratch VM as well, you should have two terminals open at this point.
2. Link the Scratch GUI with the Scratch VM.
	- Open the terminal for the **Scratch VM**. Enter the command `sudo npm link --legacy-peer-deps`. This will prompt you to enter your password in the terminal in order to complete the command.
	- Open the terminal for the **Scratch GUI**. Enter the command `sudo npm link scratch-vm --legacy-peer-deps`. Enter your password again.
	- Keep these terminals open for the next step

### Run the Scratch VM and the Scratch GUI
1. Start the Scratch VM
	- Open the terminal for the **Scratch VM** and run the command 
```sh
export NODE_OPTIONS=--openssl-legacy-provider
 && npm run watch
``` 
2. Start the Scratch GUI
	- Open the terminal for the **Scratch VM** and run the command 
```sh
export NODE_OPTIONS=--openssl-legacy-provider
 && npm start
``` 

At this point, you should have three terminals open. One should be running the Web Server, one should be running the Scratch VM, and one should be running the Scratch GUI.

If at any point the Web Server malfunctions or is otherwise unusable, you can quit it by opening the terminal in which it is running and pressing `ctrl + c`. If for some reason this fails, press `ctrl + z` to force quit. You can also simply close the terminal in which it is running (this isn't "best practice", but it doesn't matter). To start the server again, open the repository in the terminal from GitHub Desktop and run this command:
```sh
cd WebPage && python3 -m uvicorn WebPage.asgi:application --host 0.0.0.0
```
### Use Spot!
1. Open the Web Server's interface at the url `localhost:8000`. Click "Start All" to connect to the robot and turn it on
2. Open Scratch at the url `localhost:8601`.  Click on the blue button in the bottom left with the "plus" icon to view extensions and click on the Spot extension. 

If Scratch asks for your name, it means everything on the Scratch side is working! You can use the block `enable video feed` to get a live video feed from Spot (if it does not come on automatically). If this works, it means that both Spot and Scratch are connected to the Web Server! 

## Notes on Running

- You can access the robot's front camera through the block titled `enable video feed`.
- Some commands require a `wait` block in order to allow the robot to finish the current command before moving onto the next one. Others blocks, like walking, have built-in waits to prevent the user from overloading the server with blocking commands.
- A few choreography moves are included in the Scratch extension.
- Units are in meters and degrees, except for the `set height` block, which uses a range from `-1` to `1`.
- Collision avoidance is enabled when sending commands through the Scratch extension.
-  The "jog" and "hop" walk modes are currently disabled from the Scratch client due to them causing the robot to continue jogging/hopping for many seconds after reaching it's target.

## Additional notes

- Instructions on how to use the Web Server's interface can be found [here](https://github.com/code-and-circuit/spot-web-server#using-the-server)
- Make sure that the server is running before connecting to the Scratch client. If the Scratch client is opened before the server is running or the server restarts while the Scratch client is open, reload the Scratch client to ensure that it is connected to the server.
- By default, the server should automatically accept Scratch commands from the first Scratch client that connects. You can see which Scratch clients are connected and whether the server is accepting commands under the "Programs and Commands" heading on the server's control panel.
- Currently the server cannot handle a situation in which the connected robot's lease is "hijacked" - if this happens the server will crash. If this does happen, simply restart the server.
- There are certain robot states that the server currently cannot handle, such as some behavior faults. To fix this, try disconnecting and reconnecting to the robot from the server's interface, or use a different program to clear the behavior fault.
- The server should output any errors in the interface's "console". Hopefully the error messages are informative enough, but the full error is also logged in the device console from which the server is run.
- In the event that the server malfunctions or is otherwise unusable (we have not had the ability to test and/or fix every scenario), shutting it down and restarting the server should fix any issues. Make sure to reload the Scratch client if this happens in order for it to reconnect to the server.