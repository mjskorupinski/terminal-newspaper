import random
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import questionary

from src.app.config import AppConfig
from src.app.engine import NewspaperEngine
from src.app.ui import ADD_SENTINEL, BACK_SENTINEL, DIVIDER, TerminalUI

if TYPE_CHECKING:
    from src.core.article import Article


class TerminalNewspaperApp:
    def __init__(
        self,
        config: AppConfig | None = None,
        engine: NewspaperEngine | None = None,
        ui: TerminalUI | None = None,
    ) -> None:
        self._config = config or AppConfig()
        self._engine = engine or NewspaperEngine()
        self._ui = ui or TerminalUI()
        self._status_msg: str | None = None

    async def run(self) -> None:
        await self._startup()

        while True:
            self._ui.render_main_header(
                source_count=len(self._config.sources),
                article_count=self._engine.article_count,
                status_msg=self._status_msg,
            )
            self._status_msg = None

            action = await self._ui.select(self._build_main_menu())
            if action is None or action == "quit":
                self._ui.print_goodbye()
                break

            await self._dispatch(action)

    async def _startup(self) -> None:
        """Displays a startup loading screen, loads DB, and auto-fetches if empty."""
        self._ui.render_splash()

        with self._ui.spinner("Initializing search engine & database..."):
            await self._engine.initialize(self._config.sources)

        if self._engine.article_count == 0:
            if not self._config.sources:
                self._status_msg = "[yellow]![/yellow] No sources configured. Add an RSS source to begin."
                return

            with self._ui.spinner("No articles indexed for today. Fetching latest news...", style="bold blue"):
                await self._engine.prepare_news(self._config.sources)

            self._status_msg = (
                f"[bold green]✓[/bold green] Fetched and indexed {self._engine.article_count} articles for today."
            )

    async def _dispatch(self, action: Any) -> None:
        if action == "random":
            await self._open_random_article()
        elif action == "prepare":
            await self._prepare_news()
        elif action == "manage_sources":
            await self._manage_sources()
        elif action == "manage_topics":
            await self._manage_topics()
        elif isinstance(action, tuple):
            kind, value = action
            if kind == "topic":
                await self._browse_topic(value)
            elif kind == "source":
                await self._browse_source(value)

    async def _prepare_news(self) -> None:
        if not self._config.sources:
            self._status_msg = "[yellow]![/yellow] No sources configured. Add an RSS source first."
            return

        if not self._engine.is_initialized:
            with self._ui.spinner("Initializing search engine & database..."):
                await self._engine.initialize(self._config.sources)

        with self._ui.spinner("Fetching and indexing news articles...", style="bold blue"):
            await self._engine.prepare_news(self._config.sources)

        self._status_msg = "[bold green]✓[/bold green] News fetched and indexed successfully."


    async def _open_random_article(self) -> None:
        if not self._engine.is_initialized:
            with self._ui.spinner("Initializing search engine & database..."):
                await self._engine.initialize(self._config.sources)

        articles = await self._engine.get_all_articles(self._config.sources)
        if not articles:
            self._status_msg = "[yellow]![/yellow] No articles indexed today. Try fetching news first."
            return

        seen_urls: set[str] = set()

        while True:
            remaining = [a for a in articles if a.url not in seen_urls]
            if not remaining:
                seen_urls.clear()
                remaining = articles

            chosen = random.choice(remaining)
            seen_urls.add(chosen.url)

            self._ui.render_article(chosen)

            next_step = await self._ui.select([
                questionary.Choice(title="  🎲  Another random article", value="another"),
                questionary.Choice(title="  ←   Back to main menu", value=BACK_SENTINEL),
            ])
            if next_step != "another":
                return

    async def _browse_source(self, source_name: str) -> None:
        if not self._engine.is_initialized:
            with self._ui.spinner("Initializing search engine & database..."):
                await self._engine.initialize(self._config.sources)

        articles = await self._engine.get_articles_by_source(self._config.sources, source_name)
        if not articles:
            self._status_msg = (
                f"[yellow]![/yellow] No articles found for '[bold]{source_name}[/bold]'. Try fetching news first."
            )
            return

        choices: list[questionary.Choice | questionary.Separator] = [
            questionary.Choice(
                title=f"  {idx}.  {self._ui.format_article_label(art)}",
                value=art,
            )
            for idx, art in enumerate(articles, start=1)
        ]
        choices.extend([
            questionary.Separator(DIVIDER),
            questionary.Choice(title="  ←  Back to main menu", value=BACK_SENTINEL),
        ])

        while True:
            self._ui.render_sub_header(source_name.upper(), f"{len(articles)} articles")
            selected = await self._ui.select(choices)
            if selected is None or selected == BACK_SENTINEL:
                return

            self._ui.render_article(selected)
            await self._ui.pause("Press any key to return to articles...")

    async def _browse_topic(self, topic: str) -> None:
        if not self._engine.is_initialized:
            with self._ui.spinner("Initializing search engine & database..."):
                await self._engine.initialize(self._config.sources)

        with self._ui.spinner(f"Searching articles for '{topic}'..."):
            articles = await self._engine.search(self._config.sources, topic, limit=25)

        if not articles:
            self._status_msg = (
                f"[yellow]![/yellow] No articles found for '[bold]{topic}[/bold]'. Try fetching news first."
            )
            return

        choices = self._build_grouped_article_choices(articles)

        while True:
            self._ui.render_sub_header("TOPIC", f"# {topic}  ·  {len(articles)} matched")
            selected = await self._ui.select(choices)
            if selected is None or selected == BACK_SENTINEL:
                return

            self._ui.render_article(selected)
            await self._ui.pause("Press any key to return to articles...")

    def _build_grouped_article_choices(
        self,
        articles: list["Article | str"],
    ) -> list[questionary.Choice | questionary.Separator]:
        grouped: dict[str, list["Article | str"]] = defaultdict(list)

        for art in articles:
            source_name = art.source if not isinstance(art, str) else "Other"
            grouped[source_name].append(art)

        configured_order = [s.name for s in self._config.sources]
        ordered_sources = [name for name in configured_order if name in grouped]
        ordered_sources.extend(name for name in grouped if name not in ordered_sources)

        choices: list[questionary.Choice | questionary.Separator] = []
        for idx, source_name in enumerate(ordered_sources):
            source_articles = grouped[source_name]
            if idx > 0:
                choices.append(questionary.Separator(" "))
            choices.append(questionary.Separator(f"  ── {source_name} ({len(source_articles)}) ──"))

            for art in source_articles:
                choices.append(
                    questionary.Choice(
                        title=f"     •  {self._ui.format_article_label(art)}",
                        value=art,
                    )
                )

        choices.extend([
            questionary.Separator(DIVIDER),
            questionary.Choice(title="  ←  Back to main menu", value=BACK_SENTINEL),
        ])
        return choices

    async def _manage_sources(self) -> None:
        changed = False
        sub_status: str | None = None

        while True:
            self._ui.render_sub_header("MANAGE SOURCES", f"{len(self._config.sources)} configured", sub_status)
            sub_status = None

            choices: list[questionary.Choice | questionary.Separator] = [
                questionary.Choice(title="  +  Add new source", value=ADD_SENTINEL),
                questionary.Separator(" "),
                questionary.Separator("  EXISTING SOURCES (select to remove)"),
            ]
            if self._config.sources:
                choices.extend(
                    questionary.Choice(
                        title=f"  −  {src.name}  ({src.url})",
                        value=("remove", src),
                    )
                    for src in self._config.sources
                )
            else:
                choices.append(questionary.Separator("     (no sources configured)"))

            choices.extend([
                questionary.Separator(DIVIDER),
                questionary.Choice(title="  ←  Back to main menu", value=BACK_SENTINEL),
            ])

            selection = await self._ui.select(choices)
            if selection is None or selection == BACK_SENTINEL:
                break

            if selection == ADD_SENTINEL:
                sub_status, added = await self._prompt_add_source()
                changed = changed or added
            elif isinstance(selection, tuple) and selection[0] == "remove":
                src = selection[1]
                if self._config.has_source_url(src.url):
                    self._config.remove_source(src.url)
                    changed = True
                    sub_status = f"[yellow]−[/yellow] Removed source: [bold]{src.name}[/bold]"

        if changed:
            self._engine.reset()
            with self._ui.spinner("Reloading sources..."):
                await self._engine.initialize(self._config.sources)
            self._status_msg = f"[green]✓[/green] Sources updated ({len(self._config.sources)} active)."

    async def _prompt_add_source(self) -> tuple[str | None, bool]:
        self._ui.render_sub_header("ADD RSS SOURCE")

        raw_name = await self._ui.text("Enter source name (or leave empty to cancel):")
        if not raw_name or not raw_name.strip():
            return None, False

        raw_url = await self._ui.text("Enter RSS feed URL (or leave empty to cancel):")
        if not raw_url or not raw_url.strip():
            return None, False

        clean_name = raw_name.strip()
        clean_url = raw_url.strip()

        if not clean_url.startswith(("http://", "https://")):
            return f"[red]✕[/red] Invalid URL (must start with http:// or https://): [bold]{clean_url}[/bold]", False

        if self._config.has_source_url(clean_url):
            return f"[yellow]![/yellow] Source already exists: [bold]{clean_url}[/bold]", False

        self._config.add_source(clean_name, clean_url)
        return f"[green]+[/green] Added source: [bold]{clean_name}[/bold] ({clean_url})", True

    async def _manage_topics(self) -> None:
        changed = False
        sub_status: str | None = None

        while True:
            self._ui.render_sub_header("MANAGE TOPICS", f"{len(self._config.topics)} configured", sub_status)
            sub_status = None

            choices: list[questionary.Choice | questionary.Separator] = [
                questionary.Choice(title="  +  Add new topic", value=ADD_SENTINEL),
                questionary.Separator(" "),
                questionary.Separator("  EXISTING TOPICS (select to remove)"),
            ]
            if self._config.topics:
                choices.extend(
                    questionary.Choice(title=f"  −  # {topic}", value=("remove", topic))
                    for topic in self._config.topics
                )
            else:
                choices.append(questionary.Separator("     (no topics configured)"))

            choices.extend([
                questionary.Separator(DIVIDER),
                questionary.Choice(title="  ←  Back to main menu", value=BACK_SENTINEL),
            ])

            selection = await self._ui.select(choices)
            if selection is None or selection == BACK_SENTINEL:
                break

            if selection == ADD_SENTINEL:
                sub_status, added = await self._prompt_add_topic()
                changed = changed or added
            elif isinstance(selection, tuple) and selection[0] == "remove":
                topic = selection[1]
                if topic in self._config.topics:
                    self._config.remove_topic(topic)
                    changed = True
                    sub_status = f"[yellow]−[/yellow] Removed topic: [bold]{topic}[/bold]"

        if changed:
            self._status_msg = f"[green]✓[/green] Topics updated ({len(self._config.topics)} active)."

    async def _prompt_add_topic(self) -> tuple[str | None, bool]:
        self._ui.render_sub_header("ADD TOPIC")
        raw_topic = await self._ui.text("Enter topic or phrase (or leave empty to cancel):")
        if not raw_topic or not raw_topic.strip():
            return None, False

        clean_topic = raw_topic.strip()
        if clean_topic in self._config.topics:
            return f"[yellow]![/yellow] Topic already exists: [bold]{clean_topic}[/bold]", False

        self._config.add_topic(clean_topic)
        return f"[green]+[/green] Added topic: [bold]{clean_topic}[/bold]", True


    def _build_main_menu(self) -> list[questionary.Choice | questionary.Separator]:
        choices: list[questionary.Choice | questionary.Separator] = [
            questionary.Separator("  TOPICS"),
        ]

        if self._config.topics:
            choices.extend(
                questionary.Choice(title=f"  #  {topic}", value=("topic", topic))
                for topic in self._config.topics
            )
        else:
            choices.append(questionary.Separator("     (no active topics)"))

        choices.extend([
            questionary.Separator(" "),
            questionary.Separator("  SOURCES"),
        ])

        if self._config.sources:
            choices.extend(
                questionary.Choice(title=f"  ·  {src.name}", value=("source", src.name))
                for src in self._config.sources
            )
        else:
            choices.append(questionary.Separator("     (no active sources)"))

        choices.extend([
            questionary.Separator(" "),
            questionary.Choice(title="  🎲 Random article", value="random"),
            questionary.Separator(" "),
            questionary.Separator("  ACTIONS"),
            questionary.Choice(title="  ↻  Fetch & index news", value="prepare"),
            questionary.Choice(title="  ⚙  Manage sources", value="manage_sources"),
            questionary.Choice(title="  ⚙  Manage topics", value="manage_topics"),
            questionary.Separator(DIVIDER),
            questionary.Choice(title="  ✕  Quit", value="quit"),
        ])
        return choices