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

If your ComfyUI server requires authentication, provide the token via
`COMFYUI_API_KEY`:

```bash
export COMFYUI_API_KEY="your-comfy-token"
```

The interface exposes:

- **Manual Annotation** – upload an image and manually enter annotation text.
- **Auto Annotation** – upload an image and let the OpenAI model generate an annotation.
- **Approved Annotations** – view annotations that were approved in the database.

## ComfyUI Image Generation

The "Генерация изображений" tab allows you to send a workflow JSON to a
running ComfyUI server. Field names for prompt, model, width, height, steps and
seed may differ between workflows. You can specify the desired field name and
node number for each parameter before generating images. For example:

```
prompt field: text      node: 7
model field: unet_name  node: 8
width field: width      node: 10
height field: height    node: 10
steps field: steps      node: 14
seed field: noise_seed  node: 12
```

These values are stored in `comfy_settings.json` and reused on next launch.

## Other Interfaces

The repository also contains a PyQt application (`main.py`).

