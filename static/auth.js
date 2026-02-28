document.querySelectorAll("form").forEach(form => {
    form.addEventListener("submit", function (e) {
        let valid = true;
        const inputs = form.querySelectorAll("input");

        inputs.forEach(input => {
            input.classList.remove("error", "success");

            if (!input.value.trim()) {
                input.classList.add("error");
                valid = false;
            } else {
                input.classList.add("success");
            }
        });

        if (!valid) {
            e.preventDefault();
        }
    });
});
document.querySelectorAll("form").forEach(form => {
    form.addEventListener("submit", () => {
        const btn = form.querySelector("button");
        btn.classList.add("loading");
        btn.innerText = "";
    });
});
