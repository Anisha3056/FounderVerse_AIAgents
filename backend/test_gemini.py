import asyncio

from app.llm.provider import LLMProvider


async def main():
    provider = LLMProvider()

    response = await provider.generate(
        system_prompt="You are a helpful assistant.",
        user_prompt="Reply with exactly: GEMINI WORKS",
    )

    print(response)


if __name__ == "__main__":
    asyncio.run(main())