function initAuthForm() {
  const authForm = document.querySelector("#auth-form");
  const authMessage = document.querySelector("#auth-message");

  if (authForm && authMessage) {
    authForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const formData = new FormData(authForm);
      const payload = {
        username: String(formData.get("username") || "").trim(),
        password: String(formData.get("password") || "").trim(),
      };

      authMessage.textContent = "";

      console.log("Envoi du formulaire d'authentification avec les données :", payload);

      try {
        const response = await fetch(authForm.dataset.apiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        const data = await response.json();

        if (response.ok) {
          window.location.href = data.redirect || authForm.dataset.redirectUrl || "/";
        } else {
          authMessage.textContent = data.error || "Erreur.";
        }
      } catch (_error) {
        authMessage.textContent = "Erreur reseau.";
        console.error("Erreur réseau lors de l'envoi du formulaire d'authentification :", _error);
      }
    });
  }
}
