const alertDiv = document.getElementsByClassName("alerts")[0];

function isElementInViewport (el) {
    var rect = el[0].getBoundingClientRect();

    return (
        rect.top >= -rect.height/2 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) + rect.height/2 &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

function runAlert(text) {
    // if (isElementInViewport($("#output"))) return;
    const p = document.createElement("p");
    p.className = "alert"
    p.innerHTML = text;

    alertDiv.appendChild(p);
    setTimeout(() => {
        p.style.opacity = "0";
    }, 3000)
    setTimeout(() => {
        alertDiv.removeChild(p);
    }, 3500);
}

$(".alert").click(() => {
    const ht = $(".alerts").height()
    console.log(ht);
    $([document.documentElement, document.body]).animate({
        scrollTop: $(".output").offset().top - ht - 5
    }, 500);
})