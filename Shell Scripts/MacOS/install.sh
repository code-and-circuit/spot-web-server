# GitHub directory
mkdir ~/Documents/GitHub && cd ~/Documents/GitHub

# Web Server
git clone https://github.com/code-and-circuit/spot-web-server.git

touch spot-web-server/WebPage/SpotSite/secrets.py
echo "ROBOT_USERNAME = \"[YOUR SPOT USERNAME]\"
ROBOT_PASSWORD = \"[YOUR SPOT PASSWORD]\"
SECRET_KEY = \"dummy secret key\" # This does not have to be changed
ROBOT_IP = \"[ROBOT_IP]\"" > spot-web-server/WebPage/SpotSite/secrets.py

pip3 install -r spot-web-server/WebPage/requirements.txt

# Clone Scratch
git clone https://github.com/kaspesla/scratch-gui.git
git clone https://github.com/kaspesla/scratch-vm.git

# Node Stuff
cd scratch-vm
npm install --legacy-peer-deps
sudo npm link --legacy-peer-deps

cd ../scratch-gui
npm install --legacy-peer-deps
sudo npm link scratch-vm --legacy-peer-deps

# Open files to write constants
cd ..
open -e spot-web-server/WebPage/SpotSite/secrets.py
