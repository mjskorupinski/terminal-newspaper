# Terminal Newspaper (`tn`)

Aggregating news from all around the world in your terminal. For those tired of flashing colorful websites with tons of ads. An interactive, fast, and clean newspaper application that fetches and filters RSS news feeds using LangChain, ChromaDB, and OpenAI embeddings.

---

## Features

* **Semantic Topic Search:** Uses OpenAI embeddings (`text-embedding-3-small`) and ChromaDB (`cosine` distance) with self-calibrating relative-distance filtering to surface relevant articles across multilingual feeds (e.g., Polish and English) without noisy false positives.
* **Source-Segregated Views:** Browse matched articles grouped cleanly by publisher under every topic, or inspect all indexed articles from a specific news source.
* **Distraction-Free Terminal Reader:** Extracts clean Markdown via `trafilatura` (with automatic publisher boilerplate stripping) and renders articles in centered, newspaper-width panels complete with source metadata, clickable links, and reading-time estimates.
* **Random Article Discovery:** Jump straight into a random unread article from today's edition.
* **Daily Persistence:** Automatically caches today's articles (`db/articles_cache.json`) for instant startup and resets the vector database cleanly on midnight rollover.
* **Interactive Configuration:** Add or remove RSS feeds and search topics directly from the terminal menu.

---

## Prerequisites

* **Python 3.11+**
* **[`uv`](https://docs.astral.sh/uv/)** package manager installed:
  * **Linux / macOS:**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
  * **Windows (PowerShell):**
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
* **Azure OpenAI Credentials** (API key, endpoint URL, and API version) with access to the `text-embedding-3-small` deployment.

---

## Installation

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd terminal-newspaper
```

### 2. Configure Environment Variables

Create a `.env` file in the project root directory with your Azure OpenAI credentials:

```env
API_KEY=your_azure_openai_api_key
API_URL=https://your-resource-name.openai.azure.com/
API_VERSION=2024-02-01
```

### 3. Configure Initial Sources & Topics (Optional)

You can customize `settings/sources.json` and `settings/topics.json` before starting, or manage them interactively inside the app:

**`settings/sources.json`:**
```json
{
  "sources": [
    { "name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml" },
    { "name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml" }
  ]
}
```

**`settings/topics.json`:**
```json
{
  "topics": [
    "AI",
    "Middle East",
    "USA",
    "Ukraine"
  ]
}
```

### 4. Install Globally with `uv`

From the project root directory, install the CLI in **editable mode** so `settings/`, `db/`, and `.env` remain anchored to your project folder regardless of where you run the command:

```bash
uv tool install --editable .
```

If `uv` notifies you that its tool binary directory (`~/.local/bin` on Linux/macOS or `%USERPROFILE%\.local\bin` on Windows) is not on your `PATH`, run:

```bash
uv tool update-shell
```

Restart your terminal window for the updated `PATH` to take effect.

---

## Usage

Launch the application from any directory using either command:

```bash
tn
# or
terminal-newspaper
```

### Navigation

* **Topics (`#`):** Select any configured topic to view semantically matched articles grouped by news source.
* **Sources (`·`):** Select a publisher to browse all articles fetched from that feed today.
* **Random article:** Open a random article from today's edition with an option to keep shuffling.
* **Actions:**
  * `Fetch & index news` — Manually pull the latest articles from all RSS feeds.
  * `Manage sources` — Add new named RSS feeds or remove existing ones.
  * `Manage topics` — Add or remove semantic search topics.
