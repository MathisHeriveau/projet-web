function initGenAccount() {
  const app = window.GenFlixApp || {};
  const setBodyWaiting = app.setBodyWaiting || (() => {});
  const list = document.querySelector(".gen-account-card-list");

  if (list) {
    const searchForm = document.querySelector("#gen-account-search-form");
    const searchInput = document.querySelector("#gen-account-search-input");
    const selectionCount = document.querySelector("#gen-account-selection-count");
    const accountContinueButton = document.querySelector("#gen-account-continue-button");
    const initialShowsScript = document.querySelector("#gen-account-initial-shows");
    const fallbackImage = list.dataset.fallbackImage || "/static/images/no-image-blog.jpg";

    const selectedShows = new Map();
    let selectedShowsPayload = [];
    let initialShows = [];

    if (initialShowsScript) {
      try {
        initialShows = JSON.parse(initialShowsScript.textContent || "[]");
      } catch (_error) {
        initialShows = [];
      }
    }

    function getShowId(show) {
      return String(show?.id ?? show?.title ?? show?.name ?? "");
    }

    function getShowImage(show) {
      return show?.image?.original || show?.image?.medium || fallbackImage;
    }

    function getShowTitle(show) {
      return String(show?.title || show?.name || "Serie sans nom").trim() || "Serie sans nom";
    }

    function getShowGenres(show) {
      if (Array.isArray(show?.genres)) {
        return show.genres.filter(Boolean);
      }

      const genre = String(show?.genre || "").trim();
      return genre ? [genre] : [];
    }

    function getShowSummary(show) {
      const rawSummary = String(show?.summary || "").trim();
      if (!rawSummary) {
        return "";
      }

      const summaryContainer = document.createElement("div");
      summaryContainer.innerHTML = rawSummary;
      return summaryContainer.textContent?.trim() || rawSummary;
    }

    function normalizeShow(show) {
      const id = getShowId(show);
      if (!id) {
        return null;
      }

      const image = getShowImage(show);
      const title = getShowTitle(show);
      const genres = getShowGenres(show);
      const summary = getShowSummary(show);

      return {
        id,
        title,
        genres,
        summary,
        image: { medium: image },
      };
    }

    function buildSelectedShowsPayload() {
      return Array.from(selectedShows.values()).map((show) => ({
        id: show.id,
        title: show.title || "Serie sans nom",
        genres: Array.isArray(show.genres) ? show.genres : [],
        summary: show.summary || "",
        image: show.image || null,
      }));
    }

    function updateSelectionCount() {
      selectedShowsPayload = buildSelectedShowsPayload();
      list.selectedShowsPayload = selectedShowsPayload;

      console.log("Séries sélectionnées :", selectedShowsPayload);

      if (accountContinueButton) {
        accountContinueButton.selectedShowsPayload = selectedShowsPayload;
        accountContinueButton.classList.toggle("ready", selectedShows.size >= 5);
      }

      if (selectionCount) {
        selectionCount.textContent = `${selectedShows.size} série(s) sélectionnée(s)`;
      }
    }

    if (accountContinueButton) {
      accountContinueButton.addEventListener("click", () => {
        console.log("Bouton Continuer cliqué. Séries sélectionnées :", Array.from(selectedShows.values()));

        if (selectedShows.size >= 5) {
          const payload = buildSelectedShowsPayload();

          console.log("Envoi du compte avec les séries sélectionnées :", payload);
          setBodyWaiting(true);

          fetch(accountContinueButton.dataset.apiUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ shows: payload }),
          })
            .then(async (response) => {
              const data = await response.json();

              if (!response.ok) {
                throw new Error(data.error || "Erreur lors de la sauvegarde.");
              }

              return data;
            })
            .then((data) => {
              if (data.redirect) {
                window.location.href = data.redirect;
              }
            })
            .catch((error) => {
              console.error(error);
              window.alert(error.message || "Erreur lors de la sauvegarde.");
            })
            .finally(() => {
              setBodyWaiting(false);
            });
        }
      });
    } else {
      console.warn("Bouton Continuer non trouvé. La fonctionnalité de soumission du compte ne fonctionnera pas.");
    }

    function sortCards() {
      const cards = Array.from(list.querySelectorAll(".gen-account-card-item"));

      cards
        .sort((firstCard, secondCard) => {
          const firstSelected = firstCard.classList.contains("selected") ? 0 : 1;
          const secondSelected = secondCard.classList.contains("selected") ? 0 : 1;

          if (firstSelected !== secondSelected) {
            return firstSelected - secondSelected;
          }

          return Number(firstCard.dataset.renderOrder || 0) - Number(secondCard.dataset.renderOrder || 0);
        })
        .forEach((card) => {
          list.appendChild(card);
        });
    }

    function mergeShows(shows) {
      const merged = [];
      const seen = new Set();

      selectedShows.forEach((show) => {
        merged.push(show);
        seen.add(show.id);
      });

      shows.forEach((show) => {
        const normalizedShow = normalizeShow(show);
        if (normalizedShow && !seen.has(normalizedShow.id)) {
          merged.push(normalizedShow);
          seen.add(normalizedShow.id);
        }
      });

      return merged;
    }

    function createCard(show, order) {
      const card = document.createElement("div");
      const image = document.createElement("img");
      const name = document.createElement("div");
      const icon = document.createElement("i");

      card.className = "gen-account-card-item";
      card.dataset.showId = show.id;
      card.dataset.renderOrder = String(order);
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");

      image.src = getShowImage(show);
      image.alt = show.title;

      name.className = "name";
      name.textContent = show.title;

      icon.className = "bi bi-check-circle-fill gen-account-card-icon";
      icon.setAttribute("aria-hidden", "true");

      card.appendChild(image);
      card.appendChild(name);
      card.appendChild(icon);

      function syncCardState() {
        const isSelected = selectedShows.has(show.id);
        card.classList.toggle("selected", isSelected);
        card.setAttribute("aria-pressed", String(isSelected));
      }

      function toggleCard() {
        if (selectedShows.has(show.id)) {
          selectedShows.delete(show.id);
        } else {
          selectedShows.set(show.id, show);
        }

        syncCardState();
        sortCards();
        updateSelectionCount();
      }

      card.addEventListener("click", toggleCard);
      syncCardState();
      return card;
    }

    function renderShows(shows) {
      const mergedShows = mergeShows(shows);
      list.innerHTML = "";

      mergedShows.forEach((show, index) => {
        list.appendChild(createCard(show, index));
      });

      sortCards();
      updateSelectionCount();
    }

    renderShows(initialShows);

    if (searchForm && searchInput) {
      searchForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const query = searchInput.value.trim();
        if (!query) {
          renderShows(initialShows);
        } else {
          try {
            const response = await fetch(`${searchForm.dataset.apiUrl}?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (response.ok) {
              renderShows(data.items || []);
            }
          } catch (_error) {
          }
        }
      });

      searchInput.addEventListener("input", () => {
        if (!searchInput.value.trim()) {
          renderShows(initialShows);
        }
      });
    }
  }
}
