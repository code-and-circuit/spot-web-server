// Creates a link used to connect the websocket. Necessary because the IP of the server may change based on what device
// is accessing it (localhost) or the network it is connected to
// This solution isn't great but it works. There's probably a better way to do it
var href =
    "ws" +
    window.location.href.substring(4, window.location.href.length - 1) +
    "/ws/";
socket = new WebSocket(href);
var socket_index = null;
var robot_is_estopped = false;

var selected_program = "";

var programs = [];

function showPrograms() {
    $(".program-list").html("");
        for (var program in programs) {
            $(".program-list").html(
                $(".program-list").html() +
                "<br><button id='program' onclick=displayProgram('" +
                program +
                "')>" +
                program +
                "</button>"
            );
        }
}

function getPrograms() {
    $.ajax({
        type: "GET",
        url: urls.get_program,
        data: {},
        success: function (response) {
            programs = response["programs"];
            showPrograms();
        },
        error: function (response) {
            addOutput("<red>Server error: " + response["status"] + ".</red>");
            // A 500 error is generally caused by the socket being closed when output tries to be sent back
            if (response["status"] == "500") {
                addOutput("Did the socket close? If so, try reloading.", true);
            }
        },
    });
}

function displayProgram(name) {
    selected_program = name;
    $("#program-name").html(selected_program);
    $("#program-info").html("");
    for (var c in programs[name]) {
        command = programs[name][c];
        var line = command["Command"] + "(";
        for (var arg in command["Args"]) {
            line += command["Args"][arg] + ", ";
        }
        if (line.substring(line.length - 1, line.length) != "(")
            line = line.substring(0, line.length - 2);
        line += ")<br>";
        $("#program-info").html($("#program-info").html() + line);
    }
}

// Function to get the cookie for sending some commands
// Not sure how it works, just copy and pasted it
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        var cookies = document.cookie.split(";");
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
// Needed for sending files
var csrftoken = getCookie("csrftoken");

// Handles socket messages from the server
socket.onmessage = function (message) {
    // Parses the JSON
    var data = JSON.parse(message["data"]);
    // If the message is indicating that a socket has been created, store the socket's index (more of an ID: see websocket.py)
    // for future use. Also sends a message back to ensure that the connected was successful
    if (data["type"] == "socket_create") {
        socket_index = data["socket_index"];
        addOutput(
            "Successfully connected to the server at <green>socket index " +
            socket_index +
            "</green>"
        );

    }
    // Updates the yellow text that tells whether or not the background process is running
    else if (data["type"] == "bg_process") {
        if (data["output"] == "start") {
            $("#isRunning").html("Background process is running");
            robot_is_estopped = false;
            $("#estop").html("Estop");
            $("#estop").css({
                "background-color": "rgb(255, 0, 0)",
                border: "none",
                cursor: "pointer",
            });
        } else $("#isRunning").html("Background process is not running");
    } else if (data["type"] == "estop") {
        if (data["output"] == "estop") {
            robot_is_estopped = true;
            $("#estop").html("Release Estop");
            $("#estop").css({
                "background-color": "rgb(0, 200, 0)",
                border: "none",
                cursor: "pointer",
            });
        } else {
            robot_is_estopped = false;
            $("#estop").html("Estop");
            $("#estop").css({
                "background-color": "rgb(255, 0, 0)",
                border: "none",
                cursor: "pointer",
            });
        }
    } else if (data["type"] == "programs") {
        $(".program-list").html("");
        programs = data["output"];
        showPrograms();
    } else if (data["type"][0] == "@") {
        var image = data["output"];
        var image_name = data["type"].substring(1, data["type"].length);
        $("#" + image_name).attr("src", "data:image/jpeg;base64," + image);
    } else if (data["type"] == "control_mode") {
        var mode = data["output"];
        $("#space").html(mode + " Mode");
    }
    else if (data["type"] == "battery-percentage") {
        var percentage = data["output"];
        $("#b_p").html(percentage + "%")
        var c = percentage > 60 ? 'var(--green)' : percentage > 20 ? 'orange' : 'var(--red)'
        $(".bar").css({
            'width': (percentage + "%"),
            'background-color': c
        })
    }
    else if (data["type"] == "battery-runtime") {
        var runtime = data["output"];
        $("#b_r").html(Math.round(runtime / 60) + " minutes")
    }

    // General output
    else if (data["type"] == "output") {
        addOutput(data["output"]);
    } else {
        addOutput("<red>Type not recognized: " + data["type"] + "</red>");
    }
};

// Socket closes when 1) the web page closes or is reloaded 2) the server reloads during development
// This command can be inconsistent, which is why extra code is needed in websocket.py
socket.onclose = function (message) {
    setTimeout(function () {
        addOutput(
            "<red>Socket " +
            socket_index +
            " has closed.<br> You should be seeing this only if the server is being worked on.</red>"
        );
    }, 500);
};

// Adds output to the client console and scrolls to the bottom. Text can be added to a new line or
// on the same line.
function addOutput(text, sameLine = false) {
    if (sameLine) {
        $("#output").html($("#output").html() + " " + text);
    } else {
        $("#output").html($("#output").html() + "<br>> " + text);
    }
    $("#output").scrollTop($("#output").scrollTop() + 100);
}

// Used for sending a request to the server
function sendRequest(url) {
    $.ajax({
        type: "GET",
        url: url,
        data: {
            // Socket index is sent so the server knows which socket to use for output
            socket_index: socket_index,
            selected_program: selected_program,
        },
        success: function (response) { },
        error: function (response) {
            addOutput("<red>Server error: " + response["status"] + ".</red>");
            // A 500 error is generally caused by the socket being closed when output tries to be sent back
            if (response["status"] == "500") {
                addOutput("Did the socket close? If so, try reloading.", true);
            }
        },
    });
}

$("#removeProgram").click(function () {
    sendRequest(urls.remove_program);
    getPrograms();
    $("#program-info").html("");
    $("#program-name").html("");
});

$("#estop").click(function () {
    if (robot_is_estopped) return sendRequest(urls.estop_release);
    if ($("#isRunning").html() == "Background process is running")
        sendRequest(urls.estop);
});

document.onkeypress = function (event) {
    event = event || window.event;
    if (event.keyCode == 123) {
        if (robot_is_estopped) return sendRequest(urls.estop_release);
        if ($("#isRunning").html() == "Background process is running")
            sendRequest(urls.estop);
    }
};

// Runs the program from a file
$("#runProgram").click(function () {
    sendRequest(urls.run_program);
});

// Starts the background process
$("#bgStart").click(function () {
    sendRequest(urls.start_process);
});

// Ends the background process
$("#bgEnd").click(function () {
    sendRequest(urls.end_process);
});

$("#connectRobot").click(function () {
    sendRequest(urls.connect);
});

$("#getEstop").click(function () {
    sendRequest(urls.get_estop);
});

$("#getLease").click(function () {
    sendRequest(urls.lease);
});

// Sends a message to the server letting it know that the socket is closing. This command is inconsistent
// and not always sent, requiring extra code in websocket.py
$(window).on("beforeunload", function () {
    socket.send(
        JSON.stringify({
            action: "unload",
        })
    );
});

getPrograms();
