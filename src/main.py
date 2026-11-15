import asyncio
from src.app import TerminalNewspaperApp

def main() -> None:
    asyncio.run(TerminalNewspaperApp().run())

if __name__ == "__main__":
    main()