var robot_mode = "Walk";
var toggled = false;
var valid_keys = ['q', 'e', 'w', 'a', 's', 'd', 'r', 'f', ' '];
var keys_up = []
var keys_down = []
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
    if (keys_down.includes(key_pressed))
        return
    if (key_pressed == " ") {
        $("#space").addClass("key-selected");
        key_pressed = "space"
    }
    else if (valid_keys.includes(key_pressed)) {
        $("#" + key_pressed).addClass("key-selected");
    }
    keys_down.push(key_pressed)
});

$("#ctrl").keyup(function (e) {
    
    $("#ctrl").val("");

    var key_up = getKey(e);
    if (key_up == " ") {
        $("#space").removeClass("key-selected");
        robot_mode = robot_mode == "Walk" ? "Stand" : "Walk";
        $("#space").html(robot_mode + " Mode");
        key_up = 'space'
    }
    else if (valid_keys.includes(key_up)) {
        $("#" + key_up).removeClass("key-selected");
    }
    keys_up.push(key_up)
});

var cmdLoop = null;

$("#ctrl").focus(function() {
    socket.send(JSON.stringify({
        action: 'keyboard_control_start'
    }));
    cmdLoop = setInterval(function() {
        if (keys_down.length > 0 || keys_up.length > 0) {
            socket.send(JSON.stringify({
                action: 'keys',
                keys_down: keys_down,
                keys_up: keys_up
            }));
        }
        keys_up = []
        keys_down = []
    }, refresh_rate * 1000);
});

$("#ctrl").focusout(function() {
    socket.send(JSON.stringify({
        action: 'keyboard_control_release'
    }))
    clearInterval(cmdLoop);
})