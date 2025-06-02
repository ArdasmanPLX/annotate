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

Set the `HOST` and `PORT` environment variables to control where the
web server listens. By default, the app binds to `0.0.0.0` on port
`7860`, making it accessible on public platforms like Runpod.

Set the `OPENAI_API_KEY` environment variable to avoid interactive prompts:

```bash
export OPENAI_API_KEY="sk-..."
```

The interface exposes:

- **Manual Annotation** – upload an image and manually enter annotation text.
- **Auto Annotation** – upload an image and let the OpenAI model generate an annotation.
- **Approved Annotations** – view annotations that were approved in the database.

## Other Interfaces

The repository also contains a PyQt application (`main.py`).

