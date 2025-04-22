document.addEventListener('DOMContentLoaded', function() {
    // Elements for theme toggling
    const themeToggle = document.getElementById('themeToggle');
    const darkIcon = document.getElementById('darkIcon');
    const lightIcon = document.getElementById('lightIcon');
    
    // Theme toggle functionality
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
        
        // Initialize theme based on localStorage or system preference
        initializeTheme();
    }
    
    function initializeTheme() {
        // Check if theme is saved in localStorage
        const savedTheme = localStorage.getItem('theme');
        
        if (savedTheme) {
            // Apply saved theme
            document.documentElement.setAttribute('data-bs-theme', savedTheme);
            updateThemeIcons(savedTheme);
        } else {
            // Check for system preference
            const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const initialTheme = prefersDarkMode ? 'dark' : 'light';
            
            document.documentElement.setAttribute('data-bs-theme', initialTheme);
            updateThemeIcons(initialTheme);
            localStorage.setItem('theme', initialTheme);
        }
    }
    
    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        // Apply new theme
        document.documentElement.setAttribute('data-bs-theme', newTheme);
        
        // Update localStorage
        localStorage.setItem('theme', newTheme);
        
        // Update icons
        updateThemeIcons(newTheme);
    }
    
    function updateThemeIcons(theme) {
        if (theme === 'dark') {
            darkIcon.classList.add('d-none');
            lightIcon.classList.remove('d-none');
        } else {
            darkIcon.classList.remove('d-none');
            lightIcon.classList.add('d-none');
        }
    }

    // Toggle visibility of conversation messages
    document.querySelectorAll('.toggle-messages').forEach(button => {
        button.addEventListener('click', function() {
            const card = this.closest('.card');
            const messagesContainer = card.querySelector('.conversation-messages');
            
            if (messagesContainer.style.display === 'none') {
                messagesContainer.style.display = 'block';
                this.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Masquer les messages';
            } else {
                messagesContainer.style.display = 'none';
                this.innerHTML = '<i class="fas fa-eye me-1"></i>Afficher les messages';
            }
        });
        
        // Initialize - hide messages by default
        const card = button.closest('.card');
        const messagesContainer = card.querySelector('.conversation-messages');
        messagesContainer.style.display = 'none';
    });
    
    // Search functionality
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    
    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }
    
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                performSearch();
            }
        });
    }
    
    function performSearch() {
        const searchTerm = searchInput.value.toLowerCase();
        const cards = document.querySelectorAll('.conversation-card');
        
        cards.forEach(card => {
            const messageContents = Array.from(card.querySelectorAll('.message-user, .message-assistant'))
                .map(el => el.textContent.toLowerCase());
            
            const hasMatch = messageContents.some(content => content.includes(searchTerm));
            
            if (hasMatch || searchTerm === '') {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }
    
    // Filter buttons
    document.querySelectorAll('[data-filter]').forEach(button => {
        button.addEventListener('click', function() {
            // Update active button
            document.querySelectorAll('[data-filter]').forEach(btn => {
                btn.classList.remove('active');
            });
            this.classList.add('active');
            
            const filterType = this.getAttribute('data-filter');
            const cards = document.querySelectorAll('.conversation-card');
            
            cards.forEach(card => {
                const dateElement = card.querySelector('.card-header small:last-child');
                if (!dateElement) return; // Skip if element not found
                
                const dateText = dateElement.textContent;
                if (!dateText) return; // Skip if text content is empty
                
                const dateParts = dateText.split(': ');
                if (dateParts.length < 2) return; // Skip if format is not as expected
                
                const date = parseDate(dateParts[1]);
                const now = new Date();
                
                if (filterType === 'all') {
                    card.style.display = 'block';
                } else if (filterType === 'today') {
                    // Check if date is today
                    if (date.toDateString() === now.toDateString()) {
                        card.style.display = 'block';
                    } else {
                        card.style.display = 'none';
                    }
                } else if (filterType === 'week') {
                    // Check if date is within the last week
                    const oneWeekAgo = new Date();
                    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
                    
                    if (date >= oneWeekAgo) {
                        card.style.display = 'block';
                    } else {
                        card.style.display = 'none';
                    }
                }
            });
        });
    });
    
    // Helper function to parse date from string format DD/MM/YYYY HH:MM
    function parseDate(dateString) {
        if (!dateString) return new Date(); // Return current date if string is empty
        
        try {
            const parts = dateString.split(' ');
            if (parts.length < 2) return new Date(); // Return current date if format is invalid
            
            const datePart = parts[0];
            const timePart = parts[1];
            
            const [day, month, year] = datePart.split('/');
            const [hours, minutes] = timePart.split(':');
            
            return new Date(year, month - 1, day, hours, minutes);
        } catch (e) {
            console.error('Error parsing date:', e);
            return new Date(); // Return current date in case of error
        }
    }
});