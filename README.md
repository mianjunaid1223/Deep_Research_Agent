# Deep Research Agent: Autonomous AI Web Research & Synthesis

An autonomous agentic research system designed to perform end-to-end investigative research on user-defined topics. By combining LangChain Google Generative AI, LiteLLM unified completion wrappers, and resilient web scraping routines, the agent discovers source URLs, extracts textual content, parses knowledge graphs, and compiles detailed investigative reports.

---

## Architectural Pipeline

```
+-----------------------+      +---------------------------+      +--------------------------+
|  User Research Query  | ---> | Link Discovery Engine     | ---> | Concurrent Web Scraper   |
|   (Web Interface / API|      | (Gemini 1.5 via LangChain)|      | (BS4, Requests, Backoff) |
+-----------------------+      +---------------------------+      +--------------------------+
                                                                                |
                                                                                v
+-----------------------+      +---------------------------+      +--------------------------+
| Final Research Report | <--- | Synthesis & Summary Engine| <--- | Text Cleaning & Parsing  |
| (Markdown / PDF / UI) |      | (LiteLLM Model Router)    |      | (Regex, Normalization)   |
+-----------------------+      +---------------------------+      +--------------------------+
```

---

## Core Capabilities

1. Intelligent Source Discovery:
   Transforms raw user topics into targeted URL exploration lists using Google Gemini (`ChatGoogleGenerativeAI`), formulating focused queries to discover authoritative sources.

2. Resilient Web Extraction (`web_scrape_for_llm`):
   Custom web scraper utilizing BeautifulSoup4 with exponential backoff, configurable timeouts, User-Agent rotation, and structural text cleanups to strip boilerplate, ads, and navigational noise.

3. Multi-Model Synthesis (LiteLLM):
   Aggregates scraped body text and routes contextual prompts across supported model providers to draft cohesive, citation-backed research briefings.

4. Modern Packaging & Dependency Management:
   Managed entirely via the `uv` package manager with deterministic lockfiles (`uv.lock`) and standard `pyproject.toml` declarations.

---

## Technical Stack

- Agent Orchestration: LangChain Google GenAI (`langchain_google_genai`)
- LLM Gateway: LiteLLM
- Web Scraping: BeautifulSoup4, Requests, Regex Link Normalizers
- Web Framework: Flask / FastAPI backend in `main.py`
- Environment & Configuration: `python-dotenv`
- Package Management: `uv` (Astral)

---

## Environment Configuration

Create a `.env` file inside the `researcher/` directory:

```env
API_KEY=your_google_gemini_api_key
MODEL_LC=gemini-1.5-flash
OPENAI_API_KEY=your_optional_openai_key_if_using_multi_model
```

---

## Installation & Execution

### Prerequisites
- Python 3.10+
- `uv` package manager installed (`pip install uv` or official standalone installer)

### Quick Start with uv

1. Clone repository:
   ```bash
   git clone https://github.com/mianjunaid1223/Deep_Research_Agent.git
   cd Deep_Research_Agent/researcher
   ```

2. Synchronize environment:
   ```bash
   uv sync
   ```

3. Launch application:
   ```bash
   uv run python src/researcher/main.py
   ```

4. Open `http://127.0.0.1:5000` in your browser to interact with the research dashboard.

---

## Project Structure

```
Deep_Research_Agent/
|-- Deep_Research_Agent_Documentation.pdf   # Architectural whitepaper and documentation
|-- researcher/
    |-- pyproject.toml                     # Project metadata and dependencies
    |-- uv.lock                            # Deterministic dependency resolution
    |-- .env                               # Local secrets (create from template)
    |-- src/
        |-- researcher/
            |-- main.py                    # Application entry point and HTTP endpoints
            |-- logic.py                   # Agent loop, search extraction, scraping, and LLM calls
            |-- templates/                 # Jinja2 web interface templates
```
