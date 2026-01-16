function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const icon = document.querySelector('#theme-icon i');
    if (theme === 'dark') {
        icon.className = 'bi bi-sun';
    } else {
        icon.className = 'bi bi-moon-stars';
    }
}

// --- LANGUAGE LOGIC ---
function setLanguage(lang) {
    localStorage.setItem('language', lang);
    applyLanguage(lang);
}

function applyLanguage(lang) {
    // This looks for any element with data-ka and data-en attributes
    document.querySelectorAll('[data-ka]').forEach(el => {
        el.textContent = el.getAttribute(`data-${lang}`);
    });

    // Toggle active button style
    document.getElementById('btn-ka').classList.toggle('active', lang === 'ka');
    document.getElementById('btn-en').classList.toggle('active', lang === 'en');
}

// --- INITIALIZE ON LOAD ---
document.addEventListener('DOMContentLoaded', () => {
    // Apply saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    // Apply saved language
    const savedLang = localStorage.getItem('language') || 'ka';
    applyLanguage(savedLang);
});