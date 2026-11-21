# Hackathon Kit

A reusable way to run a hackathon team where every person works with their own AI agents. It contains
process only (rules, hooks, scripts, empty docs): no product code, so it is safe to bring to events that
require the project to be built on site. Disclose it under "reused components".

**The idea:** people and agents on different laptops can't read each other's chats, so **the repo is the
only shared memory**. One person leads. The lead's agent writes plans, decisions and tasks into the repo;
hooks and a watcher make every other agent read them without anyone asking.

Two layers:
- **Between people** (this kit): roles, lanes, directives, the live log, gates, evidence.
- **Inside one person's lane** (your own swarm, e.g. the Conclave): test before building, one writer per
  folder, idle agents stopped, a different model for fresh ideas.

## Start an event

**As the lead**
```bash
gh repo create <event-name> --private --template tech-cosmos/hackathon-kit --clone && cd <event-name>
scripts/init --event "HackX 2027" --start 2027-01-16T09:30 --deadline 2027-01-16T15:30 --invite maya,sam,li
```
`init` sets the clock, creates the labels and the live-log issue, writes your login into the rule files,
invites the team and prints the message to paste to them. Then open your agent in the folder; it follows
`docs/PLAYBOOK.md`.

**As a teammate** on someone's kit repo: paste the one-line prompt from `docs/SETUP.md` into your agent.

**Solo:** the same commands without `--invite`. You are the lead; directives fall away, the gates, the
spike test, demo-first and the evidence file still earn their keep.

**On a team that runs its own system:** leave this kit at home, follow theirs, and keep only the lane
habits (and a watcher on their repo).

## What happens automatically
| When | What runs | What the agent sees |
|---|---|---|
| A session starts | `scripts/catchup` (Claude Code hook) | role, clock, briefing, its directives, issues, log, main |
| Every message | `scripts/directives-check` (hook) | only directives that are for this person; nothing otherwise |
| All the time | `scripts/watch` (Monitor or a spare terminal) | a line the moment a directive, assignment, reply or gate needs it |
| Every log post | `scripts/log` | open directives again, so they reach an agent mid-task |

Other tools (Codex, Cursor, Copilot, Gemini) have no hooks: their pointer files tell them to run the same
scripts by hand before each task.

## Scripts
| Script | Who | What it does |
|---|---|---|
| `init` | lead, once | clock, labels, live log, lead's name in the files, invites, paste message |
| `catchup` | all | the whole state in about 60 lines |
| `watch` | all | pushes events: DIRECTIVE, ASSIGNED, REPLY, GATE, CLOCK; lead also REQUEST, BLOCKED, NO-ACK |
| `clock` | all | time left and every gate with its time |
| `directive "<who>: <what>"` | lead | opens a directive, assigns the people named, logs it |
| `ack <N>` · `done <N> "..."` | all | acknowledge; finish (closes when everyone named is done) and log |
| `claim <N> [folders]` | all | take an issue; refuses if someone else has that folder in an issue or PR |
| `request [--blocked] "..."` | lane owners | ask the lead for a decision or a change |
| `log "..."` | all | one line to the live-log issue |
| `check` | all, before each merge | no keys tracked + the golden path (the lead fills it in) |
| `budget` | all | API spend (OpenRouter built in) |
| `stats` | lead, at the end | issues closed, PRs merged and lines added per person |

Config lives in `kit.env` (event, lead, start, deadline, gates as percentages of the build window). The
scripts are bash, run on macOS, Linux and Git Bash on Windows, and need only `git` and `gh`.

## Where each kind of information lives
| Information | Where |
|---|---|
| Rules, roles, lanes, the golden path | `AGENTS.md` |
| What the organizers and judges want | `docs/BRIEF.md` |
| The plan right now | `docs/BRIEFING.md` "Now" |
| Team name, upload link, who uploads | `docs/SUBMISSION.md` |
| Decisions | `docs/DECISIONS.md` |
| Ideas and spike results | `docs/IDEAS.md` |
| The demo and the judge Q&A | `docs/DEMO.md` |
| Every number we say | `docs/EVIDENCE.md` |
| Dead ends, findings, limitations | `NOTES.md` |
| Orders | issues labeled `directive` |
| Asking the lead | issues labeled `request` |
| Everything as it happens | the live-log issue |
| Progress | one `status/` line per PR |
| Keys | the team chat, then `.env`. Never the repo |

## Why it is built this way (lessons from the first run, Innodata, 2026-11-14, 1st place)
| What went wrong | What the kit does about it |
|---|---|
| Directives reached an agent only when its person typed something; one went unacknowledged for 26 minutes and the lead had to take the work over | `watch` pushes them; the lead gets NO-ACK after `KIT_ACK_MIN` minutes |
| Every open directive was shown to everyone on every message, long after it was done | directives are assigned to the people named; `directives-check` shows only yours; `done` closes them |
| Two 3D demos, two slide decks and two phone pages were built in parallel | `claim` refuses a folder someone else already has in an issue or PR |
| The team name arrived 25 minutes before the upload target | `docs/SUBMISSION.md` is the first gate, and every catch-up warns until it is full |
| Teammates felt like subagents | lanes (whole pieces with an owner), not tickets handed down one by one |
| A task only a person could do (a timed human baseline) never landed | the `human` label, a desktop notification, and the lead says it out loud |
| The catch-up printed 22 KB and got cut off | `catchup` is capped at about 60 lines |
| Windows line endings broke a byte-for-byte check | `.gitattributes` forces LF from the first commit |
| Someone asked to commit the API keys | `check` refuses a tracked `.env` or anything shaped like a key |
| A lead's name was hardcoded in every script | one config file, defaults read from the git remote |

Kept as it was, because it worked: the repo as shared memory, hooks, the live log, decisions that are
final once written, the demo written before building, the evidence file, own-PR squash merges, picking
the idea by a spike test, and a keep rule written before the run.

## Sharing it with a friend
Send them `kit/SHARE.md` (written for their Claude) and add them as a collaborator:
`gh api -X PUT repos/tech-cosmos/hackathon-kit/collaborators/<their-login>`.
GitHub offers no read-only level on a personal private repo, so this grants write access; the share file
asks them to treat it as read-only and send changes as issues or pull requests.
`kit/SKILL.md` is the shareable copy of the `hackathon` skill; keep it in step with the personal one.

## After an event
Run `scripts/stats`, write the story of the day while it is fresh, and bring fixes back here: this
template only improves if each event's lessons land in it.

The process comes from Alex Epstein's setup at the Innodata hackathon (itself carried over from his
earlier events), rewritten and extended. Private; ask him before sharing it further.
