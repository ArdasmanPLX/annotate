from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
from database import DatabaseManager
from annotation import AnnotationManager
from config import DEFAULT_PROMPT
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
db_manager = DatabaseManager()
annotation_manager = AnnotationManager()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
def index():
    annotations = db_manager.get_all_annotations()
    return render_template('index.html', annotations=annotations, default_prompt=DEFAULT_PROMPT)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/annotate', methods=['POST'])
def annotate_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image = request.files['image']
    annotation = request.form.get('annotation', '')

    if not annotation:
        return jsonify({"error": "No annotation provided"}), 400

    filename = secure_filename(image.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image.save(save_path)

    db_manager.insert_annotation(save_path, annotation)
    if 'text/html' in request.headers.get('Accept', ''):
        return redirect(url_for('index'))
    return jsonify({"message": "Image received and annotation saved", "annotation": annotation}), 200

@app.route('/auto_annotate', methods=['POST'])
def auto_annotate_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image = request.files['image']
    prompt = request.form.get('prompt', DEFAULT_PROMPT)
    model = request.form.get('model', 'gpt-4-turbo-2024-04-09')

    filename = secure_filename(image.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image.save(save_path)

    try:
        annotation = annotation_manager.generate_annotation(save_path, prompt, model)
        db_manager.insert_annotation(save_path, annotation)
        if 'text/html' in request.headers.get('Accept', ''):
            return redirect(url_for('index'))
        return jsonify({"message": "Image auto-annotated", "annotation": annotation}), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred during auto-annotation: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(port=5000)

