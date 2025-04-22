/**
 * Gestion simplifiée du thème (clair/sombre)
 */
document.addEventListener('DOMContentLoaded', function() {
    // Fonction pour initialiser le thème
    function initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-bs-theme', savedTheme);
    }
    
    // Fonction pour basculer le thème
    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-bs-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    }
    
    // Ajouter les écouteurs d'événements aux boutons
    document.querySelectorAll('.theme-toggle').forEach(function(btn) {
        if (btn) {
            btn.addEventListener('click', toggleTheme);
        }
    });
    
    // Initialiser le thème
    initTheme();
});