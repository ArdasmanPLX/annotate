import os
import uuid
import json
import requests

class ComfyUIClient:
    def __init__(self, server: str):
        self.server = server.rstrip('/')

    def set_server(self, server: str):
        self.server = server.rstrip('/')

    def generate_image(self, prompt: str, model: str, width: int, height: int, steps: int, workflow: str) -> str:
        payload = {
            "prompt": prompt,
            "model": model,
            "width": width,
            "height": height,
            "steps": steps,
            "workflow": json.loads(workflow) if workflow else {}
        }
        resp = requests.post(f"{self.server}/generate", json=payload)
        resp.raise_for_status()

        out_dir = os.path.join(os.path.dirname(__file__), "generated")
        os.makedirs(out_dir, exist_ok=True)
        file_path = os.path.join(out_dir, f"{uuid.uuid4().hex}.png")
        with open(file_path, "wb") as f:
            f.write(resp.content)
        return file_path
