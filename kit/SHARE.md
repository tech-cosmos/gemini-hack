# Hackathon Kit: context for a friend's Claude

**Who this is for:** you are a Claude session working for a friend of Shivam (`tech-cosmos` on GitHub).
Shivam is sharing his Hackathon Kit with your person. This file tells you what it is, how to install it,
how to try it in ten minutes, and how to use it at an event. Do the steps yourself; stop to ask your
person only where a step says so.

## What it is
A private GitHub template for running a hackathon team where every person works with their own AI agents.
It contains process only (a rulebook, two hooks, 15 small bash scripts, empty docs) and no product code.

The problem it solves: people and agents on different laptops can't read each other's chats. So **the
repo is the only shared memory**. One person leads. The lead's agent writes the plan, decisions and tasks
into the repo, and hooks plus a background watcher make every other agent read them without being asked.

Where it comes from: Shivam's team won 1st place at the Innodata hackathon (2026-11-14) using the
original version of this process, built by the team lead, Alex Epstein. Shivam rewrote it as a reusable
kit and fixed what went wrong that day. **The kit itself has not been through a real event yet**, so
treat the first use as a test and report what gets in the way.

## What your person needs
- A GitHub account and the GitHub CLI (`gh`), signed in.
- `git` and `bash`. macOS and Linux have them; on Windows use Git Bash.
- Claude Code is the best fit (the hooks and the watcher run by themselves). Other tools work, but they
  run the same scripts by hand.

## Step 1: get access
The template is private. Ask your person for their GitHub username and have them send it to Shivam, who
adds them as a collaborator. Then accept the invite:
```bash
gh auth status   # if not signed in, ask your person to run: gh auth login
id=$(gh api user/repository_invitations --jq '.[] | select(.repository.full_name=="tech-cosmos/hackathon-kit") | .id')
[ -n "$id" ] && gh api -X PATCH "user/repository_invitations/$id"
gh repo view tech-cosmos/hackathon-kit --json name --jq .name   # prints hackathon-kit when access works
```
If the last command fails, the invite hasn't been sent yet: tell your person, and stop here.

## Step 2: install
```bash
gh repo clone tech-cosmos/hackathon-kit ~/hackathon-kit
mkdir -p ~/.claude/skills/hackathon && cp ~/hackathon-kit/kit/SKILL.md ~/.claude/skills/hackathon/SKILL.md
```
- The clone is a reference copy: read `KIT.md` in it now. It is the manual.
- The skill makes "start a hackathon" work from any folder. Tell your person to start a new Claude Code
  session so it loads.
- Before each event: `git -C ~/hackathon-kit pull` and copy the skill again, in case it changed.

## Step 3: try it (ten minutes, no teammates needed)
Create a scratch repo from the template and walk the main flow. Everything here is private and free.
```bash
cd ~ && gh repo create kit-tryout --private --template tech-cosmos/hackathon-kit --clone && cd kit-tryout
scripts/init --event "Tryout" --start <now, as YYYY-MM-DDTHH:MM> --deadline <2 hours from now>
scripts/catchup                                   # the whole state: role, clock, plan, issues, log
scripts/clock                                     # the gates with their times
scripts/directive "<your person's login>: test directive"   # prints the new issue's URL
scripts/directives-check                          # shows it as not acked
scripts/ack <N> && scripts/done <N> "tried it"    # acknowledge, finish, close
scripts/watch --once                              # what the watcher would have pushed
```
Then show your person three things: the paste message `init` printed (that is all a teammate needs), the
gates from `scripts/clock`, and the live-log issue on GitHub. When they're done, they can delete the
`kit-tryout` repo on GitHub (repo Settings, at the bottom).

On macOS the watcher also shows desktop notifications; that is expected.

## Step 4: use it at an event
Your person only has to say one line; the skill has the detailed steps for you.

**They lead:** *"Start a hackathon: <event>, I'm lead. Building 9:30 to 3:30. Team: user1, user2."*
1. You create a private repo from the template and run `scripts/init`.
2. You give them one message to paste in the team chat. Each teammate pastes a line into their own AI
   tool, which accepts the invite, clones and claims a piece.
3. From then on you follow `docs/PLAYBOOK.md` in the new repo: you are their chief of staff. They tell
   you what they hear and decide; you write it into the repo, send directives, and keep the plan current.

**Someone else leads with the kit** (for example Shivam, on the same team): *"I'm a teammate on <repo>."*
You follow `docs/SETUP.md` in that repo and work as a lane owner.

**Solo:** the same start line without teammates.

**One rule for the table:** agree out loud who leads before anyone runs anything. Exactly one person
leads; it is coordination, not rank.

## How it works, in one table
| When | What runs | What the agent sees |
|---|---|---|
| A session starts | `scripts/catchup` (hook) | its role, the clock, the plan, its directives, issues, the live log |
| Every message | `scripts/directives-check` (hook) | only directives that are for this person |
| All the time | `scripts/watch` (Monitor tool or a spare terminal) | a line the moment a directive, assignment, reply or gate needs it |
| Every log post | `scripts/log` | open directives again, mid-task |

- **Roles** come from the GitHub login: the lead's login is in `kit.env`, everyone else owns a lane.
- **Directives** are GitHub issues assigned to the people named: ack within 10 minutes, do it first,
  mark it done. The lead is warned when nobody acks.
- **The live log** is one GitHub issue where every agent posts a line after each step.
- **Lanes:** each person owns a whole piece and its folders. `scripts/claim` refuses a folder someone
  else already has, so nothing is built twice.
- **The clock:** gates are percentages of the build window (5% submission facts, 15% idea picked by a
  spike test, 25% demo written, 45% golden path runs, 65% real results, 80% feature freeze, 90%
  submission built, 95% submitted and rehearsing).
- **Evidence:** every number in the README, slides and talk comes from a file a script produced.

## Rules
- **Keys** go only into `.env`, typed in by your person. Never print them, commit them or ask for them
  in chat.
- **The event's rules win.** Many events require the project to be built on site. The kit is process
  only; list it under "reused components" and ask the organizers if unsure.
- **It's private.** Don't publish the kit or pass it on. The process is credited to Alex Epstein.
- **Don't push to the kit repo.** GitHub has no read-only level on a personal private repo, so the invite
  comes with write access. Treat it as read-only: changes go in as an issue or a pull request for Shivam.

## Known limits (as of 2026-11-16)
- Tested by one person on one Mac. Not yet tested: two real accounts replying to each other, the
  `--invite` option with a real teammate, the budget script with a real key, Windows Git Bash, Linux.
- The clock uses each laptop's local time. Fine in one room; be careful with a remote team.
- In Claude Code the watcher stops after 30 minutes (the Monitor tool's limit) and must be started again.
- Labels and issues don't copy from a template: always run `scripts/init` in a new repo.

## When something gets in the way
Open an issue on `tech-cosmos/hackathon-kit` with what happened and what would have prevented it, or tell
Shivam. Every fix there reaches the next event repo either of you creates.

If your person wants to change the kit freely, make their own copy instead:
`gh repo create <their-login>/hackathon-kit --private --template tech-cosmos/hackathon-kit`, then
`gh repo edit <their-login>/hackathon-kit --template`, and replace `tech-cosmos/hackathon-kit` with their
repo in `KIT.md`, `scripts/init` and the skill file. Their copy then stops receiving Shivam's updates.
