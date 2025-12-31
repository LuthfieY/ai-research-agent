# Lumina Research Agent

**Lumina Research** is an intelligent, autonomous research assistant powered by **LangGraph**, **Google Gemini**, and **Streamlit**. It automates the process of gathering information, writing comprehensive reports, and citing sources from both general web results and academic journals.


##  Features

- **Autonomous Agent**: Orchestrates a Researcher, Writer, and Critic to produce high-quality drafts.
- **Dual Search Modes**:
  - **General**: Broad web search using **Tavily API**.
  - **Academic**: Scholarly articles and papers using **SerpAPI (Google Scholar)**.
- **Smart Citations**: Automatically formats references in **IEEE**, **APA**, or **BibTeX** styles.
- **Research History**: Automatically saves your reports and references to a local database (`SQLite`), allowing you to revisit past research.

##  Tech Stack

- **Frontend**: Streamlit
- **Orchestration**: LangGraph, LangChain
- **LLM**: Google Gemini 2.5 Flash
- **Search Tools**: Tavily Search API, SerpAPI
- **Database**: SQLite
- **Environment**: Docker & Docker Compose

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) installed.
- API Keys for:
  - **Google Gemini** (LLM)
  - **Tavily** (General Search)
  - **SerpAPI** (Optional - for Academic Search)

### Quick Start (Docker)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/LuthfieY/ai-research-agent.git
   cd ai-research-agent
   ```
2. **Run with Docker Compose**:
   ```bash
   docker compose up --build
   ```

3. **Access the App**:
   Open your browser and navigate to:
   [http://localhost:8501](http://localhost:8501)

##  Usage Guide

1. **Configuration**: Use the **Configuration** expander in the top-left sidebar to enter your API keys if not set in `.env`.
2. **Select Mode**: Choose between **General** or **Academic Journals**.
3. **Start Research**: Enter a topic (e.g., *"Impact of AI on Healthcare"*) and click **Start Research**.
4. **View Results**: 
   - Watch the agent plan, search, writing, and critiquing in real-time.
   - Read the final justified report.
   - Check the **References** section at the bottom for source links and citation generation.
5. **History**: Click **"History"** in the sidebar to view past reports.

##  Project Structure

```
research-agent/
├── app/
│   ├── graph.py        # LangGraph agent logic (nodes & edges)
│   ├── main.py         # Streamlit UI entry point
│   ├── database.py     # SQLite history management
│   └── agent_types.py  # TypedDict definitions
├── .streamlit/         # UI Theme configuration
├── docker-compose.yml  # Docker orchestration
├── Dockerfile          # Container definition
└── requirements.txt    # Python dependencies
```

## License

This project is licensed under the MIT License.
