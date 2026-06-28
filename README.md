# Portfolio Agent — Agentic Portfolio Auto-Updater

An MCP-based agent that automatically updates a GitHub Pages portfolio website whenever a new project repository is pushed to GitHub.

## What it does

When triggered, the agent:
1. Fetches the README from a target GitHub repository
2. Uses Claude (via the Anthropic API) to generate a styled HTML project card
3. Injects the card into `index.html` between comment markers
4. Pushes the updated file back to GitHub via the Contents API

No manual HTML editing required — the portfolio updates itself.

## Tech stack

- Python
- FastMCP (Model Context Protocol server)
- Anthropic Claude API
- GitHub Contents API
- httpx
- python-dotenv

## How it works

The pipeline is built as a four-tool MCP server:

| Tool | What it does |
|---|---|
| `get_repo_readme` | Fetches README from a GitHub repo via the GitHub API |
| `generate_card` | Sends README to Claude, gets back a styled HTML card |
| `update_portfolio` | Injects the card into `index.html` between `<!-- PROJECTS-START -->` and `<!-- PROJECTS-END -->` markers |
| `push_to_github` | Commits and pushes the updated HTML file back to GitHub |

## Key design decisions

- **Duplicate guard**: before injecting, the agent checks if the project's GitHub URL already exists in `index.html`
- **Marker-based injection**: no templating framework needed — two HTML comments define the injection zone
- **Config/secret separation**: tunable settings in `config.py`, secrets in `.env` via python-dotenv

## Project structure

```
portfolio-agent/
├── server.py        # MCP server with all four tools
├── config.py        # Tunable settings (model, repo names, markers)
├── .env             # Secrets: ANTHROPIC_API_KEY, GITHUB_TOKEN
├── requirements.txt
└── README.md
```

## Setup

```bash
# Create virtual environment
python -m venv myenv
source myenv/bin/activate  # or myenv\Scripts\activate on Windows

# Install dependencies
pip install fastmcp httpx anthropic python-dotenv

# Add secrets to .env
ANTHROPIC_API_KEY=your_key_here
GITHUB_TOKEN=your_github_token_here
```

## Running the agent

```bash
python server.py
```

## Next steps

- GitHub Action to trigger the agent automatically on repo push
- Support for multiple portfolio repos
- Card style customization via config
