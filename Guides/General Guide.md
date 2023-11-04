## Prerequisites

- Ensure that Python3 is installed
- Ensure that Node is installed

## Setup 

1. Download Code & Circuit's [Spot Web Server](https://github.com/code-and-circuit/spot-web-server), instructions for this can be found [here](https://github.com/code-and-circuit/spot-web-server#installing-and-running).
	- Make sure to create the file `secrets.py` and enter the necessary constants for the robot.
	- Install the required python modules by running `pip3 install -r requirements.txt`
1. Download Code & Circuit's fork of the [Scratch VM](https://github.com/kaspesla/scratch-vm) and the [Scratch GUI](https://github.com/kaspesla/scratch-gui) and link them.
	- Run `npm install` inside of both repositories to install the required node modules
		- Since the repositories are not up-to-date with the current Scratch repositories, the flag `--legacy-peer-deps` will probably be necessary.
	- Ignore the instructions found in these repositories; refer to the [Linking Guide](https://github.com/scratchfoundation/scratch-gui/wiki/Getting-Started) to properly link the GUI with the VM.
		- Make sure that the VM and GUI repos are siblings of each other in their parent folder.
		- The flag `--legacy-peer-deps` may be needed for these commands as well.
2. Make sure the IP address that Scratch uses to connect to the Web Server is correct
	- Inside of the Scratch VM repository, go into the file `src/extensions/scratch3_spot/constants.js` and change the fields to match your setup.
	- If Scratch and the Web Server are running on the same device with default settings, these fields should not have to be changed. If they are running on different devices, change the IP address to be that of the device running the Web Server.

## Running

1. Run the Web Server, the Scratch GUI, and the Scratch VM according to their respective instructions ([Web Server](https://github.com/code-and-circuit/spot-web-server#installing-and-running), [Scratch](https://github.com/scratchfoundation/scratch-gui/wiki/Getting-Started#example-scratch-gui-vm-and-blocks-linked)).
	- On my device, when running the Scratch GUI and VM, I encountered an error related to OpenSSL that said `Error: error:0308010C:digital envelope routines::unsupported`. To fix this, I ran the command `export NODE_OPTIONS=--openssl-legacy-provider` inside of both terminals in which I was running the GUI and the VM. (found this on [Stack Overflow](https://stackoverflow.com/questions/69692842/error-message-error0308010cdigital-envelope-routinesunsupported?page=1&tab=scoredesc#tab-top))
2. Connect to the Web Server on port `8000` and the Scratch client on port `8601`.
3. Activate the Spot extension in Scratch.
	- View all extensions by clicking on the blue button with the "plus" symbol in the bottom left of the Scratch client.
	- Scroll down and click on the "Spot Control" extension. It will ask you to enter a name to be displayed on the Web Server's control panel.
4. Have fun!

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
