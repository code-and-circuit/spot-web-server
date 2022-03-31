var robot_mode = "Walk";
var toggled = false;
var valid_keys = ['q', 'e', 'w', 'a', 's', 'd', 'r', 'f', 'x', ' '];
var keys_pressed = {
    w: false,
    a: false,
    s: false,
    d: false,
    q: false,
    e: false,
    r: false,
    f: false,
    x: false,
    space: false
}
var refresh_rate = 0.2;

function toggle() {
    if (toggled) {
        toggled = false
        $("#toggle").html("keyboard control");
        $(".ctrl").css({"top": "-140px"});
    }
    else {
        toggled = true;
        $("#toggle").html("/\\");
        $(".ctrl").css({"top": "0"});
        $("#ctrl").focus();
    }
}

function getKey(e) {
    var evtobj = window.event? event : e;
    var unicode= evtobj.charCode? evtobj.charCode : evtobj.keyCode;
    var key_name = String.fromCharCode(unicode).toLowerCase()
    return key_name;
}

$("#ctrl").keypress(function (e) {
    
    $("#ctrl").val("");

    var key_pressed = getKey(e);
    if (key_pressed == " ") {
        $("#space").addClass("key-selected");
        return
    }
    else if (valid_keys.includes(key_pressed)) {
        $("#" + key_pressed).addClass("key-selected");
    }
    keys_pressed[key_pressed] = true;
});

$("#ctrl").keyup(function (e) {
    
    $("#ctrl").val("");

    var key_pressed = getKey(e);
    if (key_pressed == " ") {
        $("#space").removeClass("key-selected");
        robot_mode = robot_mode == "Walk" ? "Stand" : "Walk";
        $("#space").html(robot_mode + " Mode");
        keys_pressed['space'] = true
    }
    else if (valid_keys.includes(key_pressed)) {
        $("#" + key_pressed).removeClass("key-selected");
    }
    keys_pressed[key_pressed] = false;
});

var cmdLoop = null;

$("#ctrl").focus(function() {
    socket.send(JSON.stringify({
        action: 'keyboard_control_start'
    }));
    cmdLoop = setInterval(function() {
        var send_keys = false;
        for (var key in keys_pressed) {
            if (keys_pressed[key]) {
                send_keys = true;
                break;
            }
        }
            
        if (send_keys) {
            socket.send(JSON.stringify({
                action: 'key_press',
                keys_pressed: keys_pressed
            }));
            keys_pressed['space'] = false
        }
    }, refresh_rate * 1000);
});

$("#ctrl").focusout(function() {
    socket.send(JSON.stringify({
        action: 'keyboard_control_release'
    }))
    clearInterval(cmdLoop);
})