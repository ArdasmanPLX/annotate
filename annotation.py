import base64
from openai import OpenAI
from key_manager import get_openai_api_key

client = OpenAI(api_key=get_openai_api_key())


def available_models() -> list[str]:
    """Return a list of model identifiers available to the API key.

    If the request fails, an empty list is returned.
    """
    try:  # pragma: no cover - network call
        return [m.id for m in client.models.list().data]
    except Exception:
        return []

class AnnotationManager:
    @staticmethod
    def generate_annotation(image_path: str, prompt: str, model: str) -> str:
        """Generate an annotation for ``image_path`` using OpenAI.

        Parameters
        ----------
        image_path : str
            Path to the image file.
        prompt : str
            Instructional prompt sent to the model.
        model : str
            OpenAI model identifier.

        Returns
        -------
        str
            The annotation text returned by the model.
        """

        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        except OSError as exc:
            raise FileNotFoundError(f"Could not read image: {image_path}") from exc

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that describes images."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"},
                            },
                        ],
                    },
                ],
                max_tokens=500,
            )
        except Exception as exc:  # pragma: no cover - network call
            raise RuntimeError("Failed to generate annotation") from exc

        return response.choices[0].message.content.strip()
