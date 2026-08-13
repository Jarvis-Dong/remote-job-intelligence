"""Run the Actor locally or inside Apify."""

from .main import main

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
