# server.py
"""
This is a simple server that exposes the tools to the MCP framework.
Main objective is to generate HTML project cards for a data science portfolio website, upon GitHub README content updates.
The server is designed to be lightweight and easy to run, with minimal dependencies.
It can be run locally for testing, or deployed to a cloud service like Render or Fly.io
Emphasis is on simplicity, clarity and token efficiency, not production-level robustness.
The server exposes two tools:
1. get_repo_readme(github_username, repo_name) → str
   Fetches the README from a public GitHub repository.
2. generate_card(readme_text) → str
   Given a README text, asks Claude to generate a styled HTML project card.
"""

from mcp.server.fastmcp import FastMCP
import httpx
import anthropic
import os
from dotenv import load_dotenv
import config                    # ← import your config

load_dotenv()

mcp = FastMCP("Portfolio Agent")
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Tool 1: Check if repo has cv-page tag

def repo_has_cv_tag(repo_name: str) -> bool:
    """
    Check if a GitHub repo has the 'cv-page' topic tag.
    Returns True if tagged, False otherwise.
    """
    url = f"https://api.github.com/repos/{config.GITHUB_USERNAME}/{repo_name}/topics"
    headers = {"Accept": "application/vnd.github.mercy-preview+json"}  # required for topics API
    
    response = httpx.get(url, headers=headers)
    
    if response.status_code != 200:
        return False
    
    topics = response.json().get("names", [])
    return "cv-page" in topics

# Tool 2: Read README from GitHub
@mcp.tool()
def get_repo_readme(repo_name: str) -> str:
    """
    Fetch the README from a public GitHub repository.
    Uses the configured GitHub username automatically.
    """
    url = f"https://api.github.com/repos/{config.GITHUB_USERNAME}/{repo_name}/readme"
    headers = {"Accept": "application/vnd.github.raw+json"}
    response = httpx.get(url, headers=headers)

    if response.status_code == 200:
        return response.text
    else:
        return f"Could not fetch README. Status code: {response.status_code}"


# Tool 3: Generate HTML project card using Claude 
@mcp.tool()

def generate_card(readme_text: str, repo_name: str) -> str:
    """
    Given a README text and repo name, generate a styled HTML project card.
    """
    readme_trimmed = readme_text[:config.MAX_README_CHARS]
    
    # Build the real GitHub URL
    github_url = f"https://github.com/{config.GITHUB_USERNAME}/{repo_name}"

    prompt = f"""
You are helping update a data science portfolio website.
Based on the README below, generate a single HTML project card.

The card must follow this EXACT structure:

<div class="project-card">
  <p class="project-type type-ml">Machine Learning</p>
  <p class="project-title">Project Title Here</p>
  <p class="project-desc">
    2-3 sentence description of the project.
  </p>
  <div class="project-footer">
    <div class="tech-pills">
      <span class="tech-pill">Python</span>
      <span class="tech-pill">pandas</span>
    </div>
    <a href="{github_url}" target="_blank" class="card-link">GitHub →</a>
  </div>
</div>

Rules:
- project-type must be one of: type-ml, type-app, type-powerbi, type-eda
- Only include libraries actually mentioned in the README
- Emphasize what makes the project technically interesting
- Highlight any agentic, automation, or ML aspects prominently
- Keep description concise and professional
- Return ONLY the HTML block, no explanation, no markdown backticks

README:
{readme_trimmed}

"""
    response = claude.messages.create(
        model=config.MODEL_NAME,       # ← from config
        max_tokens=config.MAX_TOKENS,  # ← from config
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text

# ── Tool 4: Inject card into portfolio HTML ──────────────────────
@mcp.tool()
def update_portfolio(new_card_html: str, repo_name: str) -> str:
    """
    Fetches index.html, checks if project already exists,
    then injects new card if it's a new project.
    """
    url = f"https://api.github.com/repos/{config.GITHUB_USERNAME}/{config.PORTFOLIO_REPO}/contents/index.html"
    headers = {"Accept": "application/vnd.github.raw+json"}
    response = httpx.get(url, headers=headers)

    if response.status_code != 200:
        return f"Could not fetch index.html. Status code: {response.status_code}"

    current_html = response.text

    # ── Guard: check if this project already has a card ──────────
    # Look for the repo URL already existing in the HTML
    github_url = f"https://github.com/{config.GITHUB_USERNAME}/{repo_name}"
    if github_url in current_html:
        return f"⚠️ Card for '{repo_name}' already exists — skipping injection."

    # ── Check markers exist ───────────────────────────────────────
    if config.MARKER_START not in current_html:
        return f"Marker '{config.MARKER_START}' not found in index.html"
    if config.MARKER_END not in current_html:
        return f"Marker '{config.MARKER_END}' not found in index.html"

    # ── Inject new card after PROJECTS-START ──────────────────────
    updated_html = current_html.replace(
        config.MARKER_START,
        f"{config.MARKER_START}\n{new_card_html}"
    )

    return updated_html

# ── Tool 5: Push updated HTML to GitHub ─────────────────────────
@mcp.tool()
def push_to_github(updated_html: str) -> str:
    """
    Commits and pushes the updated index.html back to the portfolio repo.
    Requires GITHUB_TOKEN in .env with repo write permissions.
    """
    import base64

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return "Error: GITHUB_TOKEN not found in .env"

    # GitHub API endpoint for updating a file
    url = f"https://api.github.com/repos/{config.GITHUB_USERNAME}/{config.PORTFOLIO_REPO}/contents/index.html"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    # Step 1 — get the current file's SHA
    # GitHub requires the SHA to update an existing file
    # think of it as a version fingerprint — like a gel band confirming
    # you have the right fragment before cutting it
    response = httpx.get(url, headers=headers)
    if response.status_code != 200:
        return f"Could not fetch file metadata. Status: {response.status_code}"

    sha = response.json()["sha"]

    # Step 2 — encode updated HTML to base64
    # GitHub API requires file content in base64 format
    encoded_content = base64.b64encode(updated_html.encode()).decode()

    # Step 3 — push the update
    payload = {
        "message": "agent: add new project card",   # commit message
        "content": encoded_content,                  # new file content
        "sha": sha                                   # current version fingerprint
    }

    push_response = httpx.put(url, headers=headers, json=payload)

    if push_response.status_code == 200:
        return "✅ Portfolio updated successfully!"
    else:
        return f"❌ Push failed. Status: {push_response.status_code}\n{push_response.text}"
    

# ── Test 
if __name__ == "__main__":
    repo_name = "wattwise-app"  # ← define first

    if not repo_has_cv_tag(repo_name):
        print(f"⚠️ Repo '{repo_name}' is not tagged 'cv-page' — skipping.")
    else:
        # Only runs if tag exists
        print("Fetching README...")
        readme = get_repo_readme(repo_name)

        print("Generating card...")
        card = generate_card(readme, repo_name)

        print("\nUpdating portfolio HTML...")
        updated_html = update_portfolio(card, repo_name)

        if updated_html.startswith("⚠️"):
            print(updated_html)
        else:
            print("\nPushing to GitHub...")
            result = push_to_github(updated_html)
            print(result)