import asyncio

from google import genai
from google.genai import types
from google.genai.errors import ServerError

from app.config.settings import get_settings


class LLMProvider:
    FALLBACK_MODELS = [
        "gemini-3.7-flash",
        "gemini-3.5-flash-lite",
    ]

    def __init__(self) -> None:
        self.settings = get_settings()

        if not self.settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(
            api_key=self.settings.gemini_api_key
        )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1200,
        response_schema=None,
    ) -> str:

        models_to_try = [
            self.settings.gemini_model,
            *self.FALLBACK_MODELS,
        ]

        for index, model in enumerate(models_to_try):
            try:
                print(f"Trying Gemini model: {model}")

                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                    temperature=0.3,
                    response_mime_type=(
                        "application/json"
                        if response_schema is not None
                        else None
                    ),
                    response_schema=response_schema,
                )

                response = (
                    await self.client.aio.models.generate_content(
                        model=model,
                        contents=user_prompt,
                        config=config,
                    )
                )

                # Diagnose incomplete or truncated responses.
                candidates = response.candidates or []
                finish_reason = (
                    candidates[0].finish_reason
                    if candidates
                    else "NO_CANDIDATE"
                )

                print(f"Gemini finish reason: {finish_reason}")
                print(
                    "Gemini output tokens: "
                    f"{getattr(response.usage_metadata, 'candidates_token_count', None)}"
                )

                # Do not accept a truncated response as a successful generation.
                if str(finish_reason).upper().endswith("MAX_TOKENS"):
                    raise RuntimeError(
                        f"Gemini response from {model} was truncated "
                        f"because it reached the output-token limit ({max_tokens})."
                    )

                if not response.text:
                    raise RuntimeError(
                        f"Gemini returned an empty response from {model}."
                    )

                print(f"Gemini response received from: {model}")
                return response.text.strip()

            except ServerError as exc:
                print(f"Gemini server error with {model}: {exc}")
                continue
            except Exception as exc:
                print(f"Gemini request failed with {model}: {exc}")
                continue

        raise RuntimeError(
            "All configured Gemini models failed to generate a response."
        )


                