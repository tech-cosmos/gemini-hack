# The organizers' requirements, short version

Our summary of what the organizers gave us. If this file and their brief differ, their brief wins.
Source: the participant guide at https://cerebralvalley.ai/e/gemini-4-nyc/details (login needed; the lead
saved a copy). Venue: The Malin Chelsea, 220 W 26th St. Wi-Fi "Hackathon" / "hackathon".

## Timeline (Sat 2026-11-21, ET)
| What | When |
|---|---|
| Kick-off | 10:00 |
| Building starts | 10:30 |
| Submission deadline | **17:00** (form + 1-minute demo video) |
| Round one judging (rooms, 3 min live demo + 2 min Q&A) | 17:00 – 18:45 |
| Final round (top 6 on stage, same format) | 19:00 – 20:00 |
| Winners | 20:15 |

## The hard requirements (every project)
- Build in **one of the two problem statements** below.
- Use **at least two Gemini 4 models** (Argon, Carbon, Neon, Hydrogen), **each with a clear job**.
- **Go beyond a text box**: "voice, camera, video, images, documents or generated media should be central
  to how the project works."
- **Repository must be public.** All team members added on the submission page.
- Demo shows only what we built today. "Judges must be able to clearly identify what was created during the
  event. Failure ... will result in immediate disqualification." The kit (process files, no product code)
  is a reused component: say so in the README.

## Problem statements
**One: 5 Sigma.** "Pick a real task that today's agents struggle with, and build a Gemini 4 system that does
it reliably ... Then prove it: build an evaluation that tests your system on inputs you didn't prepare for,
and show how it compares to a simple baseline." Questions they ask: what's the baseline and how much
better; a test set with messy inputs and edge cases; where it still fails and what changed after.
Their examples: messy real-world forms (scanned PDFs, handwriting) tested on 50 unseen documents vs a
single-model baseline; a coding agent fixing real GitHub issues measured by the repo's own tests.

**Two: Element 119.** "Build something that only works because Gemini 4 can see, hear and generate media."
Video, audio, images or documents are the core input (and can be the output). "Use any Gemini 4 models
you want plus the Decisions API, and push them as far as they go: longer footage, messier audio, more
streams at once, faster real-time loops. Then show us where it breaks."
"Not allowed: text-only chatbots, demos that only run on scripted inputs, and evaluations made up entirely
of examples the team wrote to pass."

**Bonus: Build with Commerce (Shopify).** shop.dev, product discovery to a shopping agent. Open to all.

## Judging criteria (round one; the final round weights them equally)
| Criterion | Weight | What it means |
|---|---|---|
| Live Demo | 35% | "Does it work live on real, unrehearsed inputs? NOT slides or a Figma file." |
| Proof It Works | 25% | "a test against a baseline, an honest look at where it fails, or a plan the agent checks its own output against" |
| Creativity | 20% | "a problem others avoid? ... beyond a text interface in a way that matters" |
| Gemini 4 & Decisions API Use | 20% | at least two Gemini 4 models with clear jobs, plus the Decisions API; how far it pushes reasoning, speed or multimodality |

## Prizes
1st $7,500 · 2nd $5,000 · 3rd $2,500 · **Best use of Managed Agents $5,000** · Best use of Shopify $2,500 Shop Cash.

## Banned ("Sample Anti-Projects", strictly no)
AI mental health advisor · basic RAG · Streamlit apps · image analyzers · "AI for Education" chatbot ·
AI job application screener · AI nutrition coach · personality analyzers · AI medical advice ·
anything where a dashboard is the main feature · sports analyzers or coaches.

## Resources
- "Build with Gemini 4 Builder Guide" (Google Drive, linked from the guide): which model does what,
  **Gemini Decision 1** for fast routing and scoring, live voice/camera/speech/image/video/music models,
  setup, recipes for multi-model loops, the Decisions API, Managed Agents (Google-hosted or self-hosted
  sandboxes), agentic video understanding, and what to avoid in a live demo.
- Gemini accounts only for checked-in builders, in batches. Contact: blerta@cerebralvalley.ai / Discord.
- Shopify: shop.dev; Solutions Engineers on site and in Discord.
- Discord: #announcements, #rules, #questions (ping @CV).

## Model notes (public sources, verify against the builder guide)
Hydrogen: fastest and cheapest, everyday coding and agent loops. Neon: high-performance coding and
multi-step reasoning at low latency. Carbon, Argon: frontier models for the hardest work.
Managed Agents (Gemini API, Interactions API): one call starts an agent with tools and code execution
in an isolated Linux sandbox; custom instructions/skills (AGENTS.md, SKILL.md), background runs,
remote MCP, custom functions, hooks, budgets, scheduled triggers.

## What the judges and mentors said (exact words, with the time)
-

## Questions still open
1. Decisions API: what exactly does it return, latency, and limits? (builder guide)
2. Which Gemini 4 models can Managed Agents run on?
3. Live demo: is there a projector, and can we use the venue Wi-Fi for real-time video?
