// Mobile Display Menu Section Start
{
        const menuBtn = document.getElementById('menu-btn');
        const closeBtn = document.getElementById('close-btn');
        const mobileMenu = document.getElementById('mobile-menu');

        menuBtn.addEventListener('click', () => {
            mobileMenu.classList.add('open');
        });

        closeBtn.addEventListener('click', () => {
            mobileMenu.classList.remove('open');
        });
}


// // Dark Mode Toggle Section Start for desktop and phone
{

// Dark Mode Toggle (works for both desktop & mobile)

// Get desktop & mobile toggle buttons
const desktopToggle = document.getElementById('darkModeToggle');
const mobileToggle = document.getElementById('darkModeToggleMobile');

// Save original button content
const originalDesktopContent = desktopToggle ? desktopToggle.innerHTML : '';
const originalMobileContent = mobileToggle ? mobileToggle.innerHTML : '';

// Check localStorage on page load
if (localStorage.getItem('darkMode') === 'enabled') {
    document.body.classList.add('dark-mode');
    if (desktopToggle) desktopToggle.innerHTML = '☀ Light Mode';
    if (mobileToggle) mobileToggle.innerHTML = '<span>☀ Light Mode</span>';
}

// Function to toggle dark mode
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');

    if (document.body.classList.contains('dark-mode')) {
        localStorage.setItem('darkMode', 'enabled');
        if (desktopToggle) desktopToggle.innerHTML = '☀ Light Mode';
        if (mobileToggle) mobileToggle.innerHTML = '<span>☀ Light Mode</span>';
    } else {
        localStorage.setItem('darkMode', 'disabled');
        if (desktopToggle) desktopToggle.innerHTML = originalDesktopContent;
        if (mobileToggle) mobileToggle.innerHTML = originalMobileContent;
    }
}

// Add event listeners
if (desktopToggle) desktopToggle.addEventListener('click', toggleDarkMode);
if (mobileToggle) mobileToggle.addEventListener('click', toggleDarkMode);


}

// home page 
 // Hero Slider Auto Change
{
// ==========================
// Hero Slider Auto Change (Every 5s)
// ==========================
let currentSlide = 0;
const slides = document.querySelectorAll(".hero-slider img");

function changeSlide() {
  slides.forEach((slide, index) => {
    slide.classList.remove("active");
    if (index === currentSlide) {
      slide.classList.add("active");
    }
  });

  // move to next slide
  currentSlide = (currentSlide + 1) % slides.length;
}

// run first immediately so one is visible
if (slides.length > 0) {
  changeSlide();
  setInterval(changeSlide, 5000); // every 5s
}

// ==========================
// Carousel With Buttons
// ==========================
const track = document.querySelector(".carousel-track");
const prevBtn = document.querySelector(".prev");
const nextBtn = document.querySelector(".next");

if (track && prevBtn && nextBtn) {
  let index = 0;
  const imgWidth = 270; // image width + margin (adjust if needed)

  nextBtn.addEventListener("click", () => {
    if (index < track.children.length - 1) {
      index++;
      track.style.transform = `translateX(-${index * imgWidth}px)`;
    }
  });

  prevBtn.addEventListener("click", () => {
    if (index > 0) {
      index--;
      track.style.transform = `translateX(-${index * imgWidth}px)`;
    }
  });
}

}