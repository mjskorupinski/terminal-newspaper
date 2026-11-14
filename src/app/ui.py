from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

import questionary
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

if TYPE_CHECKING:
    from src.core.article import Article

DIVIDER = "  ────────────────────────────────────────────────────────────"
BACK_SENTINEL = "__BACK__"
ADD_SENTINEL = "__ADD__"


class TerminalUI:
    def __init__(self) -> None:
        self._console = Console()

    def clear(self) -> None:
        self._console.clear()

    def render_splash(self) -> None:
        """Clears the screen and displays the startup title before loading."""
        self._console.clear()
        self._console.print("\n  [bold cyan]TERMINAL NEWSPAPER[/bold cyan]")
        self._console.print(f"[dim]{DIVIDER}[/dim]\n")

    def print_goodbye(self) -> None:
        self._console.clear()
        self._console.print("\n  [dim]Goodbye![/dim]\n")

    def render_main_header(
        self,
        source_count: int,
        article_count: int,
        status_msg: str | None = None,
    ) -> None:
        self._console.clear()
        source_label = "source" if source_count == 1 else "sources"
        article_label = "article" if article_count == 1 else "articles"

        self._console.print(
            f"\n  [bold cyan]TERMINAL NEWSPAPER[/bold cyan]  "
            f"[dim]·  {source_count} {source_label}  ·  {article_count} {article_label}[/dim]"
        )
        self._console.print(f"[dim]{DIVIDER}[/dim]\n")

        if status_msg:
            self._console.print(f"  {status_msg}\n")

    def render_sub_header(
        self,
        title: str,
        subtitle: str | None = None,
        status: str | None = None,
    ) -> None:
        self._console.clear()
        suffix = f"  [dim]·  {subtitle}[/dim]" if subtitle else ""
        self._console.print(f"\n  [bold cyan]{title}[/bold cyan]{suffix}")
        self._console.print(f"[dim]{DIVIDER}[/dim]\n")

        if status:
            self._console.print(f"  {status}\n")

    def render_article(self, article: "Article | str") -> None:
        self._console.clear()

        if isinstance(article, str):
            md_content = article
        else:
            date_str = (
                article.publish_date.strftime("%Y-%m-%d %H:%M")
                if article.publish_date
                else "Unknown date"
            )
            md_content = (
                f"# {article.title}\n"
                f"*Published: {date_str}*  \n"
                f"*Source: {article.url}*\n\n"
                f"---\n\n"
                f"{article.content}\n"
            )

        self._console.print()
        self._console.print(
            Panel(Markdown(md_content), border_style="cyan", padding=(1, 2))
        )
        self._console.print()

    @contextmanager
    def spinner(self, message: str, style: str = "cyan") -> Iterator[None]:
        with Progress(
            SpinnerColumn(),
            TextColumn(f"[{style}]  {message}"),
            transient=True,
            console=self._console,
        ) as progress:
            progress.add_task(description=message, total=None)
            yield

    @staticmethod
    def format_article_label(article: "Article | str") -> str:
        if not isinstance(article, str):
            return article.title

        lines = [line.strip() for line in article.strip().splitlines() if line.strip()]
        first_line = lines[0].lstrip("# ").strip() if lines else "Untitled article"
        return f"{first_line[:80]}..." if len(first_line) > 80 else first_line

    @staticmethod
    async def select(
        choices: list[questionary.Choice | questionary.Separator],
    ) -> Any:
        return await questionary.select(
            "",
            qmark="",
            instruction="",
            pointer="❯",
            choices=choices,
        ).ask_async()

    @staticmethod
    async def text(prompt: str, qmark: str = "+") -> str | None:
        return await questionary.text(f"  {prompt}", qmark=qmark).ask_async()

    @staticmethod
    async def pause(prompt: str = "Press any key to return...") -> None:
        await questionary.press_any_key_to_continue(f"  {prompt}").ask_async()