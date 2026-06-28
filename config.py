# config.py — all tuneable settings in one place

# GitHub settings
GITHUB_USERNAME = "youlia-denisov"
PORTFOLIO_REPO  = "youlia-denisov.github.io"   # where index.html lives


# Claude API settings
MODEL_NAME       = "claude-sonnet-4-6"
MAX_TOKENS       = 500        # max tokens in Claude's response
MAX_README_CHARS = 1000      # trim README before sending to Claude

# HTML injection markers
MARKER_START = "<!-- PROJECTS-START -->"
MARKER_END   = "<!-- PROJECTS-END -->"

# Additional constraints

EXCLUDED_REPOS = ["cv-page-agent"]