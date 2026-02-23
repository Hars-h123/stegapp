function toggleTheme() {
    const body = document.getElementById("main-body");

    if (body.classList.contains("cyber")) {
        body.classList.remove("cyber");
        body.classList.add("saas");
        localStorage.setItem("theme", "saas");
    } else {
        body.classList.remove("saas");
        body.classList.add("cyber");
        localStorage.setItem("theme", "cyber");
    }
}

window.onload = function () {
    const savedTheme = localStorage.getItem("theme") || "saas";
    const body = document.getElementById("main-body");
    body.classList.add(savedTheme);
};