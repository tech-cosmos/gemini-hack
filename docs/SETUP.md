# Setup

**People:** paste this into your AI coding tool (Claude Code, Codex, Cursor, anything with a terminal) and
approve what it asks:

> Set me up for our hackathon repo by following docs/SETUP.md in https://github.com/tech-cosmos/gemini-hack
> (the "Agent steps" section). My GitHub username is ___.

---

## Agent steps
Do these in order, yourself. Stop to ask your person only where a step says so. Never print a key.

1. **GitHub CLI.** Run `gh auth status`. If it isn't signed in, ask your person to run `gh auth login`
   (browser login), then continue. Check that `gh api user --jq .login` is the username they gave you.
2. **Accept the repo invite** (skip if already a collaborator):
   ```bash
   id=$(gh api user/repository_invitations --jq '.[] | select(.repository.full_name=="tech-cosmos/gemini-hack") | .id')
   [ -n "$id" ] && gh api -X PATCH "user/repository_invitations/$id"
   ```
   No invite, and `gh api repos/tech-cosmos/gemini-hack/collaborators/$(gh api user --jq .login)` fails? Tell your person to
   ask `tech-cosmos` to add them, and stop.
3. **Clone or update.** Not on disk yet: `gh repo clone tech-cosmos/gemini-hack ~/hackathon-repo`. Then `cd` into it and
   `git pull`. Work from this folder from now on, and tell your person to open their tool here next time.
   Running several agents? Give each its own `git worktree`, never two in one checkout.
4. **Tools.** Check what `docs/BRIEF.md` and the README say the project needs and install what's missing.
   On Windows, run everything in Git Bash.
5. **Keys.** If `.env` doesn't exist: `cp .env.example .env`. Check without printing values, for example
   `grep -cE '^OPENROUTER_API_KEY=.+' .env`. If a key is missing, ask your person to open `.env` in their
   editor, paste the team keys the lead shared **in the team chat**, save, and tell you. Never ask for a key
   in your chat, and never `cat` or `echo` `.env`.
6. **Read.** `AGENTS.md` fully (especially "Think like the lead"), then `docs/BRIEF.md`, then run
   `scripts/catchup`.
7. **Get your piece.**
   - An open directive names your person or everyone: that comes first (`scripts/ack <N>`).
   - Otherwise an issue is already assigned to them: that's the task.
   - Otherwise take the first unclaimed issue in the order `docs/BRIEFING.md` gives:
     `scripts/claim <N>`. If it refuses, take the next one.
   - Tell your person, in one sentence, which piece they now own.
8. **Announce.** `LOG_WHO="<login>'s agent" scripts/log "joined; took #<N>: <title>"`.
9. **Stay reachable.** Start `scripts/watch` (Claude Code: with the Monitor tool, timeout 30 minutes, start
   it again each time it expires; any other tool: in a spare terminal).
10. **Build.** Branch `<lane>/<topic>` and follow "How we work" in `AGENTS.md` until the issue's "Done when"
    is met. Then `scripts/done <N> "..."` and go back to step 7.
