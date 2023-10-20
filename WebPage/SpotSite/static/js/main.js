// Creates a url used to connect the websocket. 
// - IP of the server may change, so it cannot be static
// - example: ws://localhost:8000/ws/
const href =
    "ws://" +
    window.location.hostname +
    ":8000/ws/"
let socket;

// Make sure that the socket connection was successful, and tell the client if it was not
try {
    socket = new WebSocket(href);
} catch (err) {
    addOutput("<red>Error connecting to the server</red>");
}

let socket_index = null;
let robot_is_estopped = false;

// Handles socket messages from the server
socket.onmessage = (message) => {
    // Parses the JSON
    const data = JSON.parse(message["data"]);

    // Ensures that the socket connection was successful and stores its index for future use
    if (data["type"] == "socket_create") {
        socket_index = data["socket_index"];
        addOutput(
            "Successfully connected to the server at <green>socket index " + socket_index + "</green>"
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
        }
        else
            $("#isRunning").html("Background process is not running");
    }
    // Updates the estop button. Useful if multiple clients are active
    else if (data["type"] == "estop") {
        if (data["output"] == "estop") {
            robot_is_estopped = true;
            $("#estop").html("Release Estop");
            $("#estop").css({
                "background-color": "rgb(0, 200, 0)",
                border: "none",
                cursor: "pointer",
            });
        }
        else {
            robot_is_estopped = false;
            $("#estop").html("Estop");
            $("#estop").css({
                "background-color": "rgb(255, 0, 0)",
                border: "none",
                cursor: "pointer",
            });
        }
    }
    // Handles the message containing the program list
    else if (data["type"] == "programs") {
        $(".program-list").html("");
        program_handler.programs = data["output"];
        program_handler.show_programs();
    }
    // Handles video feed, the prefix @ specifies that the message is an image in the video feed
    else if (data["type"][0] == "@") {
        const image = data["output"];
        const image_name = data["type"].substring(1, data["type"].length);
        $("#" + image_name).attr("src", "data:image/jpeg;base64," + image);
    }
    // Updates the keyboard control mode (Walk/Stand)
    else if (data["type"] == "control_mode") {
        const mode = data["output"];
        $("#space").html(mode + " Mode");
    }
    // Updates the battery percentage
    else if (data["type"] == "battery_percentage") {
        const percentage = data["output"];
        $("#b_p").html(percentage + "%");
        // Specifies the color of the battery icon
        const c = percentage > 50 ? 'var(--green)' : percentage > 20 ? 'orange' : 'var(--red)';
        $(".bar").css({
            'width': (percentage + "%"),
            'background-color': c
        })
    }
    // Updates the battery runtime
    else if (data["type"] == "battery_runtime") {
        const runtime = data["output"];
        const runtime_minutes = Math.round(runtime / 60); // Runtime is given in seconds, convert to minutes
        $("#b_r").html(runtime_minutes + " minutes");
    }
    // Updates whether the server is accepting commands or not
    else if (data["type"] == "toggle_accept_command") {
        const is_accepting_commands = data["output"];
        if (is_accepting_commands) {
            $("#toggle-accept-command-button").addClass("option-true");
        }
        else {
            $("#toggle-accept-command-button").removeClass("option-true");
        }
    }
    // Updates whether the robot is connected, and which action can be taken as a result
    else if (data["type"] == "robot_toggle") {
        const state = data["output"];

        if (state == "clear")
            $("#connectRobot").html("Connect to Robot")
        else
            $("#connectRobot").html("Disconnect Robot")
    }
    // Updates whether the estop is accquired, and which action can be taken as a result
    else if (data["type"] == "estop_toggle") {
        const state = data["output"];

        if (state == "clear")
            $("#getEstop").html("Acquire Estop")
        else
            $("#getEstop").html("Clear Estop")
    }
    // Updates whether the lease is accquired, and which action can be taken as a result
    else if (data["type"] == "lease_toggle") {
        const state = data["output"];

        if (state == "clear")
            $("#getLease").html("Acquire Lease")
        else
            $("#getLease").html("Clear Lease")
    }
    else if (data["type"] == "toggle_auto_run") {
        const will_auto_run = data["output"];

        if (will_auto_run) {
            $("#toggle-auto-run-commands").addClass("option-true");
        }
        else {
            $("#toggle-auto-run-commands").removeClass("option-true");
        }
    }
    // General output
    else if (data["type"] == "output") {
        addOutput(data["output"]);
    }
    else if (data["type"] == "command_queue") {
        const command_queue = JSON.parse(data["output"]);
        const command_queue_div = $("#command-queue");
        command_queue_div.html("");
        command_queue.forEach(command => {
            command_queue_div.html(command_queue_div.html() + program_handler.display_command(command));
        })
    }
    else if (data["type"] == "client-list") {
        update_client_list(data["output"]);
        
    }

    else if (data["type"] == "scratch_clients") {
        update_client_list(data["output"][0]);
        const scratch_controller = data["output"][1];
        if (scratch_controller[1] == "-1")
            scratch_controller[0] = "No One"
        else
            document.querySelector("#ip-" + scratch_controller[1].replaceAll(".", "-")).classList.add("chosen");
        document.querySelector("#scratch-controller-name").innerHTML = scratch_controller[0];
    }

    // Handles unknown output types (should not happen, just for safetey and potential debugging) 
    else {
        addOutput("<red>Type not recognized: " + data["type"] + "</red>");
    }
};

/*
Lets the client know when the socket has closed
- Displays after a delay because simply reloading the page, and there is
    no reason to flash an error message on a reload
- This should only be seen if the webpage is open while the server is under development
*/
socket.onclose = (message) => {
    setTimeout(() => {
        addOutput(
            "<red>Socket " +
            socket_index +
            " has closed.<br> You should be seeing this only if the server is being worked on.</red>"
        );
    }, 1000);
};

// Adds output to the client console and scrolls to the bottom. Text can be added to a new line or
// on the same line.
function addOutput(text, sameLine = false) {
    runAlert(text);
    if (sameLine) {
        $("#output").html($("#output").html() + " " + text);
    } else {
        $("#output").html($("#output").html() + "<br>> " + text);
    }
    $(".output").scrollTop($(".output").scrollTop() + 100);
}

// Utility function for sending a request to the server
function sendRequest(url, type = "GET") {
    $.ajax({
        type: type,
        url: url,
        data: {
            // Socket index is sent so the server knows which socket to use for output
            socket_index: socket_index,
            selected_program: program_handler.selected_program,
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

$("#removeProgram").click(() => {
    sendRequest(urls.remove_program);
    program_handler.get_programs();
    $("#program-info").html("");
    $("#program-name").html("");
});

$("#estop").click(() => {
    if (robot_is_estopped) return sendRequest(urls.estop_release);
    if ($("#isRunning").html() == "Background process is running")
        sendRequest(urls.estop);
});

$("#stop-program").click(() => {
    sendRequest(urls.clear_queue);
});

$('#toggle-accept-command-button').click(() => {
    sendRequest(urls.toggle_accept_command);
});

$("#toggle-auto-run-commands").click(() => {
    sendRequest(urls.toggle_auto_run_commands);
})

$("#runProgram").click(() => {
    sendRequest(urls.run_program);
});

$("#step-command").click(() => {
    sendRequest(urls.step_command);
})

$("#bgStart").click(() => {
    sendRequest(urls.start_process);
});

$("#bgEnd").click(() => {
    sendRequest(urls.end_process);
});

$("#connectRobot").click(() => {
    if ($("#connectRobot").html() == "Connect to Robot")
        sendRequest(urls.connect);
    else
        sendRequest(urls.disconnect_robot)
});

$("#getEstop").click(() => {
    if ($("#getEstop").html() == "Acquire Estop")
        sendRequest(urls.get_estop);
    else
        sendRequest(urls.clear_estop)
});

$("#getLease").click(() => {
    if ($("#getLease").html() == "Acquire Lease")
        sendRequest(urls.lease);
    else
        sendRequest(urls.clear_lease)
});

$("#execute-file").click(() => {
    sendRequest(urls.execute_file);
});


$(".client_name").click((e) => {
    console.log(e.target);
})

// Sends a message to the server letting it know that the socket is closing
/*
$(window).on("beforeunload", () => {
    try {
        socket.send(
            JSON.stringify({
                action: "unload",
            })
        );
    }
    catch(err) {
        console.log(err);
    }
});
*/