import os
from openai import AsyncOpenAI


async def retrieve_openai_client() -> AsyncOpenAI:
    openai_api_key = os.getenv("OPENAI_API_KEY")

    openai_client = AsyncOpenAI(api_key=openai_api_key)
    return openai_client


__all__ = ["retrieve_openai_client"]
