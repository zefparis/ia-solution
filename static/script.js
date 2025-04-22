document.addEventListener('DOMContentLoaded', function() {
    // Vérifier si un texte extrait par OCR est prêt à être envoyé (depuis la page d'extraction de texte)
    const extractedText = sessionStorage.getItem('textToSend');
    const chatContainer = document.getElementById('chatContainer');
    
    if (extractedText && chatContainer) {
        // Informer l'utilisateur qu'un texte a été extrait
        const alert = document.createElement('div');
        alert.className = 'alert alert-info alert-dismissible fade show mb-3';
        alert.role = 'alert';
        alert.innerHTML = `
            <i class="fas fa-info-circle me-2"></i>
            Un texte extrait via caméra est prêt à être envoyé à Benji. 
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insérer l'alerte en haut du conteneur de chat
        chatContainer.insertBefore(alert, chatContainer.firstChild);
        
        // Pré-remplir le champ de message avec un texte d'introduction
        const userMessageInput = document.getElementById('userMessage');
        if (userMessageInput) {
            userMessageInput.value = "Peux-tu analyser ce texte pour moi ? ";
            userMessageInput.focus();
            
            // Envoyer automatiquement le message avec le texte extrait
            setTimeout(() => {
                // Vérifier que le formulaire existe
                const messageForm = document.getElementById('messageForm');
                if (messageForm) {
                    // Simuler la soumission du formulaire
                    const submitEvent = new Event('submit', {
                        'bubbles': true,
                        'cancelable': true
                    });
                    messageForm.dispatchEvent(submitEvent);
                }
            }, 500); // Délai court pour permettre au DOM de se mettre à jour
        }
    }
    
    // Vérifier si nous sommes sur la page de chat pour éviter les erreurs
    if (!chatContainer) {
        // Nous ne sommes pas sur une page avec chat, pas besoin d'initialiser ces fonctionnalités
        return;
    }
    
    // DOM elements pour la page de chat
    const emptyState = document.getElementById('emptyState');
    const messageForm = document.getElementById('messageForm');
    const userMessageInput = document.getElementById('userMessage');
    const sendBtn = document.getElementById('sendBtn');
    const clearBtn = document.getElementById('clearBtn');
    const typingIndicator = document.getElementById('typingIndicator');
    const errorToast = document.getElementById('errorToast');
    const errorToastBody = document.getElementById('errorToastBody');
    const themeToggle = document.querySelector('.theme-toggle'); // Utiliser le sélecteur de classe au lieu de l'ID
    const toggleSpeechBtn = document.getElementById('toggleSpeechBtn');
    
    // Speech synthesis
    let synthesis = null;
    
    // Speech synthesis enabled state
    let speechEnabled = localStorage.getItem('speechEnabled') === 'true';
    
    // Variables pour les voix
    let frenchVoices = [];
    
    // Initialize speech synthesis with fallback support
    try {
        if ('speechSynthesis' in window) {
            synthesis = window.speechSynthesis;
            
            // Fonction pour récupérer et filtrer les voix françaises
            function loadVoices() {
                try {
                    const voices = synthesis.getVoices();
                    console.log('Toutes les voix disponibles:', '');
                    
                    // Filtrer les voix françaises, d'abord les locales puis les autres
                    const localFrenchVoices = voices.filter(voice => 
                        voice.lang.includes('fr') && voice.localService === true
                    );
                    
                    const remoteFrenchVoices = voices.filter(voice => 
                        voice.lang.includes('fr') && voice.localService !== true
                    );
                    
                    frenchVoices = [...localFrenchVoices, ...remoteFrenchVoices];
                    
                    if (frenchVoices.length > 0) {
                        console.log('Voix françaises disponibles:', frenchVoices.map(v => v.name).join(', '));
                    } else {
                        console.log('Aucune voix française trouvée, utilisation de la voix par défaut');
                    }
                } catch (e) {
                    console.error('Erreur lors du chargement des voix:', e);
                }
            }
            
            // Charger les voix immédiatement si elles sont disponibles
            loadVoices();
            
            // Et aussi lors de l'événement voiceschanged au cas où elles sont chargées de manière asynchrone
            if (synthesis) {
                try {
                    synthesis.addEventListener('voiceschanged', loadVoices);
                } catch (e) {
                    console.error('Erreur lors de l\'ajout de l\'écouteur voiceschanged:', e);
                    // Charger les voix après un petit délai au cas où elles ne sont pas immédiatement disponibles
                    setTimeout(loadVoices, 500);
                }
            }
            
        } else {
            throw new Error('Speech Synthesis API not supported');
        }
    } catch (error) {
        console.error('Failed to initialize speech synthesis:', error);
        // Disable the speech toggle button
        if (toggleSpeechBtn) {
            toggleSpeechBtn.disabled = true;
            toggleSpeechBtn.classList.add('btn-secondary');
            toggleSpeechBtn.classList.remove('btn-outline-info');
            toggleSpeechBtn.title = 'Synthèse vocale non disponible';
        }
    }
    
    // Bootstrap toast object
    const toast = new bootstrap.Toast(errorToast);
    
    // Function to load chat history
    async function loadChatHistory() {
        try {
            const response = await fetch('/history');
            
            if (!response.ok) {
                // Si c'est une erreur 404, c'est probablement juste un nouvel utilisateur sans historique
                if (response.status === 404) {
                    return;
                }
                throw new Error('Impossible de charger l\'historique du chat');
            }
            
            const data = await response.json();
            
            if (data.messages && data.messages.length > 0) {
                // Clear empty state
                if (emptyState) {
                    emptyState.classList.add('d-none');
                }
                
                // Add messages to chat
                data.messages.forEach(msg => {
                    const messageElement = createMessageElement(msg.role, msg.content);
                    chatContainer.appendChild(messageElement);
                });
                
                // Scroll to bottom
                scrollToBottom();
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
            // Ne pas afficher d'erreur à l'utilisateur pour cela, c'est non critique
            // C'est probablement juste un nouvel utilisateur sans historique
        }
    }
    
    // Load chat history when page loads
    if (chatContainer) {
        loadChatHistory();
    }
    
    // Event listeners
    if (messageForm) messageForm.addEventListener('submit', sendMessage);
    if (clearBtn) clearBtn.addEventListener('click', clearHistory);
    
    // Theme toggle functionality
    if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
    
    // Toggle speech synthesis (si le bouton existe)
    if (toggleSpeechBtn) {
        toggleSpeechBtn.addEventListener('click', toggleSpeech);
    }
    
    // Initialize speech toggle button state (si le bouton existe)
    if (toggleSpeechBtn) {
        updateSpeechToggleButton();
    }
    
    // Initialize theme based on localStorage or system preference
    initializeTheme();
    
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
        const darkIcon = document.querySelector('.theme-icon-dark');
        const lightIcon = document.querySelector('.theme-icon-light');
        
        if (!darkIcon || !lightIcon) return;
        
        if (theme === 'dark') {
            darkIcon.classList.add('d-none');
            lightIcon.classList.remove('d-none');
        } else {
            darkIcon.classList.remove('d-none');
            lightIcon.classList.add('d-none');
        }
    }
    
    // Function to load chat history
    async function loadChatHistory() {
        try {
            const response = await fetch('/history');
            
            if (!response.ok) {
                // Si c'est une erreur 404, c'est probablement juste un nouvel utilisateur sans historique
                if (response.status === 404) {
                    return;
                }
                throw new Error('Impossible de charger l\'historique du chat');
            }
            
            const history = await response.json();
            
            if (history && history.length > 0) {
                if (emptyState) {
                    emptyState.classList.add('d-none');
                }
                
                history.forEach(message => {
                    const messageElement = createMessageElement(
                        message.role === 'user' ? 'user' : 'assistant',
                        message.content
                    );
                    chatContainer.appendChild(messageElement);
                });
                
                // Scroll to bottom of chat
                scrollToBottom();
            } else if (emptyState) {
                emptyState.classList.remove('d-none');
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
            // Ne pas afficher d'erreur à l'utilisateur pour cela, c'est non critique
        }
    }
    
    // Function to send a message
    async function sendMessage(event) {
        event.preventDefault();
        
        // Vérifier si nous avons un texte extrait provenant de l'OCR
        let message = userMessageInput.value.trim();
        const extractedText = sessionStorage.getItem('textToSend');
        
        if (extractedText) {
            // Si l'utilisateur a également saisi un message, nous allons le combiner
            if (message) {
                message = `${message}\n\nTexte extrait via caméra :\n${extractedText}`;
            } else {
                message = `Texte extrait via caméra :\n${extractedText}`;
            }
            
            // Effacer le texte stocké après l'avoir utilisé
            sessionStorage.removeItem('textToSend');
        }
        
        if (!message) return;
        
        // Hide empty state if visible
        emptyState.classList.add('d-none');
        
        // Add user message to chat
        const userMessageElement = createMessageElement('user', message);
        chatContainer.appendChild(userMessageElement);
        
        // Clear input
        userMessageInput.value = '';
        
        // Scroll to bottom
        scrollToBottom();
        
        // Show typing indicator
        typingIndicator.classList.remove('d-none');
        
        // Disable send button
        sendBtn.disabled = true;
        
        // Créer un élément message pour la réponse de l'assistant qui sera mise à jour au fil du streaming
        const assistantMessageElement = createMessageElement('assistant', '');
        chatContainer.appendChild(assistantMessageElement);
        
        // Référence au contenu du message pour le mettre à jour pendant le streaming
        const contentDiv = assistantMessageElement.querySelector('.content');
        
        // Texte initial avec préfixe
        contentDiv.innerHTML = '<span class="streaming-cursor"></span>';
        
        // Variable pour stocker la réponse complète
        let fullResponse = '';
        
        try {
            // Envoyer la requête au serveur
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });
            
            if (!response.ok) {
                // Si la réponse n'est pas OK, essayer de récupérer le message d'erreur
                try {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Erreur de serveur');
                } catch (e) {
                    throw new Error(`Erreur de serveur: ${response.status}`);
                }
            }
            
            // Obtenir le reader pour le streaming
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            // Fonction pour traiter le texte reçu
            async function processStream() {
                try {
                    while (true) {
                        const { done, value } = await reader.read();
                        
                        if (done) {
                            // Traitement final du buffer
                            if (buffer.trim()) {
                                const lines = buffer.split('\n\n');
                                for (const line of lines) {
                                    if (line.trim().startsWith('data:')) {
                                        processServerSentEvent(line);
                                    }
                                }
                            }
                            
                            // Indiquer que le streaming est terminé si ce n'est pas déjà fait
                            typingIndicator.classList.add('d-none');
                            sendBtn.disabled = false;
                            
                            // Lire la réponse complète si la lecture vocale est activée
                            if (speechEnabled && fullResponse) {
                                speakText(fullResponse);
                            }
                            
                            break;
                        }
                        
                        // Convertir le chunk en texte et l'ajouter au buffer
                        const chunk = decoder.decode(value, { stream: true });
                        buffer += chunk;
                        
                        // Chercher des lignes complètes "data: {...}\n\n"
                        let lines = buffer.split('\n\n');
                        
                        // Conserver la dernière ligne qui pourrait être incomplète
                        buffer = lines.pop() || '';
                        
                        // Traiter les lignes complètes
                        for (const line of lines) {
                            if (line.trim().startsWith('data:')) {
                                processServerSentEvent(line);
                            }
                        }
                    }
                } catch (error) {
                    console.error('Erreur lors du traitement du stream:', error);
                    showError('Erreur de connexion. Veuillez réessayer.');
                    
                    // Nettoyer en cas d'erreur
                    typingIndicator.classList.add('d-none');
                    sendBtn.disabled = false;
                    
                    // Si aucune réponse n'a été reçue, supprimer le message vide de l'assistant
                    if (!fullResponse) {
                        assistantMessageElement.remove();
                    }
                }
            }
            
            // Fonction pour traiter un événement SSE
            function processServerSentEvent(line) {
                try {
                    // Extraire la partie JSON après "data: "
                    const jsonStr = line.trim().substring(5);
                    const data = JSON.parse(jsonStr);
                    
                    // Vérifier s'il y a une erreur
                    if (data.error) {
                        showError(data.error);
                        if (!fullResponse) {
                            assistantMessageElement.remove();
                        }
                        typingIndicator.classList.add('d-none');
                        sendBtn.disabled = false;
                        return;
                    }
                    
                    // Vérifier si le streaming est terminé
                    if (data.done) {
                        typingIndicator.classList.add('d-none');
                        sendBtn.disabled = false;
                        return;
                    }
                    
                    // Si on a un morceau de texte, l'ajouter à la réponse
                    if (data.chunk) {
                        // Ajouter le texte à la réponse complète
                        fullResponse += data.chunk;
                        
                        // Mettre à jour le contenu sans préfixe (pour éviter les répétitions)
                        const formattedContent = fullResponse.replace(/\n/g, '<br>');
                        contentDiv.innerHTML = formattedContent + '<span class="streaming-cursor"></span>';
                        
                        // Défiler vers le bas
                        scrollToBottom();
                    }
                } catch (e) {
                    console.error('Erreur lors du traitement d\'un événement SSE:', e, line);
                }
            }
            
            // Lancer le traitement du stream
            processStream();
            
        } catch (error) {
            console.error('Erreur lors de l\'envoi du message:', error);
            showError(error.message || 'Erreur réseau. Veuillez vérifier votre connexion et réessayer.');
            
            // Supprimer le message vide de l'assistant
            assistantMessageElement.remove();
            
            // Masquer l'indicateur de saisie
            typingIndicator.classList.add('d-none');
            
            // Réactiver le bouton d'envoi
            sendBtn.disabled = false;
        }
    }
    
    // Function to create a message element
    function createMessageElement(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message mb-3`;
        
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        
        const icon = document.createElement('i');
        if (role === 'user') {
            icon.className = 'fas fa-user';
        } else {
            icon.className = 'fas fa-robot';
        }
        
        avatar.appendChild(icon);
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'content';
        
        // Process message content - Convert newlines to <br>
        // Ne plus ajouter de préfixe pour éviter les répétitions
        const formattedContent = content.replace(/\n/g, '<br>');
        contentDiv.innerHTML = formattedContent;
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        
        return messageDiv;
    }
    
    // Function to clear chat history
    async function clearHistory() {
        try {
            const response = await fetch('/clear', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Clear chat container
                chatContainer.innerHTML = '';
                
                // Show empty state
                emptyState.classList.remove('d-none');
                chatContainer.appendChild(emptyState);
                
                // If there's a reset message, display it as an assistant message
                if (data.message) {
                    // Hide empty state
                    emptyState.classList.add('d-none');
                    
                    // Add assistant message with the reset confirmation
                    const resetMessageElement = createMessageElement('assistant', data.message);
                    chatContainer.appendChild(resetMessageElement);
                }
            } else {
                showError('Impossible d\'effacer l\'historique. Veuillez réessayer.');
            }
        } catch (error) {
            console.error('Error clearing history:', error);
            showError('Erreur réseau. Veuillez vérifier votre connexion et réessayer.');
        }
    }
    
    // Function to scroll to bottom of chat
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // Function to show error toast
    function showError(message) {
        errorToastBody.textContent = message;
        toast.show();
    }
    
    // Function to toggle speech synthesis
    function toggleSpeech() {
        speechEnabled = !speechEnabled;
        localStorage.setItem('speechEnabled', speechEnabled);
        updateSpeechToggleButton();
        
        // Provide feedback
        if (speechEnabled) {
            speakText("La lecture vocale est maintenant activée.");
        } else {
            // Cancel any ongoing speech
            if (synthesis) {
                synthesis.cancel();
            }
        }
    }
    
    // Function to update speech toggle button appearance
    function updateSpeechToggleButton() {
        if (!toggleSpeechBtn) return;
        
        if (speechEnabled) {
            toggleSpeechBtn.classList.remove('btn-outline-info');
            toggleSpeechBtn.classList.add('btn-info');
            toggleSpeechBtn.title = 'Désactiver la lecture vocale des réponses';
        } else {
            toggleSpeechBtn.classList.remove('btn-info');
            toggleSpeechBtn.classList.add('btn-outline-info');
            toggleSpeechBtn.title = 'Activer la lecture vocale des réponses';
        }
    }
    
    // Function to speak text (text-to-speech)
    function speakText(text) {
        if (synthesis && speechEnabled) {
            // Cancel any ongoing speech
            synthesis.cancel();
            
            // Prétraitement du texte
            // 1. Supprimer les répétitions de phrases
            const processedText = removeDuplicateSentences(text);
            
            // 2. Supprimer le préfixe "Benji :" qu'on ajoute visuellement
            let cleanText = processedText.replace(/^Benji\s*:\s*/i, '');
            
            // Create utterance
            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.lang = 'fr-FR';
            utterance.rate = 1.0; // Vitesse normale pour un son plus naturel
            utterance.pitch = 1.05; // Légèrement plus aigu pour une voix plus claire
            utterance.volume = 1.0; // Volume maximal
            
            // Sélectionner la meilleure voix française disponible (préférer les voix naturelles si disponibles)
            if (frenchVoices.length > 0) {
                // Chercher des voix naturelles (souvent indiquées par "Online" ou "Neural" dans le nom)
                const naturalVoice = frenchVoices.find(voice => 
                    voice.name.includes('Natural') || 
                    voice.name.includes('Neural') || 
                    voice.name.includes('Online') ||
                    voice.name.includes('Denise') ||
                    voice.name.includes('Sylvie')
                );
                
                if (naturalVoice) {
                    utterance.voice = naturalVoice;
                    console.log('Utilisation de la voix française naturelle:', naturalVoice.name);
                } else {
                    // Sinon utiliser la première voix française disponible
                    utterance.voice = frenchVoices[0];
                    console.log('Utilisation de la voix française standard:', frenchVoices[0].name);
                }
            } else {
                console.log('Aucune voix française disponible, utilisation de la voix par défaut');
            }
            
            // Speak
            synthesis.speak(utterance);
        }
    }
    
    // Fonction pour supprimer les phrases répétées (problème courant avec les réponses d'IA)
    function removeDuplicateSentences(text) {
        // Séparer le texte en phrases
        const sentences = text.match(/[^.!?]+[.!?]+/g) || [];
        
        // Si le texte ne contient pas assez de phrases, retourner tel quel
        if (sentences.length <= 3) return text;
        
        // Normaliser chaque phrase pour comparaison (lowercase, retirer ponctuation, espaces)
        const normalizedSentences = sentences.map(s => 
            s.toLowerCase().replace(/[^\w\s]/g, '').trim()
        );
        
        // Filtrer les phrases pour garder uniquement les uniques
        const uniqueSentences = [];
        const seen = new Set();
        
        for (let i = 0; i < sentences.length; i++) {
            const normalized = normalizedSentences[i];
            // Ignorer les phrases trop courtes
            if (normalized.length < 10) {
                uniqueSentences.push(sentences[i]);
                continue;
            }
            
            // Si nous n'avons pas encore vu cette phrase ou une similaire, la garder
            if (!seen.has(normalized)) {
                uniqueSentences.push(sentences[i]);
                seen.add(normalized);
            }
        }
        
        // Recombiner les phrases uniques
        return uniqueSentences.join(' ');
    }
    
    // Focus on input field
    userMessageInput.focus();
});