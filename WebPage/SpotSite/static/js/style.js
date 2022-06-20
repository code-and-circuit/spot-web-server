function resize_div(div_name, ratio=2/3) {
    var div = $("." + div_name);
    var width = div.width();

    //div.css("height", width * ratio);
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