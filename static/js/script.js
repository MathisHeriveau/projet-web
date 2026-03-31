const items = document.querySelectorAll(".carrousel-item");
const prevButtons = document.querySelectorAll(".carrousel-control.prev");
const nextButtons = document.querySelectorAll(".carrousel-control.next");
const bullets = document.querySelectorAll(".bullet span");
const authForm = document.querySelector("#auth-form");
const authMessage = document.querySelector("#auth-message");

let currentIndex = 0;

function updateCarousel() {
  items.forEach((item, index) => {
    item.classList.toggle("active", index === currentIndex);
  });

  bullets.forEach((bullet, index) => {
    bullet.classList.toggle("active", index === currentIndex);
  });
}

prevButtons.forEach((button) => {
  button.addEventListener("click", () => {
    currentIndex = (currentIndex - 1 + items.length) % items.length;
    updateCarousel();
  });
});

nextButtons.forEach((button) => {
  button.addEventListener("click", () => {
    currentIndex = (currentIndex + 1) % items.length;
    updateCarousel();
  });
});

updateCarousel();

if (authForm) {
  authForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(authForm);
    const payload = {
      username: String(formData.get("username") || "").trim(),
      password: String(formData.get("password") || "").trim(),
    };

    authMessage.textContent = "";

    try {
      const response = await fetch(authForm.dataset.apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        authMessage.textContent = data.error || "Erreur.";
        return;
      }

      window.location.href = data.redirect || authForm.dataset.redirectUrl || "/";
    } catch (_error) {
      authMessage.textContent = "Erreur reseau.";
    }
  });
}
