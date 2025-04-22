from flask import Blueprint, render_template, send_from_directory, jsonify, request
import os
from generate_powerpoint import create_powerpoint_from_html

# Créer le Blueprint
export_ppt_bp = Blueprint('export_powerpoint', __name__)

@export_ppt_bp.route('/presentation/export-powerpoint', methods=['GET'])
def export_powerpoint_page():
    """Page d'interface pour l'exportation en PowerPoint"""
    return render_template('presentation/export_powerpoint.html')

@export_ppt_bp.route('/presentation/generate-powerpoint', methods=['POST'])
def generate_powerpoint():
    """Génère le fichier PowerPoint et retourne le chemin pour téléchargement"""
    language = request.form.get('language', 'fr')
    
    # Vérifier si le dossier 'downloads' existe, sinon le créer
    download_dir = 'downloads'
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    # Définir le chemin source et le chemin de sortie
    if language == 'en':
        html_path = "presentation/preview_en.html"
        output_path = f"{download_dir}/presentation-ia-solution-en.pptx"
    else:
        html_path = "presentation/preview.html"
        output_path = f"{download_dir}/presentation-ia-solution-fr.pptx"
    
    try:
        # Générer le fichier PowerPoint
        created_file = create_powerpoint_from_html(html_path, output_path, language)
        
        # Retourner le nom du fichier pour téléchargement
        return jsonify({
            'success': True,
            'filename': os.path.basename(created_file),
            'message': 'Présentation PowerPoint générée avec succès' if language == 'fr' else 'PowerPoint presentation successfully generated'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f"Erreur lors de la génération du PowerPoint: {str(e)}" if language == 'fr' else f"Error generating PowerPoint: {str(e)}"
        }), 500

@export_ppt_bp.route('/downloads/<filename>', methods=['GET'])
def download_file(filename):
    """Téléchargement du fichier généré"""
    return send_from_directory('downloads', filename, as_attachment=True)

def init_app(app):
    """Initialiser les routes pour l'exportation PowerPoint"""
    app.register_blueprint(export_ppt_bp)
    
    # Créer le dossier de téléchargement s'il n'existe pas
    download_dir = 'downloads'
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)