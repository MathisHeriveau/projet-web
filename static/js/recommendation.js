function initRecommendationPage() {
  const app = window.GenFlixApp || {};
  const setBodyWaiting = app.setBodyWaiting || (() => {});
  const page = document.querySelector(".recommendation-page");

  if (page) {
    const textArea = document.querySelector("#text-recommendation");
    const regenerateButton = document.querySelector("#recommendation-regenerate-button");
    const acceptButton = document.querySelector("#recommendation-accept-button");
    const list = document.querySelector("#recommendation-card-list");
    const empty = document.querySelector("#recommendation-empty");
    const initialItemsScript = document.querySelector("#recommendation-initial-items");
    const aiModal = document.querySelector("#recommendation-ai-modal");
    const aiModalTitle = document.querySelector("#recommendation-ai-modal-title");
    const aiModalSubtitle = document.querySelector("#recommendation-ai-modal-subtitle");
    const aiModalText = document.querySelector("#recommendation-ai-modal-text");
    const aiModalPitch = document.querySelector("#recommendation-ai-modal-pitch");
    const aiModalCloseButton = document.querySelector("#recommendation-ai-modal-close");
    const fallbackImage = "/static/images/no-image-blog.jpg";

    let initialItems = [];
    let previousFocusedElement = null;

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

    function openAiModal(title, explanation, aiPitch) {
      if (aiModal && aiModalTitle && aiModalSubtitle && aiModalText && aiModalPitch) {
        previousFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
        aiModalTitle.textContent = title || "Suggestion IA";
        aiModalSubtitle.textContent = `Suggestion IA pour ${title || "cette serie"}.`;
        aiModalText.textContent =
          String(explanation || "").trim() || "Aucune explication de l'IA n'est disponible pour cette recommandation.";
        aiModalPitch.textContent =
          String(aiPitch || "").trim() || "Aucun resume court n'est disponible pour cette recommandation.";
        aiModal.hidden = false;
        document.body.style.overflow = "hidden";

        if (aiModalCloseButton) {
          aiModalCloseButton.focus();
        }
      }
    }

    function closeAiModal() {
      if (aiModal && !aiModal.hidden) {
        aiModal.hidden = true;
        document.body.style.overflow = "";

        if (previousFocusedElement) {
          previousFocusedElement.focus();
          previousFocusedElement = null;
        }
      }
    }

    function normalizeRecommendation(item) {
      const id = String(item?.id ?? "").trim();
      const title = String(item?.title || item?.name || "Serie sans nom").trim();
      const genres = Array.isArray(item?.genres) ? item.genres.filter(Boolean) : [];
      const rawPitch = String(item?.ai_pitch || "").trim();
      const rawSummary = String(item?.summary || "").trim();
      const image = item?.image?.original || item?.image?.medium || fallbackImage;
      const rawExplanation = String(item?.explanation || "").trim();

      const pitchContainer = document.createElement("div");
      pitchContainer.innerHTML = rawPitch;

      const summaryContainer = document.createElement("div");
      summaryContainer.innerHTML = rawSummary;

      const explanationContainer = document.createElement("div");
      explanationContainer.innerHTML = rawExplanation;

      return {
        id,
        title: title || "Serie sans nom",
        genres,
        ai_pitch: pitchContainer.textContent?.trim() || rawPitch,
        summary: summaryContainer.textContent?.trim() || rawSummary,
        image,
        explanation: explanationContainer.textContent?.trim() || rawExplanation,
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
      const infoButton = document.createElement("button");
      const content = document.createElement("div");
      const link = document.createElement("a");
      const title = document.createElement("h4");
      const genres = document.createElement("div");
      const pitch = document.createElement("p");

      card.className = "recommendation-card";

      image.className = "recommendation-card-image";
      image.src = item.image;
      image.alt = item.title;

      infoButton.className = "recommendation-card-info-button";
      infoButton.type = "button";
      infoButton.textContent = "?";
      infoButton.setAttribute("aria-label", `Voir l'explication de l'IA pour ${item.title}`);
      infoButton.dataset.title = item.title;
      infoButton.dataset.explanation = item.explanation;
      infoButton.dataset.aiPitch = item.ai_pitch;

      content.className = "recommendation-card-content";
      link.className = "card-cover-link";
      link.href = `/series/${encodeURIComponent(item.id)}`;
      link.setAttribute("aria-label", `Voir la fiche de ${item.title}`);

      title.textContent = item.title;

      genres.className = "recommendation-card-genres";
      (item.genres.length ? item.genres.slice(0, 2) : ["Genres indisponibles"]).forEach((genre) => {
        const badge = document.createElement("span");
        badge.className = "recommendation-card-genre";
        badge.textContent = genre;
        genres.appendChild(badge);
      });

      pitch.className = "recommendation-card-summary text-tertiary";
      pitch.textContent = truncateText(item.summary, 100) || "Description indisponible pour cette serie.";

      content.appendChild(title);
      content.appendChild(genres);
      content.appendChild(pitch);

      card.appendChild(image);
      card.appendChild(infoButton);
      card.appendChild(content);
      card.appendChild(link);
      return card;
    }

    function renderRecommendations(items) {
      if (list && empty) {
        const normalizedItems = items.map(normalizeRecommendation).filter((item) => item.id && item.title);
        list.innerHTML = "";

        if (normalizedItems.length) {
          empty.hidden = true;
          normalizedItems.forEach((item) => {
            list.appendChild(createRecommendationCard(item));
          });
        } else {
          empty.hidden = false;
        }
      }
    }

    async function fetchJson(url, options = {}) {
      const response = await fetch(url, options);
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Erreur.");
      }

      return data;
    }

    if (list) {
      list.addEventListener("click", (event) => {
        const button = event.target.closest(".recommendation-card-info-button");
        if (button) {
          event.preventDefault();
          event.stopPropagation();
          openAiModal(button.dataset.title, button.dataset.explanation, button.dataset.aiPitch);
        }
      });
    }

    if (aiModal) {
      aiModal.addEventListener("click", (event) => {
        const closeTarget = event.target.closest("[data-modal-close=\"true\"]");
        if (closeTarget) {
          closeAiModal();
        }
      });
    }

    if (aiModalCloseButton) {
      aiModalCloseButton.addEventListener("click", () => {
        closeAiModal();
      });
    }

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeAiModal();
      }
    });

    if (regenerateButton) {
      regenerateButton.addEventListener("click", async () => {
        setButtonsDisabled(true);
        setBodyWaiting(true);

        try {
          const data = await fetchJson(page.dataset.generateTextUrl);
          if (textArea) {
            textArea.value = data.text || "";
          }
        } catch (_error) {
        } finally {
          setButtonsDisabled(false);
          setBodyWaiting(false);
        }
      });
    }

    if (acceptButton) {
      acceptButton.addEventListener("click", async () => {
        setButtonsDisabled(true);
        setBodyWaiting(true);

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
          setBodyWaiting(false);
        }
      });
    }

    renderRecommendations(initialItems);
  }
}
