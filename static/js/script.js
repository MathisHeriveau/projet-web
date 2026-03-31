const items = document.querySelectorAll(".carrousel-item");
const prevButtons = document.querySelectorAll(".carrousel-control.prev");
const nextButtons = document.querySelectorAll(".carrousel-control.next");
const bullets = document.querySelectorAll(".bullet span");

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
