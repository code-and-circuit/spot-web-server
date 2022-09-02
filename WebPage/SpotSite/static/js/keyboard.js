const valid_keys = ["q", "e", "w", "a", "s", "d", "r", "f", " ", "z", "x"];
const refresh_rate = 0.2;

const sitStandTimeoutMs = 1000;
const selfRightRollOverTimeoutMs = 5000;

const time_for_commands = {
    sit: 0,
    stand: 0,
    self_right: 0,
    roll_over: 0
}

let robot_mode = "Walk";
let toggled = false;
let keys_up = [];
let keys_down = [];
let cmdLoop = null;

/*
    Functions for handling keyboard input to control the robot
    - Only one client can control the robot at a time (managed by the server)
*/

function makeSureKeysArentPressedToMuch() {
    const current_time = Date.now();
    // console.log(current_time);
    if (keys_down.includes("r")) {
        if (current_time - time_for_commands.stand > sitStandTimeoutMs) {
            time_for_commands.stand = current_time;
            // console.log("Stand Sent!")
        }
        else {
            keys_down.splice(keys_down.indexOf("r"), 1);
        }
    }
    if (keys_down.includes("f")) {
        if (current_time - time_for_commands.sit > sitStandTimeoutMs) {
            time_for_commands.sit = current_time;
            // console.log("Sit Sent!")
        }
        else {
            keys_down.splice(keys_down.indexOf("f"), 1);
        }
    }
    if (keys_down.includes("z")) {
        if (current_time - time_for_commands.self_right > selfRightRollOverTimeoutMs) {
            time_for_commands.self_right = current_time;
            // console.log("Self Right Sent!")
        }
        else {
            keys_down.splice(keys_down.indexOf("z"), 1);
        }
    }
    if (keys_down.includes("x")) {
        if (current_time - time_for_commands.roll_over > selfRightRollOverTimeoutMs) {
            time_for_commands.roll_over = current_time;
            // console.log("Roll Over Sent!")
        }
        else {
            keys_down.splice(keys_down.indexOf("x"), 1);
        }
    }
}

// Toggles the keyboard control panel
function toggle() {
    if (toggled) {
        toggled = false;
        $("#toggle").html("keyboard control");
        $(".ctrl").css({ top: "-140px" });
    } else {
        toggled = true;
        $("#toggle").html("close");
        $(".ctrl").css({ top: "0" });
        $("#ctrl").focus();
    }
}

function getKey(e) {
    var evtobj = window.event ? event : e;
    var unicode = evtobj.charCode ? evtobj.charCode : evtobj.keyCode;
    var key_name = String.fromCharCode(unicode).toLowerCase();
    return key_name;
}

$("#ctrl").keypress((e) => {
    $("#ctrl").val("");

    let key_pressed = getKey(e);
    if (keys_down.includes(key_pressed)) return; // Don't handle keys already pressed
    if (key_pressed == " ") {
        $("#space").addClass("key-selected");
        key_pressed = "space";
    } else if (valid_keys.includes(key_pressed)) {
        $("#" + key_pressed).addClass("key-selected");
    }
    keys_down.push(key_pressed);
});

$("#ctrl").keyup((e) => {
    $("#ctrl").val("");

    let key_up = getKey(e);
    if (keys_up.includes(key_up)) return; // Make sure we aren't handling a keyup event twice
    if (key_up == " ") {
        $("#space").removeClass("key-selected");
        robot_mode = robot_mode == "Walk" ? "Stand" : "Walk";
        $("#space").html(robot_mode + " Mode");
        key_up = "space";
    } else if (valid_keys.includes(key_up)) {
        $("#" + key_up).removeClass("key-selected");
    }
    keys_up.push(key_up);
});


$("#ctrl").focus(() => {
    // Tell the server that keyboard control has started
    socket.send(
        JSON.stringify({
            action: "keyboard_control_start",
        })
    );
    cmdLoop = setInterval(function () {
        if (keys_down.length > 0 || keys_up.length > 0) {
            //makeSureKeysArentPressedToMuch();
            // Keyboard timeouts result in weird behavior (Should try to fix at some point)
            socket.send(
                JSON.stringify({
                    action: "keys",
                    keys_down: keys_down,
                    keys_up: keys_up,
                })
            );
            keys_up.forEach((key) => {
                if (keys_down.includes(key)) {
                    keys_down.splice(keys_down.indexOf(key), 1);
                }
            })
        }
        keys_up = [];
        //keys_down = [];
    }, refresh_rate * 1000);
});

$("#ctrl").focusout(() => {
    // Tell the server that keyboard control has ended
    socket.send(
        JSON.stringify({
            action: "keyboard_control_release",
        })
    );
    clearInterval(cmdLoop);
});
