# Cairn playbook, what to do, and when

Every date is 2026. **All hackathon deadlines are UTC.** Pakistan is UTC+5, so 23:59 UTC on Sep 10 is **04:59 on Sep 11 your time**. Do not aim for the deadline; aim for Sep 10 morning.

| Milestone | Date | Hard? |
|---|---|---|
| Registration closes | Mon Aug 31, 23:59 UTC | **Hard. Miss it and there is no entry.** |
| Build window opens | Tue Sep 1 | Hard |
| Partner workshops | Sat Sep 5 - Mon Sep 7 | Optional, attend if you can |
| Submission closes | Thu Sep 10, 23:59 UTC | **Hard** |
| Judging | Fri Sep 11 - Sat Sep 12 |, |
| Winners announced | Sun Sep 13 - Tue Sep 15 |, |

Two windows, and they do different work. **Aug 21-31 is the prep window**: accounts, brand, learning, audience. Nothing that counts as building. **Sep 1-10 is the build window**: all code, all commits.

---

# PART A: prep window (Aug 21-31)

## TODAY, Fri Aug 21: register and claim the name

Do these four in order. Ninety minutes total.

### A1. Register the team

Do this before anything else. Everything else on this page can slip; this cannot.

Go to **https://hack.sibyllabs.org/register**.

**Done. Registered as Prime Works.** Your build page is `hack.sibyllabs.org/team/prime-works-4c21`. Keep that link private, anyone holding it can edit your submission. Bookmark it and mail it to yourself.

The team name stays Prime Works and Cairn stays the product name. That split is fine and normal, just be consistent: the repo, the README, the video and the posts all say Cairn.

If the "what are you thinking of building" box is still empty, paste this:

> Cairn, a memory-native trust layer for agent commerce. Agents about to transact with a stranger have no reliable way to check them: on Base, most ERC-8004 reputation feedback is Sybil-generated and can be fabricated for fractions of a cent. Cairn only records interactions it witnessed itself, ACP jobs, escrow outcomes, delivery hashes, keeps an isolated dossier per counterparty in Sibyl Memory, and returns a verdict with the observations it rests on. Memory is the entire product: delete it and there is no record to reason over. Planning Base for on-chain reads and attestation writes, and Virtuals ACP as a registered Evaluator agent.

Save the private build-page link the moment you get it. **That link is your submission**: there is no separate form. Bookmark it and email it to yourself.

### A2. Join the Discord

**https://discord.gg/csya975jMa**: build updates, questions, and the workshop links land there. Introduce yourself in one line. You'll want the relationships later for design partners.

### A3. Buy the domain

`usecairn.xyz` on Cloudflare, same as you did for gowarrant.xyz. Add email routing while you're in there so `hello@usecairn.xyz` works.

Set up the DNS records now so nothing is blocking on Sep 1:

| Record | Name | Points to |
|---|---|---|
| CNAME | `@` | Vercel |
| CNAME | `explorer` | Vercel |
| CNAME | `docs` | Vercel |
| CNAME | `api` | the Fly.io app |

All three web hostnames go to the **same** Vercel project. Middleware rewrites by `Host` header, so it stays one codebase. The spec is in `docs/BRIEF.md` part 1.

### A4. Create the GitHub repo

Private for now, public on Sep 1.

```bash
# unzip the scaffold I gave you, then:
cd cairn
git init
git add .
git commit -m "brand, tokens, brief and docs, prep window, pre-build"
gh repo create cairn --private --source=. --push
```

That first commit is honest and dated. It's what the Prior Work declaration in the README refers to. **Don't backdate anything and don't squash it later**: a clean, truthful history is worth more than a tidy one.

---

## Sat Aug 22: get Sibyl Memory running and touch it yourself

The single most valuable prep day. Don't outsource this one to Claude Code, you need the feel of it.

### Set up WSL2 first

Windows Application Control has blocked native bindings on you before, and this project is Python plus a Linux deploy target. Do the whole thing in WSL2 (Ubuntu). It'll save you a day somewhere around Sep 3.

```bash
wsl --install -d Ubuntu     # PowerShell as admin, then reboot
```

Everything below runs inside WSL.

### Install and activate

```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip
python3 -m venv ~/.venvs/cairn && source ~/.venvs/cairn/bin/activate

pip install 'sibyl-memory-cli[mcp]'
sibyl init        # opens a browser; sign in with wallet or email + code
sibyl status      # note your tier and cap, screenshot this for the README
```

If you hit an "externally managed environment" error, the venv above already solves it.

### Wire it into Claude Code

```bash
sibyl setup claude-code
```

Then restart Claude Code. This is worth doing for its own sake: your build sessions will carry context across days.

### Play with it for thirty minutes

```python
from sibyl_memory_client import MemoryClient
m = MemoryClient.local("/tmp/play.db")

m.set_entity("counterparty", "acme", {"risk": "high"})
print(m.get_entity("counterparty", "acme"))

m.write_event(evaluated=["acme job 88"], acted=["held"], forward=["recheck in 30d"])
print(m.read_events(limit=5))

m.set_tenant("agent-a"); m.set_entity("note", "x", {"v": 1})
m.set_tenant("agent-b"); print(m.list_entities())   # empty, isolation works
```

Notice three things: it works offline with no credentials, `set_tenant` genuinely isolates, and `write_event` has an `evaluated`/`acted`/`forward` shape. Those three facts are the foundation of the whole build.

Then read `docs/TECH-PRIMER.md` end to end.

---

## Sun Aug 23 to Mon Aug 24: the ACP agent, step by step

This is the ×1.25 multiplier. It involves real money and a real wallet, so go slowly and read each command before running it.

**Costs about $25-30 in USDC plus a few dollars of ETH for gas. Budget $40.**

### Step 1, install the CLI

```bash
node -v                                          # must be ≥ 18
npm install -g @virtuals-protocol/acp-cli
acp --version
```

### Step 2, sign in

```bash
acp configure
```

Opens a browser for OAuth. Tokens go into your OS keychain and refresh automatically. **You never paste a private key into the CLI.** If any guide tells you to, you're reading the old ACP v1 docs, stop.

### Step 3, create the agent

```bash
acp agent create
```

Provisions an on-chain wallet and an email inbox for the agent. When it asks for a name and description, use:

- **Name:** `Cairn`
- **Description:** `Neutral evaluator. Returns a counterparty's grounded record, what we witnessed, not what was claimed.`

### Step 4, add the signing key

```bash
acp agent add-signer
```

A P256 key, approved in the browser. **Required before the agent can sign anything on-chain.** Easy to skip and painful to discover on Sep 8.

### Step 5, verify

```bash
acp agent whoami
acp wallet address --json
```

Copy the address into your `.env.local` as `ACP_AGENT_ADDRESS`, and also into a note. You'll need it in the demo.

### Step 6, fund the wallet

```bash
acp wallet topup --chain-id 8453 --method coinbase --amount 25
# --method card and --method qr also work if Coinbase is awkward from Pakistan
```

Chain 8453 is Base mainnet. Also send a few dollars of ETH to the same address for gas.

### Step 7, a dry run, so Sep 8 isn't the first time

```bash
acp browse "data analysis"      # see what's out there
```

Don't create a paid job yet. You just want to confirm the CLI talks to the network and your wallet shows a balance.

### Step 8, grab the agent-readable skill file

```bash
cat "$(npm root -g)/@virtuals-protocol/acp-cli/SKILL.md" >> ~/cairn-acp-skill.md
```

On Sep 8 you'll append this to the repo's `CLAUDE.md` so Claude Code can drive the CLI without guessing.

### Step 9, the attestor wallet (separate, for Base writes)

Create a **fresh** wallet for publishing attestations. Never reuse one holding anything you care about. Fund it with $5 of ETH on Base. Private key goes in `.env.local` as `CAIRN_ATTESTOR_KEY` and nowhere else, `.gitignore` already excludes it.

---

## Tue Aug 25 to Wed Aug 26: get a Base RPC and index a sample by hand

**Get an RPC URL.** Alchemy, QuickNode or Chainstack. The free tier is plenty. Base mainnet. Put it in `.env.local` as `BASE_RPC_URL` and confirm it responds:

```bash
curl -s -X POST $BASE_RPC_URL -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}'
```

**Then read the registries by hand, once.** Not to build the indexer, to know what the data actually looks like before Claude Code writes code against it.

Open BaseScan on `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (Identity) and `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` (Reputation). Look at recent `Registered` and `NewFeedback` events. Follow two or three `agentURI`s to their off-chain registration files. You'll immediately see the thing the paper describes: lots of registrations, very few with a live service endpoint.

**Decide the scope and write it down.** The free Sibyl tier caps `memory.db` at ~5 MB. You cannot fit all 28,592 rated Base agents. Pick one:

- **Scope it**: index only ACP-active agents, roughly 2,000. Honest, free, demos identically. **Recommended.**
- **Pay**: `sibyl upgrade`, $29/month in USDC, cap removed.

Whichever you pick, write it into the README. Silent truncation that a judge discovers is far worse than a stated limit.

---

## Thu Aug 27 to Fri Aug 28: the landing page and the waitlist

This is PMF groundwork, and it's allowed: it's marketing, not the build.

Ship a **one-page** `usecairn.xyz`. Hero, the four stat rows, one waitlist field. Use `cairn-tokens.css` and the marks. Don't build the real landing page, that's phase 6 inside the window. This is a placeholder that collects emails.

Set up the X account (`@usecairn` or similar) with `brand/cairn-app-icon-1024.png` as the avatar. Post once:

> Most agent reputation on Base is fake. 90.6% of ERC-8004 reviewers show coordinated Sybil behaviour; strip them and 86.8% of rated agents have no valid feedback left. Building Cairn for @sibyl_labs_' memory hackathon, an agent that only records what it witnessed itself. usecairn.xyz

Then go find **three design partners**. Post in the Sibyl Discord, the Virtuals Discord, and reply to ACP builders on X. What you want is three people who will say publicly "I'd use this." Named, quotable, verifiable in five minutes. That's what turns the PMF bonus from 0 into something.

---

## Sat Aug 29 to Sun Aug 30: dry run the whole thing

**Read `docs/BRIEF.md` cover to cover.** You wrote the plan; now check you agree with it. Anything you'd change, change now, not on Sep 4.

**Do a throwaway build.** New folder, outside the repo. Wire `MemoryClient` to FastAPI and return a fake verdict over HTTP. Delete it afterwards. The point is to find the friction (Python imports, WSL networking, CORS) while it still costs you nothing.

**Set up Fly.io.**

```bash
curl -L https://fly.io/install.sh | sh
fly auth signup
fly volumes create cairn_data --size 1 --region sin   # Singapore, closest to you
```

Don't deploy anything. Just have the account and the volume ready.

---

## Mon Aug 31: last day to register

If you somehow haven't registered, **do it now**. 23:59 UTC is 04:59 on Sep 1 your time.

Otherwise: rest. Clear your calendar for the next ten days. Tell people you're unavailable.

---

# PART B: build window (Sep 1-10)

One phase per Claude Code session. Paste-ready prompts are in `docs/BRIEF.md` part 14.

**Every day, before you stop:** commit with a real message, and post nothing publicly except on the two build-log days. The commit history is part of the submission.

### Phase 0 (Tue Sep 1): scaffold
Make the repo public. Monorepo layout, tokens installed, `CairnMark` rendering with all four standings, favicons generated, Python side confirmed working with `sibyl status` output pasted into the README. **No page content.** Ends with a file tree and the mark on screen.

### Phase 1 (Tue Sep 1 to Wed Sep 2): the memory adapter

**This is the most important session of the ten days.**
`apps/agent/memory/store.py` and `tiers.py`. Tenancy, tier policy, promotion at three occurrences, decay-based demotion, contradiction handling, the `forward` baton. **Tests for all four behaviours.** No UI, no chain calls. If you only get one thing right in ten days, this is it.

### Phase 2 (Wed Sep 2 to Thu Sep 3): the Base indexer
Registry reads via web3.py, observation extraction, evidence hashing, journal writes. Resumable via cursor, never double-writes. Ends with a real count: N agents, M observations.

### Phase 3 (Thu Sep 3 to Fri Sep 4): verdict engine and deletion test
Deterministic verdict, reviewer weighting, then `scripts/deletion_test.py` producing exactly the output in the README. **Do not let this slip.** It's the gate.

### Phase 4 (Fri Sep 4): the API
FastAPI: `/v1/lookup`, `/v1/observations`, `/v1/verdict`, and the real `?memory=off` bypass.

### Phase 5 (Sat Sep 5): UI kit and The Stack
Components, `/kitchen-sink`, then The Stack to spec and the deletion toggle wired to the real API. **Attend the Base and Virtuals workshops today or tomorrow if the timing works**: ask about Evaluator registration specifically.

### Phase 6 (Sun Sep 6): landing page
Section by section from brief part 7, copy verbatim. Screenshot at 390px and 1440px after each section. **Post build-log #1 today**: the deletion toggle as a short video clip, tagging @sibylcap, @base and @virtuals_io.

### Phase 7 (Mon Sep 7): explorer
Dossier view, reviewer view, the prior panel, cmd+K. Real loading, empty and error states everywhere.

### Phase 8 (Tue Sep 8): partner stacks

**This is the multiplier day.**
```bash
acp offering create      # "Counterparty dossier"
```
Then run **one real ACP job end to end** with Cairn as Evaluator, and **one Base attestation write**, and confirm you can do both live without a rehearsal. Both need to be on camera on Sep 10.

If something breaks here, you still have two days. If you'd left it to Sep 9, you wouldn't.

### Phase 9 (Wed Sep 9): README, docs, PMF artifact
Finish the README with the file-and-line memory map. Write the memory implementation note. **Publish the PMF artifact**: the grounded scan of your indexed Base set, as a public page with the numbers. Post build-log #2 pointing at it.

### Thu Sep 10: record and submit
Record the demo per brief part 15. The cold-start beat is **one continuous unedited take** with a clock or `git rev-parse HEAD` visible on screen.

**Submit by 18:00 UTC, 23:00 your time.** Not 23:59 UTC. Something will go wrong with the upload and you want six hours of slack.

Full field-by-field drafts are in `docs/SUBMISSION.md`, including the two fields judges score the 40% from. Final checklist before you mark it ready:

- [ ] Repo public, MIT licence present, real commit history
- [ ] README opens with the memory map, file paths a judge can follow in two minutes
- [ ] `python scripts/deletion_test.py` runs clean from a fresh clone
- [ ] Demo video 2-5 min, cold-start beat unedited, timestamp visible
- [ ] Memory implementation note written
- [ ] Both partner stacks declared **and shown working in the video**
- [ ] Two public posts live, tagging @sibylcap and each claimed partner
- [ ] Prior Work declaration honest and complete
- [ ] Build page marked **ready**

---

## The four ways this goes wrong

**You skip Aug 23-24 and try to register the ACP agent on Sep 8.** OAuth stalls, funding takes a day to clear, the signer step fails, and you lose the ×1.25. That single multiplier is worth more than any feature you could build in its place.

**You build the pretty parts first.** The landing page is 15 points. The memory layer is 40 and it's also the pass/fail gate. Phases 1 through 3 come first even when they're less fun.

**You let the free-tier cap surprise you.** Decide the scope on Aug 26 and put it in the README.

**You submit at 23:50 UTC.** Something always breaks. Submit Sep 10 morning; you can keep committing after you mark it ready.
