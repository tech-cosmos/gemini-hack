---
name: hackathon
description: Run a hackathon with the Hackathon Kit, a reusable team setup where every person works with their own AI agents and the repo is the shared memory (roles, lanes, directives, live log, gates, evidence). Use when the user says "start a hackathon", "I'm at a hackathon", "set up the hackathon kit", "I'm the lead / a teammate for <event>", "join the hackathon repo", or "wrap up the hackathon". Covers lead, teammate, solo and wrap-up modes.
---

# Hackathon Kit

The kit is a private GitHub template, `tech-cosmos/hackathon-kit` (keep a local clone, for example
`~/hackathon-kit`, and `git pull` it before each event). It holds process only: `AGENTS.md`, hooks,
coordination scripts and empty docs. No product code, so it can be used at events that require the project
to be built on site (disclose it under "reused components"). `KIT.md` in the repo is the manual; read it
once per session before acting.

**The idea:** people and agents on different laptops can't read each other's chats, so the repo is the
only shared memory. One person leads; the lead's agent writes plans, decisions and tasks into the repo;
hooks and `scripts/watch` make every agent read them without being asked.

First work out the mode. If the user didn't say, ask one question: "Are you the lead, a teammate on
someone else's repo, or solo?"

## Mode: lead (or solo)
1. Ask only for what is missing: event name, start and deadline (local time), teammates' GitHub usernames
   (none = solo), and a budget if there is one.
2. Create the repo from the template and set it up:
   ```bash
   gh repo create <event-slug> --private --template tech-cosmos/hackathon-kit --clone && cd <event-slug>
   scripts/init --event "<Event>" --start YYYY-MM-DDTHH:MM --deadline YYYY-MM-DDTHH:MM --invite a,b,c
   ```
   Private is the default. Make it public only if the user says the event requires it, and never with
   keys in it.
3. Give the user the paste message `init` printed, in one fenced block, for the team chat.
4. Read `docs/PLAYBOOK.md` in the new repo and follow it from there: fill `docs/BRIEF.md` and
   `docs/SUBMISSION.md` from what the organizers gave, then ideas by spike test, the demo written before
   building, lanes, directives, the loop.
5. Start `scripts/watch` with the Monitor tool (timeout 30 minutes) and start it again every time it
   expires. Its lines (NO-ACK, REQUEST, BLOCKED, GATE, CLOCK) are your cues to act.
6. The user decides the track, the idea, money, anything signed, and anything public. Everything else
   inside the playbook's bounds you do without asking.

## Mode: teammate on a kit repo
1. Follow `docs/SETUP.md` ("Agent steps") in their repo: sign in to `gh`, accept the invite, clone, keys
   into `.env` by the user's own hand, read `AGENTS.md`, `scripts/catchup`, then `scripts/claim <N>`.
2. Keep `scripts/watch` running with the Monitor tool. On a DIRECTIVE line: `scripts/ack <N>` at once, do
   it before other work, `scripts/done <N> "what you did"`.
3. Work as a lane owner: only issues you claimed, inside their folders, own PRs squash-merged after
   `scripts/check`. Need anything else: `scripts/request`.
4. Inside the lane: test before building with a pass mark written first, one writer per folder (extra
   agents in their own git worktrees), stop idle agents, ask a different model when stuck.

## Mode: teammate on a team with its own system
Leave the kit out. Follow their rules file first. Keep only the lane habits above, and set up a small
Monitor loop on their repo for new assignments and replies so the user isn't the message bus.

## Mode: wrap-up (after the result)
1. `scripts/stats` in the event repo.
2. Write the story of the day wherever the user keeps notes: result, team, what was built, numbers from
   `docs/EVIDENCE.md` only, what to reuse, what went wrong, where things are.
3. Send what got in the way back to the kit: open an issue on `tech-cosmos/hackathon-kit` with what
   happened and what would have prevented it.

## Rules that hold in every mode
- Keys only in `.env`, typed in by the user. Never print, commit or ask for them in chat.
- Numbers only from files a script produced, via `docs/EVIDENCE.md`.
- Only organizer keys and free tiers; estimate before any batch and log the spend.
- The organizers' rules beat the kit's.
- The kit is private. Don't publish it or pass it on.
