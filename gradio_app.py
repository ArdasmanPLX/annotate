import os
import json
import gradio as gr
from database import DatabaseManager
from annotation import AnnotationManager, available_models
from comfy_client import ComfyUIClient
from config import DEFAULT_PROMPT, COMFY_DEFAULTS

# Managers for annotations and image generation
_db = DatabaseManager()
_annotator = AnnotationManager()
_generation_settings = COMFY_DEFAULTS.copy()
_comfy = ComfyUIClient(_generation_settings.get("server", ""))

MODELS = available_models() or ["gpt-4-turbo"]


def _refresh_list():
    """Return annotation list in display format."""
    rows = _db.get_all_annotations() or []
    items = []
    for image_path, _ann, is_new, is_approved in rows:
        status = "[Approved]" if is_approved else "[Not Approved]" if not is_new else "[New]"
        items.append(f"{os.path.basename(image_path)} {status}")
    return gr.update(choices=items)


def load_image(image_path):
    if not image_path:
        return None, "", False, "No image selected"
    data = _db.get_annotation(image_path)
    annotation = data[0] if data else ""
    is_app = bool(data[1]) if data else False
    return image_path, annotation, is_app, "Image loaded"


def save_annotation(current_image, text):
    if not current_image or not text.strip():
        return "No image or annotation"
    _db.insert_or_update_annotation(current_image, text.strip())
    return "Annotation saved"


def auto_annotate(current_image, prompt, model):
    if not current_image:
        return "", "No image"
    prompt = prompt or DEFAULT_PROMPT
    annotation = _annotator.generate_annotation(current_image, prompt, model)
    _db.insert_or_update_annotation(current_image, annotation)
    return annotation, "Annotation generated"


def annotate_folder(files, prompt, model, progress=gr.Progress(track_tqdm=False)):
    if not files:
        return "No files provided"
    prompt = prompt or DEFAULT_PROMPT
    for i, file in enumerate(files, start=1):
        annotation = _annotator.generate_annotation(file.name, prompt, model)
        _db.insert_or_update_annotation(file.name, annotation)
        progress(i / len(files))
    return "Folder annotated"


def approve_annotation(current_image):
    if not current_image:
        return "No image"
    _db.update_annotation_status(current_image, True)
    return "Approved"


def not_approve_annotation(current_image):
    if not current_image:
        return "No image"
    _db.update_annotation_status(current_image, False)
    return "Not approved"


def approve_all():
    _db.approve_all_annotations()
    return "All annotations approved"


def save_changes(current_image, text):
    if not current_image:
        return "No image"
    _db.update_annotation(current_image, text.strip())
    return "Saved"


def clear_preview():
    return None, "", False


def clear_database():
    _db.clear_database()
    return "Database cleared"


def delete_annotation(current_image):
    if not current_image:
        return "No image"
    _db.delete_annotation(current_image)
    return "Annotation deleted"


def generate_text_files():
    rows = _db.get_approved_annotations() or []
    for image_path, ann in rows:
        txt_path = os.path.splitext(image_path)[0] + ".txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(ann)
    return f"Created {len(rows)} text files"


def export_database():
    rows = _db.get_all_annotations() or []
    return json.dumps([list(r) for r in rows], ensure_ascii=False, indent=2)


def import_database(file_obj):
    if not file_obj:
        return "No file"
    try:
        with open(file_obj.name, "r", encoding="utf-8") as f:
            data = json.load(f)
        _db.import_annotations(data)
    except Exception:
        return "Failed to import"
    return "Database imported"


def select_from_list(name_with_status):
    if not name_with_status:
        return None, "", False, ""
    name = name_with_status.split(" [")[0]
    result = _db.get_annotation_by_filename(name)
    if not result:
        return None, "", False, "Not found"
    annotation, is_app, path = result
    return path, annotation, bool(is_app), "Loaded"


def generate_image(server, model, steps, width, height, annotation_text):
    _generation_settings.update({
        "server": server,
        "model": model,
        "steps": steps,
        "width": width,
        "height": height,
    })
    _comfy.set_server(server)
    return _comfy.generate_image(annotation_text, model, width, height, steps, "")


def build_interface():
    with gr.Blocks() as demo:
        current_image = gr.State()
        status = gr.Textbox(label="Status", interactive=False)

        with gr.Tab("Аннотации"):
            model_select = gr.Dropdown(MODELS, value=MODELS[0], label="LLM Model")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("**Manual Annotation**")
                    image_input = gr.Image(label="Load Image", type="filepath")
                    save_btn = gr.Button("Save Annotation")
                with gr.Column():
                    gr.Markdown("**LLM Annotation**")
                    prompt_box = gr.Textbox(value=DEFAULT_PROMPT, label="Prompt")
                    annotate_btn = gr.Button("Annotate Image")
                    folder_input = gr.File(file_count="multiple", label="Annotate Folder")
                with gr.Column():
                    gr.Markdown("**Image Data Base**")
                    clear_db_btn = gr.Button("Clear Database")
                    delete_btn = gr.Button("Delete Annotation")
                    gen_txt_btn = gr.Button("Generate Text Files")
                    export_btn = gr.Button("Export Database")
                    import_file = gr.File(file_types=[".json"], label="Import Database")

            with gr.Row():
                with gr.Column(scale=2):
                    preview = gr.Image(label="Preview")
                    clear_preview_btn = gr.Button("Clear Preview")
                    annotation_box = gr.Textbox(lines=8, label="Annotation")
                    with gr.Row():
                        approve_btn = gr.Button("Approve")
                        approve_all_btn = gr.Button("Approve All")
                        not_approve_btn = gr.Button("Not Approved")
                        save_changes_btn = gr.Button("Save")
                with gr.Column():
                    annotation_list = gr.Dropdown(choices=[], label="Annotations")

            # Events
            image_input.upload(load_image, image_input, [preview, annotation_box, approve_btn, status],
                               show_progress=False).then(lambda p: p, None, current_image)
            save_btn.click(save_annotation, [current_image, annotation_box], status)
            annotate_btn.click(auto_annotate, [current_image, prompt_box, model_select], [annotation_box, status])
            folder_input.change(annotate_folder, [folder_input, prompt_box, model_select], status).then(_refresh_list, None, annotation_list, queue=False)
            approve_btn.click(approve_annotation, current_image, status)
            approve_all_btn.click(lambda: approve_all(), None, status)
            not_approve_btn.click(not_approve_annotation, current_image, status)
            save_changes_btn.click(save_changes, [current_image, annotation_box], status)
            clear_preview_btn.click(clear_preview, None, [preview, annotation_box, approve_btn])
            clear_db_btn.click(clear_database, None, status)
            delete_btn.click(delete_annotation, current_image, status)
            gen_txt_btn.click(generate_text_files, None, status)
            export_btn.click(export_database, None, status)
            import_file.change(import_database, import_file, status).then(_refresh_list, None, annotation_list, queue=False)
            annotation_list.change(select_from_list, annotation_list, [preview, annotation_box, approve_btn, status]).then(lambda p: p, None, current_image)
            demo.load(_refresh_list, None, annotation_list)

            # Refresh list after button actions
            for btn in [save_btn, annotate_btn, clear_db_btn, delete_btn, gen_txt_btn,
                        export_btn, approve_btn, approve_all_btn, not_approve_btn,
                        save_changes_btn]:
                btn.click(_refresh_list, None, annotation_list, queue=False)

            # File components trigger refresh after handling events above

        with gr.Tab("Генерация изображений"):
            server_in = gr.Textbox(value=_generation_settings["server"], label="Сервер генерации ComfyUI")
            model_in = gr.Textbox(value=_generation_settings.get("model", ""), label="Модель")
            steps_in = gr.Number(value=_generation_settings.get("steps", 20), label="Шаги (Steps)")
            width_in = gr.Number(value=_generation_settings.get("width", 512), label="Ширина")
            height_in = gr.Number(value=_generation_settings.get("height", 512), label="Высота")
            annotation_disp = gr.Textbox(lines=8, interactive=True, label="Аннотация")
            gen_btn = gr.Button("Generate")
            output_img = gr.Image(label="Result")
            with gr.Column():
                gen_list = gr.Dropdown(choices=[], label="Annotations")

            gen_list.change(select_from_list, gen_list, [None, annotation_disp, None, status]).then(lambda p: p, None, current_image)
            gen_btn.click(generate_image, [server_in, model_in, steps_in, width_in, height_in, annotation_disp], output_img)
            demo.load(_refresh_list, None, gen_list)

    return demo


def main():
    iface = build_interface()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "7860"))
    iface.launch(server_name=host, server_port=port)


if __name__ == "__main__":
    main()
