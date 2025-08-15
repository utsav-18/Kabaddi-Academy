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
