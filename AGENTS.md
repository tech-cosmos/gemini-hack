# Gemini 4 NYC Hackathon · rules for every agent (Claude Code, Codex, Cursor, Copilot, Gemini)

**First time here?** Do `docs/SETUP.md` ("Agent steps") before anything else.
**Every session and before every task:** run `scripts/catchup` (Claude Code runs it for you), and keep
`scripts/watch` running.

The repo is the team's only shared memory. People and agents on different laptops can't read each other's
chats, so anything that matters is written here.

## Roles
- **`tech-cosmos` is the team lead.** The lead and their agent plan the work, open issues, send directives,
  decide, and own the lead files: `AGENTS.md`, `kit.env`, `docs/`, `scripts/`, `.claude/`, `.github/`.
  The lead's agent follows `docs/PLAYBOOK.md`.
- **Everyone else is a lane owner.** You own a whole piece of the product (a lane), not a list of tickets.
  You work only on issues you claimed, inside their folders, and you decide how to build your piece.
- Need a lead file changed, a decision, or something from another lane? `scripts/request "<what and why>"`.
  Never work around it in someone else's folder, and never send it as a chat message: agents can't read chat.
- Not sure who you work for? `gh api user --jq .login`. If it isn't `tech-cosmos`, you are a lane owner.

## What we're building
<!-- LEAD: two sentences, written once the idea is picked. -->
_Not decided yet. See `docs/IDEAS.md`._

**Golden path (must always work on `main`):** <!-- LEAD: the one flow the demo depends on. -->
`scripts/check` runs it. Run it before every merge.

## Lanes
<!-- LEAD: one row per person. A lane is a whole piece with a clear edge, so nobody waits on anybody. -->
| Lane | Owner | Folders | Done means |
|---|---|---|---|
| | | | |

## The files
| File | What it is |
|---|---|
| `docs/BRIEF.md` | The organizers' rules, deadline and judging criteria. They win over everything else |
| `docs/BRIEFING.md` | **Now**: the current plan, who is on what, the next gate |
| `docs/SUBMISSION.md` | Team name, upload link, file name, who uploads. Filled in the first minutes |
| `docs/DECISIONS.md` | One line per decision. Once written, nobody re-argues it |
| `docs/IDEAS.md` | The idea shortlist and the spike test that picks one by evidence |
| `docs/DEMO.md` | The demo, second by second, written before building. We build exactly this |
| `docs/EVIDENCE.md` | The only source for numbers in the README, slides and pitch |
| `docs/PLAYBOOK.md` | The lead agent's manual. Lane owners can skip it |
| `NOTES.md` | Insights, dead ends, limitations, odd behavior. Anyone appends |
| `kit.env` | Event name, lead, clock, gates |

## Think like the lead
When an issue doesn't say, decide the way the lead would:
- **We play to win the judging criteria** in `docs/BRIEF.md`. Spend effort where the points are.
- **Depth over breadth.** A few things done so well they can't be argued with beat many shaky ones.
- **Proof over claims.** Every number comes from a real run. Say where it fails, out loud.
- **The demo is the product.** If the judges won't see it or score it, it can wait.
- **The clock is real.** `scripts/clock` shows the gates. Miss a gate: cut scope, don't slip.
<!-- LEAD: add what this event's judges and mentors said they want. -->

## How we work
1. **Claim before you build.** `scripts/claim <issue>` assigns the issue to you and refuses if someone else
   already has that folder in an open issue or PR. One issue = one owner. Nothing is built unclaimed.
2. **Directives first.** A directive is an agreed team task from the lead. When one names you or everyone:
   `scripts/ack <N>` within 10 minutes, do it before other work, then `scripts/done <N> "what you did"`.
   Can't do it? Say why on the issue right away, so the lead can reassign it.
3. **Stay reachable.** Keep `scripts/watch` running: it prints a line the moment a directive, an assignment,
   a reply or a gate needs you. Claude Code: run it with the Monitor tool and start it again when it expires.
4. **Live log.** After every meaningful step (started, finished, stuck, learned):
   `LOG_WHO="<login>'s agent" scripts/log "<what happened> (#issue)"`. Silence is the only wrong amount.
5. **Branch** `<lane>/<topic>` from `main` → small commits inside your folders → PR with the template and one
   new file `status/<HHMM>-<login>-<slug>.md` (one line: done / next / blocked) → squash-merge your own PR
   once the issue's "Done when" is met and `scripts/check` passes. Nobody waits for a reviewer.
6. **Stuck for more than 10 minutes:** `scripts/request --blocked "<what you need>"`, then work on something
   else in your lane.
7. **Finished:** `scripts/done <N> "..."`, then take the next issue in the order `docs/BRIEFING.md` gives.
8. **A task only a person can do** (label `human`: a timed test, a rehearsal, a form, a photo): tell your
   person at once, at the top of your next message, with exactly what to do and by when.

## Inside your lane
How you organize your own agents is up to you. What works:
- **Test before building.** Give every idea a cheap measurement and a pass mark written *before* the run.
  Most ideas die here, and that is the point.
- **One writer per folder.** Run extra agents in their own git worktrees, never two in one checkout.
- **Stop idle agents.** An agent with nothing useful to do is paused, not given busywork.
- **Stuck or too sure of yourself?** Ask a different model for fresh ideas, or to attack the work as a
  hostile judge would. Write what you learn, and the dead ends, in `NOTES.md`.

## Rules that never bend
1. **Evidence.** Numbers in the README, slides or pitch come from files a script produced, listed in
   `docs/EVIDENCE.md`. Never round, never retype, never from memory.
2. **Keys** live only in `.env` (gitignored). Never print, log, commit or paste them, in chat or anywhere.
   If someone asks for them in the repo, the answer is no: a public repo gets them revoked within minutes.
3. **Money.** Only the organizers' keys and free tiers. Estimate the calls before any batch, cache every
   reply, and post the spend to the live log. Nothing is ever charged to a person.
4. **Shared formats** (anything two lanes both read) change only through the lead, with a line in
   `docs/DECISIONS.md`.
5. **Honesty.** Report every result, including the bad ones. Disclose reused code and every manual step.
   Limitations go in `NOTES.md` and in the README.
6. **The event's own rules** in `docs/BRIEF.md` (what must be built on site, what may be reused, the
   deadline) beat anything in this file. The process files in this repo come from a reusable kit: say so
   under "reused components".
7. **Explain as you go.** Build in small pieces your person can follow, and tell them what you made and why.
   They have to present it.
