const output = document.getElementById("response-output");

function printOutput(content) {
    output.textContent = typeof content === "string" ? content : JSON.stringify(content, null, 2);
}

async function apiGet(url) {
    // TODO: centraliser ici les appels GET.
    const response = await fetch(url);
    return response.json();
}

async function apiPost(url, payload) {
    // TODO: centraliser ici les appels POST.
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
    });
    return response.json();
}

async function runGetExample() {
    // TODO: appeler une route GET de ton choix.
    printOutput({
        todo: "Remplis runGetExample() avec ta logique GET.",
    });
}

async function runPostExample() {
    // TODO: appeler une route POST de ton choix.
    printOutput({
        todo: "Remplis runPostExample() avec ta logique POST.",
    });
}

function bindEvents() {
    // TODO: brancher ici tes boutons / formulaires / listeners.
}

function main() {
    bindEvents();
}

main();
