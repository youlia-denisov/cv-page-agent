# How the Portfolio Automation Works

Here's the idea behind `cv-page-agent`, in plain terms: tag a repo with `cv-page`, push to `main`, and a card for that project shows up on the portfolio site automatically. No copy-pasting HTML, no manually editing `index.html` every time something new ships.

## The short version

Add the `cv-page` topic to a repo → push → a card appears on `youlia-denisov.github.io`. That's it, that's the whole pitch.

## What actually happens when you push

1. You push to `main` in a project repo that has the GitHub Action set up.
2. The Action wakes up, checks out `cv-page-agent`, and runs `server.py` with the repo's name passed in automatically.
3. The agent asks itself two questions before doing anything: is this repo on the excluded list (so it never tries to process itself), and does it actually have the `cv-page` tag? If either answer is wrong, it just stops there — no card, no fuss.
4. If it passes both checks, the agent grabs the README, hands it to Claude to write up a card, and peeks at the current portfolio HTML to make sure that project doesn't already have one.
5. New project → the card gets slotted in and pushed live. Already there → nothing happens, which is exactly what you want.

## Adding a new project to the rotation

1. Tag the repo `cv-page` (Settings → About → gear icon → Topics).
2. Copy the workflow file from `wattwise-app` or `ngt-tracker` into `.github/workflows/update-portfolio.yml`.
3. Add `ANTHROPIC_API_KEY` as a secret in that repo (GitHub already hands over `GITHUB_TOKEN` for free, no setup needed there).
4. Push, then check the Actions tab to make sure it actually ran and didn't quietly fail.
5. If the project has its own pages worth linking to (a demo, a "how it works" writeup), flip on GitHub Pages for it too.

## A few design choices worth remembering

The portfolio repo itself stays lean — just `index.html`, `style.css`, and shared assets. Every project lives in its own repo with its own README and demo pages, served from its own GitHub Pages URL. The portfolio just links out to all of it rather than hosting everyone else's content directly.

The duplicate check is just a string match — it looks for the project's GitHub URL already sitting in the portfolio HTML. Simple, but it works as long as that URL format stays consistent.

And the tag-based trigger wasn't an accident — a manual list of "approved repos" would mean editing the agent's code every single time something new gets added, which defeats the whole point of automating this in the first place.

## Things that have bitten us before (and might again)

GitHub Pages takes a minute or two to actually go live after you flip it on — don't panic if a fresh URL 404s right away, just wait and refresh.

The GitHub topics API is picky and wants a specific `Accept` header (`application/vnd.github.mercy-preview+json`). Forget it, and the tag check just silently says "no tag found" even when there is one.

The portfolio update overwrites the whole `index.html` each time, so if two pushes land back to back, whichever one finishes last wins. Not a problem at this scale, but worth knowing.