import gradio as gr
from database import DatabaseManager
from annotation import AnnotationManager
from config import DEFAULT_PROMPT


db_manager = DatabaseManager()
annotation_manager = AnnotationManager()


def manual_annotation(image, annotation):
    if image is None or not annotation:
        return "No image or annotation provided"
    db_manager.insert_or_update_annotation(image, annotation)
    return "Annotation saved"


def auto_annotation(image, prompt=DEFAULT_PROMPT, model="gpt-4-turbo"):
    if image is None:
        return "No image provided"
    if not prompt:
        prompt = DEFAULT_PROMPT
    annotation = annotation_manager.generate_annotation(image, prompt, model)
    db_manager.insert_or_update_annotation(image, annotation)
    return annotation


def list_approved_annotations():
    rows = db_manager.get_approved_annotations() or []
    return rows


def build_interface():
    manual = gr.Interface(
        fn=manual_annotation,
        inputs=[gr.Image(type="filepath"), gr.Textbox(label="Annotation")],
        outputs="text",
        title="Manual Annotation",
    )

    auto = gr.Interface(
        fn=auto_annotation,
        inputs=[gr.Image(type="filepath"), gr.Textbox(value=DEFAULT_PROMPT, label="Prompt"), gr.Textbox(value="gpt-4-turbo", label="Model")],
        outputs="text",
        title="Auto Annotation",
    )

    approved = gr.Interface(
        fn=list_approved_annotations,
        inputs=[],
        outputs="dataframe",
        title="Approved Annotations",
    )

    return gr.TabbedInterface([manual, auto, approved], ["Manual", "Auto", "Approved"])


def main():
    iface = build_interface()
    iface.launch()


if __name__ == "__main__":
    main()

