(function () {
    const el = document.getElementById("form-error");
    if (!el) return;
    const code = new URLSearchParams(window.location.search).get("error");
    const msg = code ? el.dataset[code] : "";
    if (!msg) return;
    el.textContent = msg;
    el.hidden = false;
})();
