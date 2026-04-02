function initSeriesPage() {
  const app = window.GenFlixApp || {};
  const setBodyWaiting = app.setBodyWaiting || (() => {});
  const seriesForm = document.querySelector(".series-form");

  if (seriesForm) {
    const ratingButtons = Array.from(seriesForm.querySelectorAll(".series-actions button[name='opinion']"));

    function setButtonsDisabled(disabled) {
      ratingButtons.forEach((button) => {
        button.disabled = disabled;
      });
    }

    function setActiveOpinion(opinionValue) {
      ratingButtons.forEach((button) => {
        button.classList.toggle("active", button.value === opinionValue);
      });
    }

    seriesForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const clickedButton = event.submitter;
      if (clickedButton && clickedButton.value) {
        setButtonsDisabled(true);
        setBodyWaiting(true);

        try {
          const response = await fetch(seriesForm.dataset.apiUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              serie_id: seriesForm.dataset.serieId,
              opinion: clickedButton.value,
            }),
          });

          const data = await response.json().catch(() => ({}));
          if (!response.ok) {
            throw new Error(data.error || "Erreur.");
          }

          setActiveOpinion(clickedButton.value);
        } catch (_error) {
          console.error("Erreur lors de la sauvegarde de l'opinion :", _error);
        } finally {
          setButtonsDisabled(false);
          setBodyWaiting(false);
        }
      }
    });
  }
}
