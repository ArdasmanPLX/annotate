# Annotate Application

This repository provides tools for annotating images using a graphical interface and a Gradio web UI.

## Installation

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Launch Gradio UI

Run the following command to start the Gradio interface:

```bash
python gradio_app.py
```

The interface exposes:

- **Manual Annotation** – upload an image and manually enter annotation text.
- **Auto Annotation** – upload an image and let the OpenAI model generate an annotation.
- **Approved Annotations** – view annotations that were approved in the database.

## Other Interfaces

The repository also contains a PyQt application (`main.py`).

