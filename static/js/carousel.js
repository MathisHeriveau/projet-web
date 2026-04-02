function initCarousel() {
  const items = document.querySelectorAll(".home-carousel-slide");
  if (!items.length) {
    return;
  }

  const prevButtons = document.querySelectorAll(".home-carousel-control-prev");
  const nextButtons = document.querySelectorAll(".home-carousel-control-next");
  const bullets = document.querySelectorAll(".home-carousel-bullets span");
  let currentIndex = 0;

  function renderCarousel() {
    items.forEach((item, index) => {
      item.classList.toggle("is-active", index === currentIndex);
    });

    bullets.forEach((bullet, index) => {
      bullet.classList.toggle("is-active", index === currentIndex);
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
