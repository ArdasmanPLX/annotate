OPENAI_API_KEY = ""
DEFAULT_PROMPT = "1. Begin with the special word: gsai, illustration. 2. The description should be short and concise but contain all key requirements. 3. Requirements: Highlight and describe the main objects in the image that are in the foreground. Then, describe the secondary objects, if any. Describe the background. Describe the atmsphere or mood of the image. Pay special attention to the light and shadows, and the nature of the lighting. Describe the lighting in detail. Describe the composition and the dynamic arrangement of the objects in the image. Describe the interactions between the objects in the image. Pay attention to the time of day, season, natural environment, weather, etc. If there is a character in the image, describe them in detail (appearance, physique, emotions, clothing details). Briefly describe the narrative of the image, if there is a story being told. 4. Write the whole thing in one paragraph"

# Default settings used for image generation via ComfyUI
COMFY_DEFAULTS = {
    "server": "http://localhost:8188",
    "model": "",
    "width": 512,
    "height": 512,
    "steps": 20,
    "workflow": ""
}
