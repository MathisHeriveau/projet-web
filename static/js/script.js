const items = document.querySelectorAll(".carrousel-item");
const prevButtons = document.querySelectorAll(".carrousel-control.prev");
const nextButtons = document.querySelectorAll(".carrousel-control.next");
const bullets = document.querySelectorAll(".bullet span");
const authForm = document.querySelector("#auth-form");
const authMessage = document.querySelector("#auth-message");
const profileCardList = document.querySelector(".gen-profile-card-list");
const profileSearchForm = document.querySelector("#gen-profile-search-form");
const profileSearchInput = document.querySelector("#gen-profile-search-input");
const profileSearchMessage = document.querySelector("#gen-profile-search-message");
const initialShowsElement = document.querySelector("#gen-profile-initial-shows");
const profileSelectionCount = document.querySelector("#gen-profile-selection-count");
const profileContinueButton = document.querySelector("#gen-profile-continue-button");
const profileContinueMessage = document.querySelector("#gen-profile-continue-message");

let currentIndex = 0;
const MIN_PROFILE_SELECTIONS = 5;
const selectedProfileShows = new Set();
const selectedProfileShowData = new Map();
const fallbackProfileImage = profileCardList?.dataset.fallbackImage || "";
let initialProfileShows = [];

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

function setupProfileCard(item) {
  item.setAttribute("role", "button");
  item.setAttribute("tabindex", "0");

  if (!item.querySelector(".gen-profile-card-icon")) {
    const icon = document.createElement("i");
    icon.className = "bi bi-check-circle-fill gen-profile-card-icon";
    icon.setAttribute("aria-hidden", "true");
    item.appendChild(icon);
  }

  const syncSelectionState = () => {
    const showId = item.dataset.showId || "";
    const isSelected = selectedProfileShows.has(showId);
    item.classList.toggle("selected", isSelected);
    item.setAttribute("aria-pressed", String(isSelected));
  };

  const toggleSelection = () => {
    const showId = item.dataset.showId || "";
    if (!showId) {
      return;
    }

    if (selectedProfileShows.has(showId)) {
      selectedProfileShows.delete(showId);
      selectedProfileShowData.delete(showId);
    } else {
      selectedProfileShows.add(showId);
      const show = getProfileShowFromItem(item);
      if (show) {
        selectedProfileShowData.set(showId, show);
      }
    }

    syncSelectionState();
    reorderProfileCards();
    updateContinueState();
  };

  item.addEventListener("click", toggleSelection);
  item.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    event.preventDefault();
    toggleSelection();
  });
  syncSelectionState();
}

function reorderProfileCards() {
  if (!profileCardList) {
    return;
  }

  const cards = Array.from(profileCardList.querySelectorAll(".gen-profile-card-item"));
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
      profileCardList.appendChild(card);
    });
}

function updateContinueState() {
  const selectedCount = selectedProfileShows.size;
  const remainingCount = Math.max(MIN_PROFILE_SELECTIONS - selectedCount, 0);

  if (profileSelectionCount) {
    profileSelectionCount.textContent = `${selectedCount} série(s) sélectionnée(s)`;
  }

  if (profileContinueButton) {
    profileContinueButton.classList.toggle("ready", selectedCount >= MIN_PROFILE_SELECTIONS);
  }

  if (!profileContinueMessage) {
    return;
  }

  if (selectedCount === 0) {
    profileContinueMessage.textContent = "";
    profileContinueMessage.className = "gen-profile-continue-message text-tertiary";
    return;
  }

  if (selectedCount >= MIN_PROFILE_SELECTIONS) {
    profileContinueMessage.textContent = "Parfait, vous pouvez continuer.";
    profileContinueMessage.className = "gen-profile-continue-message success";
    return;
  }

  profileContinueMessage.textContent = `Encore ${remainingCount} série(s) à sélectionner minimum.`;
  profileContinueMessage.className = "gen-profile-continue-message error";
}

function getShowId(show) {
  return String(show?.id ?? show?.name ?? "");
}

function getShowImage(show) {
  return show?.image?.medium || fallbackProfileImage;
}

function normalizeProfileShow(show) {
  const showId = getShowId(show);
  if (!showId) {
    return null;
  }

  const image = getShowImage(show);

  return {
    id: show?.id ?? showId,
    name: show?.name || "Serie sans nom",
    image: image ? { medium: image } : null,
  };
}

function getProfileShowFromItem(item) {
  return normalizeProfileShow({
    id: item.dataset.showId || "",
    name: item.dataset.showName || "Serie sans nom",
    image: item.dataset.showImage ? { medium: item.dataset.showImage } : null,
  });
}

function getMergedProfileShows(shows) {
  const mergedShows = [];
  const mergedShowIds = new Set();

  selectedProfileShowData.forEach((show) => {
    const normalizedShow = normalizeProfileShow(show);
    if (!normalizedShow) {
      return;
    }

    mergedShows.push(normalizedShow);
    mergedShowIds.add(getShowId(normalizedShow));
  });

  shows.forEach((show) => {
    const normalizedShow = normalizeProfileShow(show);
    if (!normalizedShow) {
      return;
    }

    const showId = getShowId(normalizedShow);
    if (mergedShowIds.has(showId)) {
      return;
    }

    mergedShows.push(normalizedShow);
    mergedShowIds.add(showId);
  });

  return mergedShows;
}

function createProfileCard(show, index) {
  const item = document.createElement("div");
  item.className = "gen-profile-card-item";
  item.dataset.showId = getShowId(show);
  item.dataset.showName = show?.name || "Serie sans nom";
  item.dataset.showImage = getShowImage(show);
  item.dataset.renderOrder = String(index);

  const image = document.createElement("img");
  image.src = getShowImage(show);
  image.alt = show?.name || "Serie";

  const name = document.createElement("div");
  name.className = "name";
  name.textContent = show?.name || "Serie sans nom";

  item.appendChild(image);
  item.appendChild(name);
  setupProfileCard(item);
  return item;
}

function renderProfileCards(shows, emptyMessage = "Aucune serie n'a pu etre chargee pour le moment.") {
  if (!profileCardList) {
    return;
  }

  const mergedShows = getMergedProfileShows(shows);
  profileCardList.innerHTML = "";

  if (!mergedShows.length) {
    const emptyState = document.createElement("p");
    emptyState.className = "gen-profile-empty text-tertiary";
    emptyState.textContent = emptyMessage;
    profileCardList.appendChild(emptyState);
    return;
  }

  mergedShows.forEach((show, index) => {
    profileCardList.appendChild(createProfileCard(show, index));
  });

  reorderProfileCards();
  updateContinueState();
}

updateCarousel();

if (initialShowsElement && profileCardList) {
  try {
    initialProfileShows = JSON.parse(initialShowsElement.textContent || "[]");
  } catch (_error) {
    initialProfileShows = [];
  }

  renderProfileCards(initialProfileShows);
}

if (profileContinueButton) {
  profileContinueButton.addEventListener("click", () => {
    const selectedCount = selectedProfileShows.size;

    if (!profileContinueMessage) {
      return;
    }

    if (selectedCount < MIN_PROFILE_SELECTIONS) {
      profileContinueMessage.textContent = `Il faut sélectionner au moins ${MIN_PROFILE_SELECTIONS} séries avant de continuer.`;
      profileContinueMessage.className = "gen-profile-continue-message error";
      return;
    }

    profileContinueMessage.textContent = "Parfait, vous pouvez continuer.";
    profileContinueMessage.className = "gen-profile-continue-message success";
  });
}

if (profileSearchForm && profileSearchInput && profileCardList) {
  profileSearchForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const query = profileSearchInput.value.trim();
    if (!query) {
      renderProfileCards(initialProfileShows);
      if (profileSearchMessage) {
        profileSearchMessage.textContent = "";
      }
      return;
    }

    if (profileSearchMessage) {
      profileSearchMessage.textContent = "Recherche en cours...";
    }

    try {
      const response = await fetch(
        `${profileSearchForm.dataset.apiUrl}?q=${encodeURIComponent(query)}`
      );
      const data = await response.json();

      if (!response.ok) {
        if (profileSearchMessage) {
          profileSearchMessage.textContent = data.error || "Erreur de recherche.";
        }
        return;
      }

      renderProfileCards(
        data.items || [],
        "Aucune serie ne correspond a votre recherche."
      );

      if (profileSearchMessage) {
        profileSearchMessage.textContent =
          data.count > 0 ? `${data.count} serie(s) trouvee(s).` : "Aucun resultat.";
      }
    } catch (_error) {
      if (profileSearchMessage) {
        profileSearchMessage.textContent = "Erreur reseau.";
      }
    }
  });

  profileSearchInput.addEventListener("input", () => {
    if (profileSearchInput.value.trim()) {
      return;
    }

    renderProfileCards(initialProfileShows);
    if (profileSearchMessage) {
      profileSearchMessage.textContent = "";
    }
  });
}

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
