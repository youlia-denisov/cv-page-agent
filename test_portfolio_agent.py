"""
test_portfolio_agent.py
=======================
Basic tests for the portfolio MCP pipeline.

Using unit tests for the core logic, and pytest for the overall pipeline.
This type of tests is independent of the MCP framework, and can be run without any API keys or network access.

Run with:
    pytest test_portfolio_agent.py -v

Install pytest if needed:
    pip install pytest
"""

import pytest

# ── What we're testing ───────────────────────────────────────────────────────
# We import only the pure-logic functions — NOT the MCP-decorated versions.
# Because @mcp.tool() wraps your function in MCP machinery.
# We want to test the logic, not the MCP layer.
#
# So in server.py, make sure the core logic can be imported.
# If you can't import cleanly, we use "mocking" (see below).


# ── 1. TESTING HTML INJECTION LOGIC ─────────────────────────────────────────
# This is the most important logic to test: injecting a card into index.html.
# We test it with a fake/minimal HTML string — no file I/O needed.

def inject_card_into_html(html: str, new_card: str,
                           marker_start: str = "<!-- PROJECTS-START -->",
                           marker_end: str = "<!-- PROJECTS-END -->") -> str:
    """
    Core injection logic (copied from server.py for testing).
    Finds the marker comments and inserts the new card before PROJECTS-END.
    """
    if marker_start not in html or marker_end not in html:
        raise ValueError("Markers not found in HTML")

    # Split the HTML at the END marker
    before_end, after_end = html.split(marker_end, 1)

    # Insert card just before the end marker
    return before_end + new_card + "\n    " + marker_end + after_end


# Minimal HTML that mimics the real structure (only the relevant part)
SAMPLE_HTML = """
<div class="project-grid">
  <!-- PROJECTS-START -->
  <div class="project-card">Existing card</div>
  <!-- PROJECTS-END -->
</div>
"""

NEW_CARD = '<div class="project-card">New project</div>'


def test_card_is_inserted():
    """The new card should appear somewhere in the output HTML."""
    result = inject_card_into_html(SAMPLE_HTML, NEW_CARD)
    assert NEW_CARD in result, "New card was not found in the output HTML"


def test_existing_card_preserved():
    """Injection must not erase existing cards."""
    result = inject_card_into_html(SAMPLE_HTML, NEW_CARD)
    assert "Existing card" in result, "Existing project card was lost!"


def test_new_card_before_end_marker():
    """The new card must appear BEFORE the PROJECTS-END marker, not after."""
    result = inject_card_into_html(SAMPLE_HTML, NEW_CARD)
    new_card_pos = result.index(NEW_CARD)
    end_marker_pos = result.index("<!-- PROJECTS-END -->")
    assert new_card_pos < end_marker_pos, "Card was inserted after the end marker"


def test_missing_marker_raises_error():
    """
    If the HTML file is malformed (no markers), we should get a clear error —
    not a silent failure or corrupted HTML.
    """
    bad_html = "<html><body>No markers here</body></html>"
    with pytest.raises(ValueError, match="Markers not found"):
        inject_card_into_html(bad_html, NEW_CARD)


def test_markers_still_present_after_injection():
    """Both marker comments must survive the injection."""
    result = inject_card_into_html(SAMPLE_HTML, NEW_CARD)
    assert "<!-- PROJECTS-START -->" in result
    assert "<!-- PROJECTS-END -->" in result


# ── 2. TESTING CARD HTML STRUCTURE ──────────────────────────────────────────
# We can't test Claude's output deterministically (it's generative),
# but we CAN test that whatever Claude returns has the required HTML structure.

def is_valid_project_card(html: str) -> bool:
    """
    Check that the generated card contains the required CSS classes.
    A simple structural validator — not a full HTML parser.
    """
    required_classes = [
        'class="project-card"',
        'class="project-title"',
        'class="project-desc"',
        'class="project-footer"',
    ]
    return all(cls in html for cls in required_classes)


def test_valid_card_passes():
    """A well-formed card should pass validation."""
    good_card = '''
    <div class="project-card">
      <p class="project-type type-ml">ML</p>
      <p class="project-title">My Project</p>
      <p class="project-desc">A cool project.</p>
      <div class="project-footer">
        <div class="tech-pills"><span class="tech-pill">Python</span></div>
        <a href="#" class="card-link">View →</a>
      </div>
    </div>
    '''
    assert is_valid_project_card(good_card)


def test_incomplete_card_fails():
    """A card missing required classes should fail validation."""
    bad_card = '<div class="project-card"><p>Oops, missing structure</p></div>'
    assert not is_valid_project_card(bad_card)


# ── 3. TESTING CONFIG VALUES ─────────────────────────────────────────────────
# Quick sanity checks that config.py has sensible values.
# These catch typos and accidental changes.

def test_config_values():
    """
    Config should have correct types and non-empty strings.
    Import is inside the test so it fails gracefully if config.py is missing.
    """
    try:
        import config
    except ImportError:
        pytest.skip("config.py not found — skipping config tests")

    assert isinstance(config.GITHUB_USERNAME, str) and config.GITHUB_USERNAME != ""
    assert isinstance(config.PORTFOLIO_REPO, str) and config.PORTFOLIO_REPO != ""
    assert isinstance(config.MAX_README_CHARS, int) and config.MAX_README_CHARS > 0
    assert isinstance(config.MAX_TOKENS, int) and config.MAX_TOKENS > 0
    assert "<!-- PROJECTS-START -->" in config.MARKER_START or config.MARKER_START == "<!-- PROJECTS-START -->"


# ── 4. TESTING README FETCH — MOCKED ────────────────────────────────────────
# We don't want tests to make real HTTP requests:
#   - They're slow
#   - They fail if GitHub is down
#   - They use your API rate limit
#
# Instead, we "mock" the HTTP call: replace it with a fake that returns
# what we tell it to. Same principle as using a synthetic control in an
# experiment — you control the output to test the logic around it.

def test_readme_fetch_success(monkeypatch):
    """
    Simulate a successful GitHub API response.
    monkeypatch is a pytest built-in for temporarily replacing functions.
    """
    import httpx

    # Fake response object that mimics httpx's Response
    class FakeResponse:
        status_code = 200
        text = "# My Project\nThis is a great project."

    # Replace httpx.get with a function that always returns our fake response
    monkeypatch.setattr(httpx, "get", lambda url, headers=None: FakeResponse())

    # Now call your actual function
    # (adjust the import path if needed)
    try:
        from server import get_repo_readme
        result = get_repo_readme("some-repo")
        assert "My Project" in result
    except ImportError:
        pytest.skip("server.py not importable from test location")


def test_readme_fetch_404(monkeypatch):
    """Simulate a 404 — repo doesn't exist or is private."""
    import httpx

    class FakeResponse:
        status_code = 404
        text = ""

    monkeypatch.setattr(httpx, "get", lambda url, headers=None: FakeResponse())

    try:
        from server import get_repo_readme
        result = get_repo_readme("nonexistent-repo")
        # Should return an error message, not crash
        assert "404" in result or "Could not" in result.lower()
    except ImportError:
        pytest.skip("server.py not importable from test location")


# ── HOW TO READ TEST OUTPUT ──────────────────────────────────────────────────
# When you run: pytest test_portfolio_agent.py -v
#
# PASSED  → test logic works as expected ✓
# FAILED  → something broke, pytest shows you exactly what
# SKIPPED → test needs a file that wasn't found (not a failure)
#
# Aim: all tests PASS or SKIP — never FAIL on working code.