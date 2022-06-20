/*
    Used to set the height of the video feed divs
    - Aspect ratio should be fixed, no easy way to do with css
*/
function resize_div(div_name, ratio=2/3) {
    const div = $("." + div_name);

    div.css("height", div.width() * ratio);
}

function resize_divs() {
    resize_div("front");
    resize_div("back");

    resize_div("video-feed", 0.8);
}

$(window).resize(function() {
    resize_divs();
});

$(document).ready(function() {
    resize_divs();
});