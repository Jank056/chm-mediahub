"""reCAPTCHA v3 verification service."""

import httpx

from config import get_settings

VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


async def verify_recaptcha(token: str) -> bool:
    """Verify a reCAPTCHA v3 token. Returns True if valid."""
    settings = get_settings()

    if not settings.recaptcha_enabled or not settings.recaptcha_secret_key:
        return True  # Skip verification if not configured

    async with httpx.AsyncClient() as client:
        response = await client.post(
            VERIFY_URL,
            data={
                "secret": settings.recaptcha_secret_key,
                "response": token,
            },
        )

    result = response.json()
    return (
        result.get("success", False)
        and result.get("score", 0) >= settings.recaptcha_min_score
    )
