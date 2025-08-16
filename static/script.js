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
// Mobile Display Menu Section end
const toggleButton = document.getElementById('darkModeToggle');

// Check localStorage on page load
if (localStorage.getItem('darkMode') === 'enabled') {
    document.body.classList.add('dark-mode');
    toggleButton.textContent = '☀ Light Mode';
}

// Toggle dark mode on button click
toggleButton.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');

    if(document.body.classList.contains('dark-mode')){
        localStorage.setItem('darkMode', 'enabled');
        toggleButton.textContent = '☀ Light Mode';
    } else {
        localStorage.setItem('darkMode', 'disabled');
        toggleButton.textContent = '🌙 Dark Mode';
    }
});


// home page 
 // Hero Slider Auto Change
let currentSlide = 0;
const slides = document.querySelectorAll(".hero-slider img");

function changeSlide() {
  slides.forEach((slide, index) => {
    slide.classList.remove("active");
    if (index === currentSlide) {
      slide.classList.add("active");
    }
  });

  currentSlide = (currentSlide + 1) % slides.length;
}

const track = document.querySelector(".carousel-track");
const prevBtn = document.querySelector(".prev");
const nextBtn = document.querySelector(".next");

let index = 0;
const imgWidth = 270; // image width + margin

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
