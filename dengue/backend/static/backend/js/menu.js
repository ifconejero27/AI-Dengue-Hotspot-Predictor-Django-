document.addEventListener('DOMContentLoaded', function() {
  const navBtn = document.querySelector('.nav-btn');
  const mainMenu = document.querySelector('.main-menu');
  navBtn.addEventListener('click', function() {
    mainMenu.classList.toggle('active');
    if (mainMenu.classList.contains('active')) {
      navBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
    } else {
      navBtn.innerHTML = '<i class="fa-solid fa-bars"></i>';
    }
  });

  const profileTrigger = document.getElementById('pf');
  const profileModal = document.getElementById('profile-modal');
  profileTrigger.addEventListener('click', function() {
    profileModal.classList.toggle('active');
  });
});

