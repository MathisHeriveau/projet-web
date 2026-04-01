/*
|--------------------------------------------------------------------------
| ACCUEIL
|--------------------------------------------------------------------------
| Gère le carousel visible sur la page d'accueil.
*/
function initCarousel() {
  const items = document.querySelectorAll(".carrousel-item");
  if (!items.length) {
    return;
  }

  const prevButtons = document.querySelectorAll(".carrousel-control.prev");
  const nextButtons = document.querySelectorAll(".carrousel-control.next");
  const bullets = document.querySelectorAll(".bullet span");
  let currentIndex = 0;

  function renderCarousel() {
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
      renderCarousel();
    });
  });

  nextButtons.forEach((button) => {
    button.addEventListener("click", () => {
      currentIndex = (currentIndex + 1) % items.length;
      renderCarousel();
    });
  });

  renderCarousel();
}

/*
|--------------------------------------------------------------------------
| AUTHENTIFICATION
|--------------------------------------------------------------------------
| Gère l'envoi AJAX des formulaires de connexion / inscription.
*/
function initAuthForm() {
  const authForm = document.querySelector("#auth-form");
  const authMessage = document.querySelector("#auth-message");

  if (!authForm || !authMessage) {
    return;
  }

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

      if (!response.ok) {
        authMessage.textContent = data.error || "Erreur.";
        return;
      }

      window.location.href = data.redirect || authForm.dataset.redirectUrl || "/";
    } catch (_error) {
      authMessage.textContent = "Erreur reseau.";
      console.error("Erreur réseau lors de l'envoi du formulaire d'authentification :", _error);
    }
  });
}

/*
|--------------------------------------------------------------------------
| GENERATION DU COMPTE
|--------------------------------------------------------------------------
| Gère la page de première connexion :
| - affichage des séries
| - sélection / désélection
| - recherche TVMaze
| - remontée des séries sélectionnées en premier
*/
function initGenAccount() {
  const list = document.querySelector(".gen-account-card-list");
  if (!list) {
    return;
  }

  const searchForm = document.querySelector("#gen-account-search-form");
  const searchInput = document.querySelector("#gen-account-search-input");
  const selectionCount = document.querySelector("#gen-account-selection-count");
  const accountContinueButton = document.querySelector("#gen-account-continue-button");
  const initialShowsScript = document.querySelector("#gen-account-initial-shows");
  const fallbackImage = list.dataset.fallbackImage || "/static/images/no-image-blog.jpg";

  const selectedShows = new Map();
  let selectedShowsPayload = [];
  let initialShows = [];

  /*
  |--------------------------------------------------------------------------
  | DONNEES DE BASE
  |--------------------------------------------------------------------------
  | On recharge les séries envoyées par Flask au premier affichage.
  */
  if (initialShowsScript) {
    try {
      initialShows = JSON.parse(initialShowsScript.textContent || "[]");
    } catch (_error) {
      initialShows = [];
    }
  }

  /*
  |--------------------------------------------------------------------------
  | PETITS HELPERS
  |--------------------------------------------------------------------------
  | Fonctions utilitaires pour normaliser les données et mettre à jour
  | l'interface sans répéter du code partout.
  */
  function getShowId(show) {
    return String(show?.id ?? show?.title ?? show?.name ?? "");
  }

  function getShowImage(show) {
    return show?.image?.medium || fallbackImage;
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
      image: { medium: image } ,
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
    }

    if (selectionCount) {
      selectionCount.textContent = `${selectedShows.size} série(s) sélectionnée(s)`;
    }

    if (accountContinueButton) {
      accountContinueButton.classList.toggle("ready", selectedShows.size >= 5);
    }
  }

  
  if (accountContinueButton) {
    accountContinueButton.addEventListener("click", () => {
      console.log("Bouton Continuer cliqué. Séries sélectionnées :", Array.from(selectedShows.values()));
      if (selectedShows.size < 5) {
        return;
      }

      const payload = buildSelectedShowsPayload();

      console.log("Envoi du compte avec les séries sélectionnées :", payload);

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
        });


    });
  }else {
    console.warn("Bouton Continuer non trouvé. La fonctionnalité de soumission du compte ne fonctionnera pas.");
  } 

  /*
  |--------------------------------------------------------------------------
  | TRI ET FUSION DES CARTES
  |--------------------------------------------------------------------------
  | Les séries sélectionnées restent visibles et remontent en haut,
  | même après une recherche puis un retour à la liste de base.
  */
  function sortCards() {
    const cards = Array.from(list.querySelectorAll(".gen-account-card-item"));

    cards
      .sort((firstCard, secondCard) => {
        const firstSelected = firstCard.classList.contains("selected") ? 0 : 1;
        const secondSelected = secondCard.classList.contains("selected") ? 0 : 1;

        if (firstSelected !== secondSelected) {
          return firstSelected - secondSelected;
        }

        return (
          Number(firstCard.dataset.renderOrder || 0) -
          Number(secondCard.dataset.renderOrder || 0)
        );
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
      if (!normalizedShow || seen.has(normalizedShow.id)) {
        return;
      }

      merged.push(normalizedShow);
      seen.add(normalizedShow.id);
    });

    return merged;
  }

  /*
  |--------------------------------------------------------------------------
  | CREATION ET RENDU DES CARTES
  |--------------------------------------------------------------------------
  | Création d'une carte de série, gestion du clic, puis rendu complet
  | de la grille à partir de la liste courante.
  */
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

  /*
  |--------------------------------------------------------------------------
  | RECHERCHE
  |--------------------------------------------------------------------------
  | Appelle l'API backend qui interroge TVMaze avec le nom saisi.
  */
  searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const query = searchInput.value.trim();
    if (!query) {
      renderShows(initialShows);
      return;
    }

    try {
      const response = await fetch(
        `${searchForm.dataset.apiUrl}?q=${encodeURIComponent(query)}`
      );
      const data = await response.json();

      if (!response.ok) {
        return;
      }

      renderShows(data.items || []);

    } catch (_error) {
    }
  });

  searchInput.addEventListener("input", () => {
    if (searchInput.value.trim()) {
      return;
    }

    renderShows(initialShows);
  });
}

/*
|--------------------------------------------------------------------------
| RECOMMANDATIONS
|--------------------------------------------------------------------------
| Gère la page recommandations :
| - affichage du texte déjà sauvegardé
| - régénération du texte via l'API
| - sauvegarde du texte puis génération des séries IA
| - affichage des dernières recommandations déjà enregistrées
*/
function initRecommendationPage() {
  const page = document.querySelector(".recommendation-page");
  if (!page) {
    return;
  }

  const textArea = document.querySelector("#text-recommendation");
  const regenerateButton = document.querySelector("#recommendation-regenerate-button");
  const acceptButton = document.querySelector("#recommendation-accept-button");
  const list = document.querySelector("#recommendation-card-list");
  const empty = document.querySelector("#recommendation-empty");
  const initialItemsScript = document.querySelector("#recommendation-initial-items");
  const fallbackImage = "/static/images/no-image-blog.jpg";

  let initialItems = [];

  if (initialItemsScript) {
    try {
      initialItems = JSON.parse(initialItemsScript.textContent || "[]");
    } catch (_error) {
      initialItems = [];
    }
  }

  function setButtonsDisabled(disabled) {
    if (regenerateButton) {
      regenerateButton.disabled = disabled;
    }

    if (acceptButton) {
      acceptButton.disabled = disabled;
    }
  }

  function normalizeRecommendation(item) {
    const id = String(item?.id ?? "").trim();
    const title = String(item?.title || item?.name || "Serie sans nom").trim();
    const genres = Array.isArray(item?.genres) ? item.genres.filter(Boolean) : [];
    const rawSummary = String(item?.summary || "").trim();
    const image = item?.image?.medium || item?.image?.original || fallbackImage;

    const summaryContainer = document.createElement("div");
    summaryContainer.innerHTML = rawSummary;

    return {
      id,
      title: title || "Serie sans nom",
      genres,
      summary: summaryContainer.textContent?.trim() || rawSummary,
      image,
    };
  }

  function truncateText(text, maxLength) {
    const normalizedText = String(text || "").trim();
    if (normalizedText.length <= maxLength) {
      return normalizedText;
    }

    return `${normalizedText.slice(0, maxLength).trim()}...`;
  }

  function createRecommendationCard(item) {
    const card = document.createElement("article");
    const image = document.createElement("img");
    const content = document.createElement("div");
    const title = document.createElement("h4");
    const genres = document.createElement("div");
    const summary = document.createElement("p");

    card.className = "recommendation-card";

    image.className = "recommendation-card-image";
    image.src = item.image;
    image.alt = item.title;

    content.className = "recommendation-card-content";

    title.textContent = item.title;

    genres.className = "recommendation-card-genres";
    (item.genres.length ? item.genres : ["Genres indisponibles"]).forEach((genre) => {
      const badge = document.createElement("span");
      badge.className = "recommendation-card-genre";
      badge.textContent = genre;
      genres.appendChild(badge);
    });

    summary.className = "recommendation-card-summary text-tertiary";
    summary.textContent =
      truncateText(item.summary, 250) || "Resume indisponible pour cette serie.";

    content.appendChild(title);
    content.appendChild(genres);
    content.appendChild(summary);

    card.appendChild(image);
    card.appendChild(content);
    return card;
  }

  function renderRecommendations(items) {
    if (!list || !empty) {
      return;
    }

    const normalizedItems = items.map(normalizeRecommendation).filter((item) => item.id && item.title);
    list.innerHTML = "";

    if (!normalizedItems.length) {
      empty.hidden = false;
      return;
    }

    empty.hidden = true;
    normalizedItems.forEach((item) => {
      list.appendChild(createRecommendationCard(item));
    });
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.error || "Erreur.");
    }

    return data;
  }

  if (regenerateButton) {
    regenerateButton.addEventListener("click", async () => {
      setButtonsDisabled(true);

      try {
        const data = await fetchJson(page.dataset.generateTextUrl);
        if (textArea) {
          textArea.value = data.text || "";
        }
      } catch (_error) {
      } finally {
        setButtonsDisabled(false);
      }
    });
  }

  if (acceptButton) {
    acceptButton.addEventListener("click", async () => {
      setButtonsDisabled(true);

      try {
        await fetchJson(page.dataset.saveTextUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            recommendation_text: textArea ? textArea.value : "",
          }),
        });

        const data = await fetchJson(page.dataset.generateSeriesUrl);
        renderRecommendations(data.items || []);
      } catch (_error) {
      } finally {
        setButtonsDisabled(false);
      }
    });
  }

  renderRecommendations(initialItems);
}

/*
|--------------------------------------------------------------------------
| INITIALISATION GLOBALE
|--------------------------------------------------------------------------
| Chaque bloc s'active seulement si les éléments de la page existent.
*/
initCarousel();
initAuthForm();
initGenAccount();
initRecommendationPage();
