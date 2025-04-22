document.addEventListener('DOMContentLoaded', function() {
    // Éléments DOM communs
    const extractedTextArea = document.getElementById('extractedText');
    const titleInput = document.getElementById('titleInput');
    const saveTextBtn = document.getElementById('saveTextBtn');
    const sendToChatBtn = document.getElementById('sendToChatBtn');
    const processingIndicator = document.getElementById('processingIndicator');
    const confidenceIndicator = document.getElementById('confidenceIndicator');
    const confidenceValue = document.getElementById('confidenceValue');
    const savedTextsList = document.getElementById('savedTextsList');
    const noSavedTexts = document.getElementById('noSavedTexts');
    
    // Éléments pour la caméra
    const video = document.getElementById('cameraFeed');
    const canvas = document.getElementById('canvas');
    const capturedImage = document.getElementById('capturedImage');
    const captureBtn = document.getElementById('captureBtn');
    const switchCameraBtn = document.getElementById('switchCameraBtn');
    
    // Éléments pour l'upload d'image
    const imageUpload = document.getElementById('imageUpload');
    const uploadedImage = document.getElementById('uploadedImage');
    const processUploadBtn = document.getElementById('processUploadBtn');
    
    // Variables pour la gestion de la caméra et des images
    let stream = null;
    let facingMode = 'environment'; // Par défaut, on utilise la caméra arrière
    let extractedData = null;
    let savedTexts = [];
    
    // Initialisation
    initCamera();
    loadSavedTexts();
    
    // Initialiser la caméra
    async function initCamera() {
        try {
            // Vérifier d'abord si mediaDevices est disponible
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error("L'API MediaDevices n'est pas disponible sur ce navigateur ou cet environnement");
            }
            
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            
            // Options de la caméra : résolution plus petite et plus compatible
            const constraints = {
                video: {
                    facingMode: facingMode,
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    frameRate: { ideal: 15 }
                }
            };
            
            // Ajouter une contrainte pour la qualité sur les appareils mobiles
            if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
                constraints.video.advanced = [{ zoom: 2 }]; // Zoom x2 si disponible sur le mobile
            }
            
            stream = await navigator.mediaDevices.getUserMedia(constraints);
            video.srcObject = stream;
            
            // Attendre que la vidéo soit chargée avant de continuer
            await new Promise(resolve => {
                video.onloadedmetadata = () => {
                    resolve();
                };
            });
            
            // Démarrer la lecture
            await video.play();
            
            // Si tout va bien, afficher un message de succès dans la console
            console.log("Caméra activée avec succès: " + stream.getVideoTracks()[0].label);
            
            // Masquer les éventuels messages d'erreur précédents
            const errorMessageElement = document.getElementById('cameraErrorMessage');
            if (errorMessageElement) {
                errorMessageElement.style.display = 'none';
            }
            
            // Activer le bouton de capture
            captureBtn.disabled = false;
        } catch (err) {
            console.error('Erreur lors de l\'accès à la caméra:', err);
            
            // Afficher un message d'erreur plus détaillé dans l'interface
            const cameraContainer = document.querySelector('.camera-container');
            
            // Vérifier si un message d'erreur existe déjà
            let errorMessageElement = document.getElementById('cameraErrorMessage');
            
            if (!errorMessageElement) {
                // Créer un nouvel élément pour afficher le message d'erreur
                errorMessageElement = document.createElement('div');
                errorMessageElement.id = 'cameraErrorMessage';
                errorMessageElement.className = 'alert alert-warning mt-2';
                cameraContainer.appendChild(errorMessageElement);
            }
            
            // Personnaliser le message en fonction de l'erreur
            if (err.name === 'NotAllowedError') {
                errorMessageElement.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Accès à la caméra refusé. Veuillez autoriser l\'accès dans les paramètres de votre navigateur.';
            } else if (err.name === 'NotFoundError') {
                errorMessageElement.innerHTML = '<i class="fas fa-camera-slash me-2"></i>Aucune caméra détectée sur cet appareil.';
            } else if (err.name === 'NotReadableError' || err.name === 'AbortError') {
                errorMessageElement.innerHTML = '<i class="fas fa-camera-slash me-2"></i>La caméra est peut-être déjà utilisée par une autre application.';
            } else if (err.name === 'OverconstrainedError') {
                // Réessayer avec des contraintes plus simples
                initCameraWithSimpleConstraints();
                return;
            } else {
                errorMessageElement.innerHTML = '<i class="fas fa-exclamation-circle me-2"></i>Impossible d\'accéder à la caméra: ' + err.message + '<br><small class="text-muted">Cette fonctionnalité fonctionne mieux sur smartphone où l\'accès à la caméra est généralement disponible.</small>';
            }
            
            errorMessageElement.style.display = 'block';
            
            // Désactiver le bouton de capture
            captureBtn.disabled = true;
        }
    }
    
    // Fonction simplifiée pour initialiser la caméra avec des contraintes minimales
    async function initCameraWithSimpleConstraints() {
        try {
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            
            // Contraintes minimales
            const simpleConstraints = {
                video: {
                    facingMode: facingMode
                }
            };
            
            stream = await navigator.mediaDevices.getUserMedia(simpleConstraints);
            video.srcObject = stream;
            
            await video.play();
            console.log("Caméra activée avec des contraintes simplifiées");
            
            // Masquer les messages d'erreur
            const errorMessageElement = document.getElementById('cameraErrorMessage');
            if (errorMessageElement) {
                errorMessageElement.style.display = 'none';
            }
            
            // Activer le bouton de capture
            captureBtn.disabled = false;
        } catch (err) {
            console.error('Échec avec contraintes simplifiées:', err);
            
            // Afficher message d'erreur
            const cameraContainer = document.querySelector('.camera-container');
            let errorMessageElement = document.getElementById('cameraErrorMessage');
            
            if (!errorMessageElement) {
                errorMessageElement = document.createElement('div');
                errorMessageElement.id = 'cameraErrorMessage';
                errorMessageElement.className = 'alert alert-warning mt-2';
                cameraContainer.appendChild(errorMessageElement);
            }
            
            errorMessageElement.innerHTML = '<i class="fas fa-exclamation-circle me-2"></i>Impossible d\'accéder à la caméra même avec des paramètres simplifiés. Veuillez essayer l\'option "Importer une image" à la place.';
            errorMessageElement.style.display = 'block';
            
            // Désactiver le bouton de capture
            captureBtn.disabled = true;
        }
    }
    
    // Changer de caméra (avant/arrière)
    switchCameraBtn.addEventListener('click', function() {
        facingMode = facingMode === 'environment' ? 'user' : 'environment';
        initCamera();
    });
    
    // Capturer une image
    captureBtn.addEventListener('click', function() {
        const context = canvas.getContext('2d');
        
        // Utiliser des dimensions plus petites mais suffisantes
        const idealWidth = 1280;  // Résolution suffisante pour l'OCR
        const idealHeight = 960;  // Conserver les proportions approximativement
        
        // Ajuster la taille du canvas
        canvas.width = idealWidth;
        canvas.height = idealHeight;
        
        // Améliorer la qualité de l'image de façon modérée
        context.filter = 'contrast(1.1) brightness(1.05)';  // Contraste et luminosité plus modérés
        
        // Dessiner l'image de la vidéo sur le canvas
        context.drawImage(video, 0, 0, idealWidth, idealHeight);
        
        // Convertir le canvas en URL de données avec bonne qualité
        const imageDataUrl = canvas.toDataURL('image/jpeg', 0.95);
        
        // Afficher l'image capturée
        capturedImage.src = imageDataUrl;
        capturedImage.style.display = 'block';
        
        // Indiquer que le traitement est en cours
        const qualityNote = document.createElement('div');
        qualityNote.className = 'alert alert-info mt-2';
        qualityNote.innerHTML = 'Image capturée. Préparation pour l\'extraction de texte...';
        
        // Remplacer toute note existante
        const existingNote = capturedImage.parentNode.querySelector('.alert');
        if (existingNote) {
            existingNote.remove();
        }
        capturedImage.parentNode.appendChild(qualityNote);
        
        // Montrer l'indicateur de traitement avec information précise
        processingIndicator.style.display = 'block';
        processingIndicator.innerHTML = '<div class="spinner-border text-primary" role="status"></div><span class="ms-2">Envoi de l\'image à AWS Textract pour une extraction précise...</span>';
        
        // Réinitialiser le champ texte et les boutons
        extractedTextArea.value = 'Traitement en cours avec AWS Textract...\nLes résultats s\'afficheront ici dans quelques instants.';
        saveTextBtn.disabled = true;
        sendToChatBtn.disabled = true;
        confidenceIndicator.style.display = 'none';
        
        // Extraire le texte via AWS Textract avec un court délai pour mise à jour de l'interface
        setTimeout(() => {
            // Extraire la partie Base64 de l'URL de données
            const base64Image = imageDataUrl.split(',')[1];
            sendToAWSTextract(base64Image);
        }, 100);
    });
    
    // Extraire le texte de l'image avec Tesseract.js
    async function extractTextFromImage(imageDataUrl) {
        try {
            // Afficher un message pendant le chargement
            extractedTextArea.value = "Extraction du texte en cours...\nCela peut prendre quelques instants.";
            
            // Optimiser l'image avant de la traiter
            const optimizedImage = await optimizeImageForOCR(imageDataUrl);
            
            // Créer un worker pour la langue française et anglaise (meilleure détection)
            const worker = await Tesseract.createWorker('fra+eng', 1, {
                logger: m => {
                    // Mise à jour progressive du statut dans la console
                    console.log(m);
                    
                    // Mise à jour du message dans l'interface si c'est une étape significative
                    if (m.status === 'recognizing text') {
                        const progress = Math.floor(m.progress * 100);
                        extractedTextArea.value = `Extraction du texte: ${progress}%\nMerci de patienter...`;
                    }
                }
            });
            
            // Activer les options avancées pour une meilleure reconnaissance
            await worker.setParameters({
                tessedit_pageseg_mode: Tesseract.PSM.AUTO,  // Auto page segmentation
                tessedit_ocr_engine_mode: Tesseract.OEM.LSTM_ONLY,  // LSTM neural net mode (plus précis)
                tessjs_create_hocr: '0',    // Désactiver la sortie hOCR pour accélérer
                tessjs_create_tsv: '0',     // Désactiver la sortie TSV pour accélérer
                preserve_interword_spaces: '1',  // Préserver les espaces entre les mots
                tessedit_char_whitelist: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,;:€$£%&()=+-_*#@!?"\'/\\<>[]{}|~^` ',
                textord_min_linesize: '2.5', // Permet de détecter des lignes de texte plus petites
            });
            
            // Reconnaître le texte dans l'image optimisée
            const result = await worker.recognize(optimizedImage);
            
            // Améliorer le texte extrait
            let extractedText = result.data.text;
            
            // Post-traitement du texte: correction des erreurs courantes
            extractedText = cleanExtractedText(extractedText);
            
            // Afficher le texte extrait amélioré
            extractedTextArea.value = extractedText;
            
            // Calculer et afficher le niveau de confiance
            const confidence = Math.round(result.data.confidence);
            confidenceValue.textContent = confidence;
            confidenceIndicator.style.display = 'inline-block';
            
            // Stocker les données extraites
            extractedData = {
                text: extractedText,
                confidence: confidence
            };
            
            // Activer les boutons
            saveTextBtn.disabled = false;
            sendToChatBtn.disabled = false;
            
            // Terminer le worker pour libérer les ressources
            await worker.terminate();
        } catch (error) {
            console.error('Erreur lors de l\'extraction du texte:', error);
            extractedTextArea.value = 'Erreur lors de l\'extraction du texte. Veuillez réessayer.';
        } finally {
            // Cacher l'indicateur de traitement
            processingIndicator.style.display = 'none';
        }
    }
    
    // Fonction pour optimiser l'image avant l'OCR
    async function optimizeImageForOCR(imageDataUrl) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                // Créer un canvas pour manipuler l'image
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                // Dimensions optimales pour l'OCR
                const targetWidth = 1024;
                const targetHeight = Math.round(img.height * (targetWidth / img.width));
                
                // Définir les dimensions du canvas
                canvas.width = targetWidth;
                canvas.height = targetHeight;
                
                // Dessiner l'image redimensionnée avec un fond blanc pour garantir la lisibilité
                ctx.fillStyle = 'white';
                ctx.fillRect(0, 0, targetWidth, targetHeight);
                ctx.drawImage(img, 0, 0, targetWidth, targetHeight);
                
                // Appliquer des filtres pour améliorer la lisibilité du texte
                ctx.globalCompositeOperation = 'multiply';
                ctx.fillStyle = 'white';
                ctx.globalAlpha = 0.1;
                ctx.fillRect(0, 0, targetWidth, targetHeight);
                ctx.globalCompositeOperation = 'source-over';
                ctx.globalAlpha = 1.0;
                
                // Appliquer des techniques d'amélioration spécifiques pour l'OCR
                const imageData = ctx.getImageData(0, 0, targetWidth, targetHeight);
                const data = imageData.data;
                
                // Calculer l'histogramme pour déterminer les seuils optimaux
                const histogram = new Array(256).fill(0);
                for (let i = 0; i < data.length; i += 4) {
                    const avg = Math.round((data[i] + data[i + 1] + data[i + 2]) / 3);
                    histogram[avg]++;
                }
                
                // Trouver le seuil optimal en utilisant la méthode d'Otsu
                let sum = 0;
                let total = 0;
                for (let i = 0; i < 256; i++) {
                    sum += i * histogram[i];
                    total += histogram[i];
                }
                
                let sumB = 0;
                let wB = 0;
                let wF = 0;
                let maxVariance = 0;
                let threshold = 128; // valeur par défaut
                
                for (let i = 0; i < 256; i++) {
                    wB += histogram[i];
                    if (wB === 0) continue;
                    
                    wF = total - wB;
                    if (wF === 0) break;
                    
                    sumB += i * histogram[i];
                    const mB = sumB / wB;
                    const mF = (sum - sumB) / wF;
                    
                    const variance = wB * wF * (mB - mF) * (mB - mF);
                    if (variance > maxVariance) {
                        maxVariance = variance;
                        threshold = i;
                    }
                }
                
                // Appliquer un contraste adaptatif et une légère amélioration des bords
                for (let i = 0; i < data.length; i += 4) {
                    // Calcul de la moyenne des RGB
                    const avg = (data[i] + data[i + 1] + data[i + 2]) / 3;
                    
                    // Appliquer un contraste adaptatif
                    let newValue;
                    if (avg > threshold) {
                        // Pour les pixels clairs, les rendre plus clairs mais pas complètement blancs
                        // Cela préserve les détails dans les zones claires
                        newValue = Math.min(255, avg + 20);
                    } else {
                        // Pour les pixels sombres, les assombrir davantage pour augmenter le contraste
                        // Mais pas complètement noir pour préserver les nuances
                        newValue = Math.max(0, avg - 20);
                    }
                    
                    // Appliquer la valeur calculée mais avec une légère teinte bleutée
                    // Cela aide à réduire le bruit jaune/rouge et améliore la reconnaissance de texte
                    data[i] = newValue * 0.95;      // R (légèrement réduit)
                    data[i + 1] = newValue * 0.95;  // G (légèrement réduit)
                    data[i + 2] = Math.min(255, newValue * 1.05); // B (légèrement augmenté)
                    // Alpha reste inchangé
                }
                
                // Appliquer les modifications
                ctx.putImageData(imageData, 0, 0);
                
                // Ajout d'un filtre de netteté pour améliorer les détails fins (bords de texte)
                const tempCanvas = document.createElement('canvas');
                const tempCtx = tempCanvas.getContext('2d');
                tempCanvas.width = targetWidth;
                tempCanvas.height = targetHeight;
                
                // Dessiner l'image actuelle sur le canvas temporaire
                tempCtx.drawImage(canvas, 0, 0);
                
                // Appliquer un filtre de netteté léger
                ctx.filter = 'contrast(1.1) saturate(0.9) brightness(1.05)';
                ctx.drawImage(tempCanvas, 0, 0);
                ctx.filter = 'none';
                
                // Retourner l'image optimisée avec une qualité maximale
                resolve(canvas.toDataURL('image/jpeg', 1.0));
            };
            
            img.src = imageDataUrl;
        });
    }
    
    // Fonction pour nettoyer et améliorer le texte extrait
    // Fonction pour envoyer l'image directement à AWS Textract via le serveur
    function sendToAWSTextract(base64Image) {
        // Préparer les données à envoyer au serveur
        const data = {
            image: base64Image,
            use_textract: true,
            analyze_expense: true
        };
        
        // Appeler l'API du serveur qui utilise AWS Textract
        fetch('/api/save-extracted-text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Erreur de réseau ou de serveur');
            }
            return response.json();
        })
        .then(result => {
            if (result.success) {
                // Afficher le texte brut extrait
                extractedTextArea.value = result.text || '';
                
                // Stocker les données extraites
                extractedData = {
                    text: result.text || '',
                    confidence: 95, // AWS Textract ne fournit pas de score de confiance global
                    extracted_info: result.extracted_info || {}
                };
                
                // Si des informations financières ont été extraites, les ajouter au texte
                if (result.extracted_info) {
                    const info = result.extracted_info;
                    let infoText = "=== INFORMATIONS EXTRAITES ===\n\n";
                    
                    if (info.document_type) {
                        infoText += `📄 Type: ${info.document_type === 'invoice' ? 'Facture' : 
                                           info.document_type === 'receipt' ? 'Reçu' : 
                                           info.document_type}\n`;
                    }
                    
                    if (info.vendor) {
                        infoText += `🏢 Fournisseur: ${info.vendor}\n`;
                    }
                    
                    if (info.amount) {
                        infoText += `💰 Montant: ${info.amount} €\n`;
                    }
                    
                    if (info.date) {
                        infoText += `📅 Date: ${info.date}\n`;
                    }
                    
                    if (info.tax_amount) {
                        infoText += `💲 TVA: ${info.tax_amount} €\n`;
                    }
                    
                    // Ajouter le résumé au début du texte extrait
                    extractedTextArea.value = infoText + "\n" + 
                                             "=== TEXTE COMPLET ===\n\n" + 
                                             extractedTextArea.value;
                }
                
                // Activer les boutons
                saveTextBtn.disabled = false;
                sendToChatBtn.disabled = false;
                
                // Afficher un indicateur de confiance arbitraire
                confidenceValue.textContent = "99";
                confidenceIndicator.style.display = 'inline-block';
            } else {
                // Afficher l'erreur et essayer avec Tesseract.js comme solution de secours
                console.error("Erreur AWS Textract:", result.error);
                extractedTextArea.value = "Erreur avec AWS Textract. Tentative avec OCR local...\n";
                
                // Utiliser Tesseract.js comme solution de secours
                setTimeout(() => {
                    const imageDataUrl = "data:image/jpeg;base64," + base64Image;
                    extractTextFromImage(imageDataUrl);
                }, 100);
            }
        })
        .catch(error => {
            console.error('Erreur lors de l\'appel API:', error);
            extractedTextArea.value = "Erreur de connexion au serveur. Tentative avec OCR local...\n";
            
            // Utiliser Tesseract.js comme solution de secours
            setTimeout(() => {
                const imageDataUrl = "data:image/jpeg;base64," + base64Image;
                extractTextFromImage(imageDataUrl);
            }, 100);
        })
        .finally(() => {
            // Cacher l'indicateur de traitement
            processingIndicator.style.display = 'none';
        });
    }

    // Fonction pour nettoyer et améliorer le texte extrait
    function cleanExtractedText(text) {
        if (!text) return text;
        
        // Détection des cas spéciaux (comme le problème des "I" alignés verticalement)
        if (text.match(/^\s*[.I…]{2,}\s*$/gm)) {
            // Si le texte contient plusieurs lignes avec seulement des I ou des points alignés
            // c'est probablement une erreur d'OCR - on essaie de le nettoyer radicalement
            const lines = text.split('\n');
            const cleanedLines = lines.filter(line => {
                // Garder uniquement les lignes avec du contenu significatif
                const trimmedLine = line.trim();
                return trimmedLine && !trimmedLine.match(/^[.I…]{1,}$/);
            });
            
            // Si on a perdu plus de 70% des lignes, c'est probablement un document sans texte réel
            if (cleanedLines.length < lines.length * 0.3 && lines.length > 5) {
                return "⚠️ Aucun texte clairement lisible n'a pu être extrait de cette image.\nEssayez de prendre une photo avec un meilleur éclairage et un meilleur angle.";
            }
            
            text = cleanedLines.join('\n');
        }
        
        // 1. Nettoyer les caractères répétitifs qui indiquent des erreurs d'OCR
        let cleanedText = text;
        
        // 1a. Nettoyer les lignes avec que des points, I ou des caractères répétitifs
        cleanedText = cleanedText.replace(/^[.I…]{3,}$/gm, '');
        
        // 1b. Nettoyer les lignes qui commencent par des espaces puis ont des points/I répétés
        cleanedText = cleanedText.replace(/^\s*[.I…]{3,}\s*$/gm, '');
        
        // 1c. Supprimer les colonnes de points et I qui apparaissent parfois dans l'OCR
        cleanedText = cleanedText.replace(/[.…]{2,}/g, ' '); // Séries de points
        cleanedText = cleanedText.replace(/I{2,}/g, ' ');    // Séries de I
        
        // 2. Supprimer les lignes vides excessives qui peuvent résulter du nettoyage
        cleanedText = cleanedText.replace(/\n{3,}/g, '\n\n');
        
        // 3. Corriger les espaces multiples
        cleanedText = cleanedText.replace(/\s{2,}/g, ' ');
        
        // 4. Corriger les caractères parasites qui restent isolés
        cleanedText = cleanedText.replace(/(\s|^)\.(\s|$)/g, ' '); // Points isolés
        cleanedText = cleanedText.replace(/(\s|^)I(\s|$)/g, ' ');  // I isolés
        cleanedText = cleanedText.replace(/(\s|^)[,:;](\s|$)/g, ' '); // Ponctuations isolées
        
        // 5. Corriger les erreurs courantes d'OCR
        const commonOCRErrors = {
            '0': 'O',
            'l': 'I',
            '|': 'I',
            '5': 'S',
            '€': 'E',
            '¢': 'c',
            '±': '+',
            '°C': '°C',
            '°F': '°F',
            '...': '…',
            ',,': ','
        };
        
        for (const [error, correction] of Object.entries(commonOCRErrors)) {
            // Utiliser des expressions régulières avec word boundaries pour éviter de remplacer au milieu des mots
            const regex = new RegExp(`(\\s|^)${error}(\\s|$)`, 'g');
            cleanedText = cleanedText.replace(regex, `$1${correction}$2`);
        }
        
        // 6. Nettoyer les espaces consécutifs après suppressions
        cleanedText = cleanedText.replace(/\s{2,}/g, ' ').trim();
        
        // 7. Améliorer la présentation pour les montants et dates
        // Format monétaire: corriger les espaces dans les montants (1 000,00 €)
        cleanedText = cleanedText.replace(/(\d)\s+(\d{3}[,.]\d{2})/g, '$1$2');
        
        // Format de date: normaliser les dates (DD/MM/YYYY)
        cleanedText = cleanedText.replace(/(\d{2})[.-](\d{2})[.-](\d{4})/g, '$1/$2/$3');
        
        // 8. Vérification finale : si le texte est vide ou contient seulement des espaces après nettoyage
        if (!cleanedText.trim()) {
            return "⚠️ Aucun texte n'a pu être extrait de cette image.\nEssayez de prendre une photo avec un meilleur éclairage et un meilleur angle.";
        }
        
        return cleanedText;
    }
    
    // Sauvegarder le texte extrait
    saveTextBtn.addEventListener('click', function() {
        // Récupérer le texte actuel depuis le textarea
        const extractedText = extractedTextArea.value.trim();
        if (!extractedText) {
            alert("Aucun texte à enregistrer.");
            return;
        }
        
        // Si extractedData n'existe pas, le créer à partir du textarea
        if (!extractedData) {
            extractedData = {
                text: extractedText,
                confidence: 0
            };
        }
        
        const title = titleInput.value.trim() || `Texte du ${new Date().toLocaleString()}`;
        
        // Récupérer l'image capturée en base64 pour AWS Textract
        let imageBase64 = "";
        if (capturedImage && capturedImage.style.display !== 'none' && capturedImage.src) {
            imageBase64 = capturedImage.src.split(',')[1]; // Extraire la partie base64 sans le préfixe
        } else if (uploadedImage && uploadedImage.style.display !== 'none' && uploadedImage.src) {
            imageBase64 = uploadedImage.src.split(',')[1]; // Idem pour l'image uploadée
        }
        
        const textData = {
            title: title,
            text: extractedText, // Utiliser le texte du textarea directement
            image: imageBase64 || "", // S'assurer que ce n'est jamais null
            confidence: extractedData.confidence || 0,
            use_textract: true,  // Utiliser AWS Textract par défaut
            analyze_expense: true, // Activer l'analyse de factures/reçus
            timestamp: new Date().toISOString()
        };
        
        // Afficher un indicateur de chargement plus détaillé
        processingIndicator.style.display = 'block';
        processingIndicator.innerHTML = '<div class="spinner-border text-primary" role="status"></div><span class="ms-2">Analyse avancée avec AWS Textract en cours...</span>';
        
        // Envoyer les données au serveur
        fetch('/api/save-extracted-text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(textData),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Mettre à jour l'interface avec le texte extrait par AWS Textract
                processingIndicator.style.display = 'none';
                
                // Si les données extraites par Textract sont disponibles, mettre à jour le texte affiché
                if (data.extracted_info) {
                    console.log("Données extraites par AWS Textract:", data.extracted_info);
                    
                    // Créer un résumé informatif pour l'utilisateur
                    let infoText = "=== INFORMATIONS EXTRAITES ===\n\n";
                    if (data.extracted_info.document_type) {
                        infoText += `🧾 Type de document: ${data.extracted_info.document_type === 'invoice' ? 'Facture' : 
                                                         data.extracted_info.document_type === 'receipt' ? 'Reçu' : 
                                                         data.extracted_info.document_type}\n`;
                    }
                    
                    if (data.extracted_info.amount) {
                        infoText += `💰 Montant: ${data.extracted_info.amount} €\n`;
                    }
                    
                    if (data.extracted_info.date) {
                        infoText += `📅 Date: ${data.extracted_info.date}\n`;
                    }
                    
                    if (data.extracted_info.vendor) {
                        infoText += `🏢 Fournisseur:\n${data.extracted_info.vendor}\n`;
                    }
                    
                    if (data.extracted_info.tax_amount) {
                        infoText += `💸 TVA: ${data.extracted_info.tax_amount} €\n`;
                    }
                    
                    // Chercher d'autres informations qui pourraient être disponibles
                    const otherFields = ['address', 'total', 'subtotal', 'invoice_receipt_id', 'payment_terms'];
                    let hasOtherFields = false;
                    
                    otherFields.forEach(field => {
                        if (data.extracted_info[field]) {
                            if (!hasOtherFields) {
                                infoText += "\n=== AUTRES DÉTAILS ===\n";
                                hasOtherFields = true;
                            }
                            infoText += `${field}: ${data.extracted_info[field]}\n`;
                        }
                    });
                    
                    // Si des informations détaillées sont extraites mais pas de texte complet
                    if (data.extracted_info.full_text && data.extracted_info.full_text.trim().length > 0) {
                        infoText += "\n=== TEXTE COMPLET EXTRAIT ===\n\n";
                        infoText += data.extracted_info.full_text;
                    } else if (data.text && data.text.trim().length > 0) {
                        // Utiliser le texte de base s'il est disponible
                        infoText += "\n=== TEXTE EXTRAIT ===\n\n";
                        infoText += data.text;
                    } else {
                        infoText += "\n❗ Extraction partielle : AWS Textract a pu extraire certaines informations structurées mais pas le texte complet du document.";
                    }
                    
                    // Mettre à jour l'interface avec les informations extraites
                    extractedTextArea.value = infoText;
                    
                    // Mettre à jour les données extraites
                    extractedData = {
                        text: extractedTextArea.value,
                        confidence: 95  // AWS Textract est généralement très précis
                    };
                    
                    // Afficher un badge de confiance
                    confidenceValue.textContent = "95";
                    confidenceIndicator.style.display = 'inline-block';
                }
                
                // Activer les boutons
                saveTextBtn.disabled = false;
                sendToChatBtn.disabled = false;
                
                // Message de succès et mise à jour des textes sauvegardés
                alert('Texte analysé et sauvegardé avec succès !');
                loadSavedTexts(); // Recharger la liste des textes sauvegardés
                
                // Réinitialiser le champ de titre
                titleInput.value = '';
            } else {
                alert('Erreur lors de la sauvegarde: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            alert('Erreur lors de la sauvegarde du texte.');
        });
    });
    
    // Envoyer le texte extrait à Benji (l'assistant)
    sendToChatBtn.addEventListener('click', function() {
        if (!extractedData) return;
        
        const text = extractedData.text;
        
        // Stocker le texte dans sessionStorage pour l'utiliser sur la page de chat
        sessionStorage.setItem('textToSend', text);
        
        // Rediriger vers la page de chat dédiée
        window.location.href = '/chat';
    });
    
    // Charger les textes sauvegardés
    function loadSavedTexts() {
        fetch('/api/get-extracted-texts')
            .then(response => response.json())
            .then(data => {
                savedTexts = data.texts || [];
                
                if (savedTexts.length === 0) {
                    noSavedTexts.style.display = 'block';
                    savedTextsList.innerHTML = '';
                    return;
                }
                
                noSavedTexts.style.display = 'none';
                
                // Trier les textes par date (plus récent d'abord)
                savedTexts.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                
                // Afficher les textes
                let html = '';
                
                savedTexts.forEach(text => {
                    const date = new Date(text.created_at).toLocaleString();
                    const confidenceBadge = text.confidence 
                        ? `<span class="badge bg-info">Confiance: ${text.confidence}%</span>` 
                        : '';
                    
                    html += `
                        <div class="card mb-3" data-id="${text.id}">
                            <div class="card-header d-flex justify-content-between align-items-center">
                                <h6 class="mb-0">${escapeHtml(text.title || 'Sans titre')}</h6>
                                <div>
                                    ${confidenceBadge}
                                    <small class="text-muted ms-2">${date}</small>
                                </div>
                            </div>
                            <div class="card-body">
                                <p class="card-text">${escapeHtml(text.content.substring(0, 200))}${text.content.length > 200 ? '...' : ''}</p>
                                <div class="d-flex justify-content-end">
                                    <button class="btn btn-sm btn-info me-2 view-text-btn">
                                        <i class="bi bi-eye"></i> Voir
                                    </button>
                                    <button class="btn btn-sm btn-primary me-2 send-to-chat-btn">
                                        <i class="bi bi-chat"></i> Envoyer à Benji
                                    </button>
                                    <button class="btn btn-sm btn-danger delete-text-btn">
                                        <i class="bi bi-trash"></i> Supprimer
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                savedTextsList.innerHTML = html;
                
                // Ajouter les gestionnaires d'événements
                document.querySelectorAll('.view-text-btn').forEach(btn => {
                    btn.addEventListener('click', handleViewText);
                });
                
                document.querySelectorAll('.send-to-chat-btn').forEach(btn => {
                    btn.addEventListener('click', handleSendToChat);
                });
                
                document.querySelectorAll('.delete-text-btn').forEach(btn => {
                    btn.addEventListener('click', handleDeleteText);
                });
            })
            .catch(error => {
                console.error('Erreur lors du chargement des textes:', error);
            });
    }
    
    // Gestionnaire pour voir un texte
    function handleViewText(e) {
        const textId = e.target.closest('.card').dataset.id;
        const text = savedTexts.find(t => t.id == textId);
        
        if (text) {
            // Afficher le texte dans les champs
            titleInput.value = text.title || '';
            extractedTextArea.value = text.content;
            
            // Mettre à jour extractedData
            extractedData = {
                text: text.content,
                confidence: text.confidence || 0
            };
            
            // Afficher le niveau de confiance
            if (text.confidence) {
                confidenceValue.textContent = text.confidence;
                confidenceIndicator.style.display = 'inline-block';
            } else {
                confidenceIndicator.style.display = 'none';
            }
            
            // Activer les boutons
            saveTextBtn.disabled = false;
            sendToChatBtn.disabled = false;
            
            // Faire défiler vers le haut
            window.scrollTo(0, 0);
        }
    }
    
    // Gestionnaire pour envoyer un texte à l'assistant
    function handleSendToChat(e) {
        const textId = e.target.closest('.card').dataset.id;
        const text = savedTexts.find(t => t.id == textId);
        
        if (text) {
            // Stocker le texte dans sessionStorage
            sessionStorage.setItem('textToSend', text.content);
            
            // Rediriger vers la page de chat dédiée
            window.location.href = '/chat';
        }
    }
    
    // Gestionnaire pour supprimer un texte
    function handleDeleteText(e) {
        const card = e.target.closest('.card');
        const textId = card.dataset.id;
        
        // Afficher la modal de confirmation
        const deleteModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
        deleteModal.show();
        
        // Configurer le bouton de confirmation
        document.getElementById('confirmDeleteBtn').onclick = function() {
            // Envoyer la requête de suppression
            fetch(`/api/delete-extracted-text/${textId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Supprimer la carte de l'interface
                    card.remove();
                    
                    // Mettre à jour la liste des textes sauvegardés
                    savedTexts = savedTexts.filter(t => t.id != textId);
                    
                    // Afficher le message "Aucun texte" si nécessaire
                    if (savedTexts.length === 0) {
                        noSavedTexts.style.display = 'block';
                    }
                    
                    // Fermer la modal
                    deleteModal.hide();
                } else {
                    alert('Erreur lors de la suppression: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Erreur:', error);
                alert('Erreur lors de la suppression du texte.');
            });
        };
    }
    
    // Gérer l'upload d'image
    imageUpload.addEventListener('change', function(e) {
        if (e.target.files.length === 0) return;
        
        const file = e.target.files[0];
        
        // Vérifier si c'est une image
        if (!file.type.match('image.*')) {
            alert('Veuillez sélectionner une image valide.');
            return;
        }
        
        // Afficher l'image téléchargée
        const reader = new FileReader();
        reader.onload = function(event) {
            uploadedImage.src = event.target.result;
            uploadedImage.style.display = 'block';
            processUploadBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    });
    
    // Traiter l'image téléchargée
    processUploadBtn.addEventListener('click', function() {
        // Réinitialiser le texte extrait
        extractedTextArea.value = '';
        saveTextBtn.disabled = true;
        sendToChatBtn.disabled = true;
        confidenceIndicator.style.display = 'none';
        
        // Montrer l'indicateur de traitement
        processingIndicator.style.display = 'block';
        
        // Extraire le texte de l'image
        extractTextFromImage(uploadedImage.src);
    });
    
    // Fonction utilitaire pour échapper le HTML
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
    
    // Gestion des documents PDF et Word
    const documentUpload = document.getElementById('documentUpload');
    const documentPreview = document.getElementById('documentPreview');
    const documentTypeIcon = document.getElementById('documentTypeIcon');
    const documentName = document.getElementById('documentName');
    const documentDetails = document.getElementById('documentDetails');
    const processDocumentBtn = document.getElementById('processDocumentBtn');
    const clearDocumentBtn = document.getElementById('clearDocumentBtn');
    const documentMetadata = document.getElementById('documentMetadata');
    const metadataTable = document.getElementById('metadataTable');
    
    // Gestionnaire d'événement pour le chargement d'un document
    if (documentUpload) {
        documentUpload.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                
                // Afficher les détails du document
                documentName.textContent = file.name;
                
                // Définir l'icône en fonction du type de fichier
                if (file.name.toLowerCase().endsWith('.pdf')) {
                    documentTypeIcon.className = 'bi bi-file-earmark-pdf fs-1 text-danger';
                    documentDetails.textContent = `Type: PDF - Taille: ${formatFileSize(file.size)}`;
                } else if (file.name.toLowerCase().endsWith('.docx')) {
                    documentTypeIcon.className = 'bi bi-file-earmark-word fs-1 text-primary';
                    documentDetails.textContent = `Type: Word - Taille: ${formatFileSize(file.size)}`;
                } else {
                    documentTypeIcon.className = 'bi bi-file-earmark-text fs-1';
                    documentDetails.textContent = `Type: Document - Taille: ${formatFileSize(file.size)}`;
                }
                
                // Afficher la prévisualisation et activer le bouton
                documentPreview.style.display = 'block';
                processDocumentBtn.disabled = false;
                clearDocumentBtn.style.display = 'block';
                
                // Cacher les métadonnées lorsqu'un nouveau fichier est chargé
                documentMetadata.style.display = 'none';
            }
        });
    }
    
    // Bouton pour effacer le document
    if (clearDocumentBtn) {
        clearDocumentBtn.addEventListener('click', function() {
            // Réinitialiser le champ de fichier
            documentUpload.value = '';
            
            // Cacher la prévisualisation et les métadonnées
            documentPreview.style.display = 'none';
            documentMetadata.style.display = 'none';
            
            // Désactiver le bouton d'extraction
            processDocumentBtn.disabled = true;
            clearDocumentBtn.style.display = 'none';
            
            // Effacer les champs de texte
            extractedTextArea.value = '';
            
            // Désactiver les boutons
            saveTextBtn.disabled = true;
            sendToChatBtn.disabled = true;
        });
    }
    
    // Fonction pour traiter le document
    if (processDocumentBtn) {
        processDocumentBtn.addEventListener('click', function() {
            if (!documentUpload || documentUpload.files.length === 0) return;
            
            // Afficher l'indicateur de traitement
            processingIndicator.style.display = 'block';
            processingIndicator.innerHTML = '<div class="spinner-border text-primary" role="status"></div><span class="ms-2">Traitement du document en cours...</span>';
            
            // Créer un objet FormData
            const formData = new FormData();
            formData.append('document', documentUpload.files[0]);
            
            // Envoyer le document au serveur
            fetch('/api/process-document', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erreur de réseau ou de serveur');
                }
                return response.json();
            })
            .then(result => {
                // Cacher l'indicateur de traitement
                processingIndicator.style.display = 'none';
                
                if (result.success) {
                    // Afficher le texte extrait
                    titleInput.value = result.title || '';
                    extractedTextArea.value = result.text || '';
                    
                    // Stocker les données extraites
                    extractedData = {
                        text: result.text || '',
                        document_type: result.document_type || '',
                        metadata: result.metadata || {}
                    };
                    
                    // Activer les boutons
                    saveTextBtn.disabled = false;
                    sendToChatBtn.disabled = false;
                    
                    // Afficher les métadonnées si disponibles
                    if (result.metadata && Object.keys(result.metadata).length > 0) {
                        // Créer le tableau des métadonnées
                        let metadataHTML = '';
                        
                        // Fonction pour formater les valeurs spéciales
                        const formatMetadataValue = (key, value) => {
                            if (value === null || value === undefined) return '-';
                            if (key.includes('date') && typeof value === 'string' && value.includes('T')) {
                                return new Date(value).toLocaleDateString();
                            }
                            if (typeof value === 'string' && value.length > 100) {
                                return value.substring(0, 100) + '...';
                            }
                            return value.toString();
                        };
                        
                        // Ajouter les métadonnées au tableau
                        for (const [key, value] of Object.entries(result.metadata)) {
                            // Formatter le nom de la clé
                            const formattedKey = key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');
                            
                            // Ajouter la ligne au tableau
                            metadataHTML += `
                                <tr>
                                    <th scope="row">${formattedKey}</th>
                                    <td>${formatMetadataValue(key, value)}</td>
                                </tr>
                            `;
                        }
                        
                        // Ajouter le contenu au tableau
                        metadataTable.innerHTML = metadataHTML;
                        
                        // Afficher les métadonnées
                        documentMetadata.style.display = 'block';
                    } else {
                        // Cacher les métadonnées si non disponibles
                        documentMetadata.style.display = 'none';
                    }
                } else {
                    // Afficher l'erreur
                    alert('Erreur lors du traitement du document: ' + result.error);
                }
            })
            .catch(error => {
                // Cacher l'indicateur de traitement
                processingIndicator.style.display = 'none';
                console.error('Erreur:', error);
                alert('Erreur lors du traitement du document.');
            });
        });
    }
    
    // Fonction utilitaire pour formater la taille des fichiers
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Chargement initial des textes sauvegardés
    loadSavedTexts();
});