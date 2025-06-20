import os
import uuid
import json
import urllib.parse
import urllib.request
import websocket

class ComfyUIClient:
    def __init__(self, server: str):
        self.server = server.rstrip('/')

    def set_server(self, server: str):
        self.server = server.rstrip('/')

    def _queue_prompt(self, prompt: dict, client_id: str) -> str:
        data = json.dumps({"prompt": prompt, "client_id": client_id}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.server}/prompt",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req).read()
        return json.loads(resp)["prompt_id"]

    def _get_image(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        params = urllib.parse.urlencode(
            {"filename": filename, "subfolder": subfolder, "type": folder_type}
        )
        url = f"{self.server}/view?{params}"
        with urllib.request.urlopen(url) as resp:
            return resp.read()

    def generate_image(
        self,
        prompt: str,
        model: str,
        width: int,
        height: int,
        steps: int,
        workflow: str,
    ) -> str:
        """Generate an image using a ComfyUI server.

        The provided ``workflow`` JSON is sent directly to ComfyUI.
        ``prompt`` and other parameters should already be baked into the
        workflow by the user.
        """

        prompt_data = json.loads(workflow) if workflow else {}

        client_id = uuid.uuid4().hex

        ws_url = (
            self.server.replace("http://", "ws://")
            .replace("https://", "wss://")
            + f"/ws?clientId={client_id}"
        )

        ws = websocket.WebSocket()
        ws.connect(ws_url)

        prompt_id = self._queue_prompt(prompt_data, client_id)

        # wait for execution to finish
        while True:
            out = ws.recv()
            if isinstance(out, str):
                msg = json.loads(out)
                if msg.get("type") == "executing":
                    data = msg.get("data", {})
                    if data.get("node") is None and data.get("prompt_id") == prompt_id:
                        break
            else:
                continue

        history_req = urllib.request.urlopen(f"{self.server}/history/{prompt_id}")
        history = json.loads(history_req.read())[prompt_id]

        image_data = None
        for _node_id, node_output in history.get("outputs", {}).items():
            if "images" in node_output and node_output["images"]:
                img = node_output["images"][0]
                image_data = self._get_image(
                    img["filename"], img["subfolder"], img["type"]
                )
                break

        ws.close()

        if image_data is None:
            raise RuntimeError("No image data returned from ComfyUI")

        out_dir = os.path.join(os.path.dirname(__file__), "generated")
        os.makedirs(out_dir, exist_ok=True)
        file_path = os.path.join(out_dir, f"{uuid.uuid4().hex}.png")
        with open(file_path, "wb") as f:
            f.write(image_data)
        return file_path
