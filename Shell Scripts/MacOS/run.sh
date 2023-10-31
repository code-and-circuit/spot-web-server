osascript -e 'tell app "Terminal"
    do script "cd ~/Documents/Github/scratch-vm && export NODE_OPTIONS=--openssl-legacy-provider && npm run watch"
end tell'

osascript -e 'tell app "Terminal"
    do script "cd ~/Documents/Github/scratch-gui && export NODE_OPTIONS=--openssl-legacy-provider && npm start"
end tell'

osascript -e 'tell app "Terminal"
    do script "cd ~/Documents/Github/spot-web-server/WebPage && python3 -m uvicorn WebPage.asgi:application --host 0.0.0.0 --reload"
end tell'
