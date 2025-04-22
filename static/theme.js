/**
 * Gestion du thème (clair/sombre) pour toute l'application
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialise le thème à partir du localStorage ou utilise le thème sombre par défaut
    function initializeTheme() {
        const storedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-bs-theme', storedTheme);
        updateThemeIcons(storedTheme);
    }
    
    // Bascule entre les thèmes clair et sombre
    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-bs-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        updateThemeIcons(newTheme);
    }
    
    // Met à jour les icônes du bouton de bascule selon le thème
    function updateThemeIcons(theme) {
        const darkIcons = document.querySelectorAll('.theme-icon-dark');
        const lightIcons = document.querySelectorAll('.theme-icon-light');
        
        if (darkIcons.length === 0 || lightIcons.length === 0) {
            return; // Les icônes ne sont pas présentes sur cette page
        }
        
        if (theme === 'dark') {
            darkIcons.forEach(icon => icon.classList.remove('d-none'));
            lightIcons.forEach(icon => icon.classList.add('d-none'));
        } else {
            darkIcons.forEach(icon => icon.classList.add('d-none'));
            lightIcons.forEach(icon => icon.classList.remove('d-none'));
        }
    }
    
    // Configure le bouton de bascule du thème
    const themeToggleButtons = document.querySelectorAll('.theme-toggle');
    if (themeToggleButtons.length > 0) {
        themeToggleButtons.forEach(button => {
            button.addEventListener('click', toggleTheme);
        });
    }
    
    // Initialise le thème au chargement de la page
    initializeTheme();
});