from flask import Flask, request, jsonify
from database import DatabaseManager
from annotation import AnnotationManager
from config import DEFAULT_PROMPT
import os

app = Flask(__name__)
db_manager = DatabaseManager()
annotation_manager = AnnotationManager()

@app.route('/annotate', methods=['POST'])
def annotate_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image = request.files['image']
    annotation = request.form.get('annotation', '')

    if not annotation:
        return jsonify({"error": "No annotation provided"}), 400

    # Save image to a temporary file
    temp_image_path = f"temp_{image.filename}"
    image.save(temp_image_path)

    # Save annotation to database
    db_manager.insert_annotation(temp_image_path, annotation)

    return jsonify({"message": "Image received and annotation saved", "annotation": annotation}), 200

@app.route('/auto_annotate', methods=['POST'])
def auto_annotate_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image = request.files['image']
    prompt = request.form.get('prompt', DEFAULT_PROMPT)
    model = request.form.get('model', 'gpt-4-turbo-2024-04-09')

    # Save image to a temporary file
    temp_image_path = f"temp_{image.filename}"
    image.save(temp_image_path)

    try:
        annotation = annotation_manager.generate_annotation(temp_image_path, prompt, model)
        db_manager.insert_annotation(temp_image_path, annotation)
        return jsonify({"message": "Image auto-annotated", "annotation": annotation}), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred during auto-annotation: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(port=5000)