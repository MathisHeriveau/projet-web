window.GenFlixApp = window.GenFlixApp || {};

window.GenFlixApp.setBodyWaiting = function setBodyWaiting(isWaiting) {
  document.body.classList.toggle("is-waiting", isWaiting);
};
