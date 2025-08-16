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


// Dark Mode Toggle Section Start for desktop
{
            const toggleButton = document.getElementById('darkModeToggle');

        // Save original button content
        const originalContent = toggleButton.innerHTML;

        // Check localStorage on page load
        if (localStorage.getItem('darkMode') === 'enabled') {
            document.body.classList.add('dark-mode');
            toggleButton.innerHTML = '☀ Light Mode';
        }

        // Toggle dark mode on button click
        toggleButton.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');

            if (document.body.classList.contains('dark-mode')) {
                localStorage.setItem('darkMode', 'enabled');
                toggleButton.innerHTML = '☀ Light Mode';
            } else {
                localStorage.setItem('darkMode', 'disabled');
                toggleButton.innerHTML = originalContent; // 👈 restore what you had originally
            }
        });
}

// dark mode toggle for phone 
{
// Dark Mode Toggle Section for Mobile Only
const mobileToggle = document.getElementById('darkModeToggleMobile');

// Save original button content
const originalMobileContent = mobileToggle ? mobileToggle.innerHTML : '';

// Check localStorage on page load
if (localStorage.getItem('darkModeMobile') === 'enabled') {
    document.body.classList.add('dark-mode');
    if (mobileToggle) mobileToggle.innerHTML = '<span>☀ Light Mode</span>';
}

// Toggle dark mode on mobile button click
if (mobileToggle) {
    mobileToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');

        if (document.body.classList.contains('dark-mode')) {
            localStorage.setItem('darkModeMobile', 'enabled');
            mobileToggle.innerHTML = '<span>☀ Light Mode</span>';
        } else {
            localStorage.setItem('darkModeMobile', 'disabled');
            mobileToggle.innerHTML = originalMobileContent; // restore original
        }
    });
}


}

