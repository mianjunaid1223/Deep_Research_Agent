# Deep Research Agent

[![Year Built](https://img.shields.io/badge/Year%20Built-2025-blue.svg)](#)


Agentic research orchestration engine combining LangChain Google GenAI query expansion, BeautifulSoup web scraping with exponential backoff, and LiteLLM multi-model synthesis to deliver structured technical reports.

```
+-----------------------------------------------------------------------------------------+
|                                    Client Interface                                     |
|                                                                                         |
|   +---------------------------------------------------------------------------------+   |
|   | Modern Single-Page Application (Monochromatic Zinc Palette, Tailwind CSS)       |   |
|   | User Input: Natural Language Query -> POST /api/chat                            |   |
|   +---------------------------------------------------------------------------------+   |
+--------------------------------------------|--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                                Flask Research Orchestrator                              |
|                                                                                         |
|   +---------------------------------------------------------------------------------+   |
|   | Phase 1: Query Expansion & URL Discovery                                        |   |
|   | LangChain ChatGoogleGenerativeAI (Gemini)                                       |   |
|   | Generates targeted search trajectories and authoritative source links           |   |
|   +----------------------------------------|----------------------------------------+   |
|                                            |                                            |
|                                            v                                            |
|   +---------------------------------------------------------------------------------+   |
|   | Phase 2: Autonomous Web Extraction Subsystem                                    |   |
|   | Regex link parser: re.findall(r'https?://[^\s\)]+', text)                       |   |
|   | Requests HTTP client with timeouts, retry backoff, and user-agent simulation    |   |
|   | BeautifulSoup4 text extraction, element stripping, and token budgeting         |   |
|   +----------------------------------------|----------------------------------------+   |
|                                            |                                            |
|                                            v                                            |
|   +---------------------------------------------------------------------------------+   |
|   | Phase 3: Multi-Model Synthesis & HTML Rendering                                 |   |
|   | LiteLLM completion API unifying disparate frontier models                      |   |
|   | Markdown stripping, semantic HTML structure (<section>), Tailwind styling      |   |
|   | Response caching to local filesystem (response.txt) and JSON API response       |   |
|   +---------------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------------+
```

## System Architecture

Deep Research Agent executes a two-tier retrieval and synthesis workflow. The system combines prompt orchestration frameworks (LangChain) with universal model gateways (LiteLLM) to perform automated information discovery across web resources.

### Architectural Subsystems

1. Query Expansion Pipeline: Takes high-level research questions, analyzes underlying informational requirements, and prompts Google Gemini via LangChain ChatGoogleGenerativeAI to propose specific, authoritative target URLs for exploration.

2. Web Extraction Engine: The logic.py module handles raw HTTP content collection using the Requests library. It enforces configurable retry counts (default: 1), inter-attempt delay windows (default: 3 seconds), and request timeouts (default: 20 seconds). BeautifulSoup parses retrieved DOM trees to isolate meaningful article text while purging markup noise.

3. Cross-Model Synthesis Engine: Uses LiteLLM to decouple prompt execution from specific LLM providers. The engine synthesizes gathered intelligence into an analytical report structured as semantic HTML5 with Tailwind CSS classes adhering to a monochromatic dark-mode zinc aesthetic.

4. Flask API Server: The main.py module serves the user interface and exposes REST endpoints for research dispatch, error interception, and file system artifact logging.

## Directory Structure Reference

```
Deep_Research_Agent/
|-- Deep_Research_Agent_Documentation.pdf   # Architectural report and design documentation
|-- researcher/
|   |-- pyproject.toml                      # Project metadata, dependencies, build config
|   |-- .env                                # Local secrets and model identifiers
|   |-- .python-version                     # Pinned Python version (3.13)
|   |-- README.md                           # Internal package notes
|   |-- src/
|   |   `-- researcher/
|   |       |-- __init__.py                 # Module namespace initialization
|   |       |-- logic.py                    # URL extraction, web scraper, retry mechanics
|   |       `-- main.py                     # Flask web server, API routes, LiteLLM engine
`-- README.md                               # Root project documentation
```

## Extraction Pipeline Mechanics

The web extraction algorithm in logic.py implements defensive error handling across remote endpoints:

```python
def web_scrape_for_llm(url: str, retries=1, delay=3, timeout=20) -> str:
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text(separator=" ", strip=True)
            return page_text[:5000]

        except requests.exceptions.RequestException as e:
            if attempt + 1 < retries:
                time.sleep(delay)
            else:
                return f"Error fetching the URL: {str(e)}"
        except requests.exceptions.Timeout:
            return "Timeout occurred for URL. No data found."

    return "Failed to fetch the URL after multiple attempts."
```

## API Endpoint Reference

### Research Query Endpoint

```http
POST /api/chat
Content-Type: application/json

{
    "query": "Quantum computing commercial roadmap 2026-2030"
}
```

#### Response Format (200 OK)

```json
{
    "response": "<section class=\"bg-zinc-900 border border-zinc-800 rounded-lg p-6 text-zinc-100\">\n<h2 class=\"text-xl font-bold text-zinc-200 mb-4\">Executive Overview</h2>\n<p class=\"text-zinc-400 mb-4\">...</p>\n</section>"
}
```

#### Error Responses

- 400 Bad Request: Dispatched when query is empty or contains whitespace only.
- 500 Internal Server Error: Dispatched on LLM rate-limit exhaustion or unhandled network exceptions with error diagnostics.

## Environment Configuration

Configure credentials in researcher/.env:

| Key | Description | Example |
|---|---|---|
| API_KEY | Google Gemini API key from Google AI Studio | AIzaSy... |
| MODEL_LC | LangChain model identifier | gemini-1.5-flash |
| MODEL | LiteLLM target model string | gemini/gemini-1.5-flash |
| GEMINI_API_KEY | Mirrored key for native LiteLLM driver | AIzaSy... |

## Local Installation and Execution

### Using uv Package Manager (Recommended)

```bash
# Navigate to the researcher project root
cd researcher

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
uv pip install -e .

# Launch research server
python src/researcher/main.py
```

### Using Standard pip

```bash
cd researcher
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install flask beautifulsoup4 litellm langchain-google-genai python-dotenv requests
python src/researcher/main.py
```

Access the agent interface at http://127.0.0.1:5000.
