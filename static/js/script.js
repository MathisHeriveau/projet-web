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

/*
|--------------------------------------------------------------------------
| GENERATION DU PROFIL
|--------------------------------------------------------------------------
| Gère la page de première connexion :
| - affichage des séries
| - sélection / désélection
| - recherche TVMaze
| - remontée des séries sélectionnées en premier
*/
function initGenProfile() {
  const list = document.querySelector(".gen-profile-card-list");
  if (!list) {
    return;
  }

  const searchForm = document.querySelector("#gen-profile-search-form");
  const searchInput = document.querySelector("#gen-profile-search-input");
  const selectionCount = document.querySelector("#gen-profile-selection-count");
  const profileContinueButton = document.querySelector("#gen-profile-continue-button");
  const initialShowsScript = document.querySelector("#gen-profile-initial-shows");
  const fallbackImage = list.dataset.fallbackImage || "/static/images/no-image-blog.jpg";

  const selectedShows = new Map();
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
    return String(show?.id ?? show?.name ?? "");
  }

  function getShowImage(show) {
    return show?.image?.medium || fallbackImage;
  }

  function normalizeShow(show) {
    const id = getShowId(show);
    if (!id) {
      return null;
    }

    const image = getShowImage(show);

    return {
      id,
      name: show?.name || "Serie sans nom",
      image: image ? { medium: image } : null,
    };
  }

  function updateSelectionCount() {
    if (selectionCount) {
      selectionCount.textContent = `${selectedShows.size} série(s) sélectionnée(s)`;
    }

    if (profileContinueButton) {
      profileContinueButton.classList.toggle("ready", selectedShows.size >= 5);
    }
  }

  /*
  |--------------------------------------------------------------------------
  | TRI ET FUSION DES CARTES
  |--------------------------------------------------------------------------
  | Les séries sélectionnées restent visibles et remontent en haut,
  | même après une recherche puis un retour à la liste de base.
  */
  function sortCards() {
    const cards = Array.from(list.querySelectorAll(".gen-profile-card-item"));

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

    card.className = "gen-profile-card-item";
    card.dataset.showId = show.id;
    card.dataset.renderOrder = String(order);
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");

    image.src = getShowImage(show);
    image.alt = show.name;

    name.className = "name";
    name.textContent = show.name;

    icon.className = "bi bi-check-circle-fill gen-profile-card-icon";
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
| INITIALISATION GLOBALE
|--------------------------------------------------------------------------
| Chaque bloc s'active seulement si les éléments de la page existent.
*/
initCarousel();
initAuthForm();
initGenProfile();
