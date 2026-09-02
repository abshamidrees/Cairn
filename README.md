<img src="brand/cairn-mark-standing.svg" width="72" alt="Cairn">

# Cairn

**A record, not a rating.**

Cairn is a memory-native trust layer for agent commerce. When one AI agent is about to pay another, Cairn answers the only question that matters. *Has this counterparty done what it said it would, before?* Then it shows you the observations the answer came from.

Built on [Sibyl Memory](https://docs.sibyllabs.org). Reads and writes on [Base](https://base.org). Operates as an Evaluator on [Virtuals ACP](https://os.virtuals.io/acp/overview).

**[usecairn.xyz](https://usecairn.xyz)** · **[explorer](https://explorer.usecairn.xyz)** · **[docs](https://docs.usecairn.xyz)** · **[demo video](#)**

> Submission for the Sibyl Labs Memory Hackathon, Sep 1-10 2026.

---

## Where memory is load-bearing

> **Judges: this is the two-minute answer.** Everything below is a real file path.

| What | Where |
|---|---|
| The only module that touches Sibyl Memory | `apps/agent/memory/store.py` |
| Writes, every observation lands in the journal | `apps/agent/memory/store.py` → `record_observation()` |
| Reads, the verdict pulls priors and evidence back out | `apps/agent/judge/verdict.py` → `load_prior()`, `gather_basis()` |
| Tier promotion, demotion and archival | `apps/agent/memory/tiers.py` |
| Cross-session baton (`forward`) drained on boot | `apps/agent/memory/session.py` |
| Proof it is load-bearing | `scripts/deletion_test.py` |

### The deletion test

The hackathon's gate is: *remove the memory layer, does it still do what it claims?* We ship the tool that answers it.

```bash
python scripts/deletion_test.py --agent 0x...
```

```
  memory ON      standing=grounded  confidence=0.87  basis=41 observations
  memory OFF     standing=thin      confidence=-     basis=0  observations
                 ↳ verdict engine returned NO_BASIS

  Cairn's core function is unavailable without the memory layer.  PASS
```

Exits non-zero if the memory-off run ever produces a usable verdict.

---

## How memory made this possible

Cairn is not a product that uses memory. Cairn is a product made of memory.

The thing being sold is an accumulated, grounded record of what agents have actually done. Strip the record and there is no product, not a degraded product, no product. A stateless model asked "should I pay `0x...`?" can only guess, because the answer lives entirely in what was observed before this moment.

Three memory patterns do the work:

**Tenancy as coordination.** `MemoryClient.set_tenant()` gives every counterparty and every reviewer a fully isolated dossier inside one database file. A single verdict reads three tenants, the counterparty's, each reviewer's, and Cairn's own, and writes back to two. Memory is the substrate three parties coordinate through, not a cache.

**Tiers as a decision, revised over time.** An observation seen once stays in the COLD journal. Seen three times, Cairn promotes it to a WARM entity and journals the promotion. When its supporting evidence ages out, Cairn archives it with a reason. When a new observation contradicts it, the schema-level `UNIQUE (tenant_id, category, name)` constraint means the entity is overwritten rather than duplicated. Both values go to the journal, so the change stays auditable. Where a fact lives is information.

**`forward` as the session baton.** `write_event(evaluated=..., acted=..., forward=...)`: the `forward` list is what the next session must pick up: counterparties due for re-check, claims awaiting corroboration, reviewers whose weight is still provisional. Cairn's first act on boot is to drain it. That is how a fresh process resumes a judgment it started days ago.

---

## The indexed set

The free tier caps `memory.db` at 5,242,880 bytes and the SDK enforces it, so the
indexed set is scoped rather than truncated quietly. Brief part 10 asks for that
decision to be stated, so here it is.

| | |
|---|---|
| Chain | Base mainnet, 8453 |
| Registries | Identity `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`, Reputation `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |
| Block range | 50,763,849 to 50,783,850 (20,002 blocks) |
| Agents seen | 107 |
| Counterparty dossiers | 70 |
| Reviewer dossiers | 14 |
| Observations | 364, being 139 feedback, 139 claims, 86 registrations |
| Registration files | 55 resolved, 24 unavailable |
| Promoted to WARM | 7 patterns at three or more occurrences |
| Database | 3,522,560 bytes, 67.2% of the cap |

Rebuild it with:

```bash
python -m apps.agent.observe.base --blocks 20000 --json
```

The window is the binding constraint, not a preference. At roughly 9.7KB per
observation once the journal is indexed for search, the cap holds around 500
observations, and the scan stops cleanly and reports `stopped_at_cap` rather than
dying or silently dropping rows. The remaining third is left for the verdicts and
promotions phase 3 writes. Widening the window means the paid tier, and that is a
decision to take deliberately rather than by accident.

The indexer is cursor-based and idempotent. Every observation is keyed by a
SHA-256 of the raw log, so rerunning the same range writes nothing:

```
observations_written  0
duplicates_skipped    364
```

### What the window shows

One structural note, stated as a property of the registry rather than of anyone
using it. Of the 139 feedback observations in this window, 100 were written by a
single reviewer about a single agent, and 72% of the tagged feedback carries one
tag. Cairn does not read that as misconduct and does not say so anywhere in the
product. It reads it as the reason a reputation layer that counts feedback
without weighting who produced it cannot mean very much, which is the argument
the reviewer-weighting layer exists to answer.

### On the reputation event's shape

Neither registry implementation is verified on Sourcify, so the feedback event's
ABI is not published anywhere the indexer can fetch. Its layout was derived from
the wire and decoded 549 of 549 live logs cleanly, and the tests pin it against a
log captured from mainnet. Three integers in the event have no published meaning,
so they are carried under `unresolved` rather than being named. Naming one of
them "score" and then judging a real agent on the guess is precisely the failure
brief part 21 is written to prevent.

---

## Partner stacks

| Stack | What it does here | Where |
|---|---|---|
| **Base** | Reads the ERC-8004 Identity + Reputation registries; writes each verdict back as an on-chain attestation | `packages/chain/`, `apps/agent/publish/` |
| **Virtuals ACP** | Cairn is a registered agent with a live offering, taking the neutral Evaluator role on real jobs | `apps/agent/observe/acp.py` |

Neither is decorative. Without Base there is nothing to observe; without ACP there is no evaluator role to occupy.

---

## Quickstart

Requires Python 3.12+, Node 18+, and a Base RPC URL.

```bash
git clone https://github.com/<you>/cairn && cd cairn
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

sibyl init                       # activate Sibyl Memory (free tier is enough)
sibyl status                     # confirm tier and DB size

cp .env.example .env.local       # fill in BASE_RPC_URL and ANTHROPIC_API_KEY
python -m apps.agent.observe.base --bootstrap   # index the counterparty set
python -m apps.agent.api                        # http://localhost:8000

cd apps/web && pnpm install && pnpm dev         # http://localhost:3000
```

Ask about a counterparty:

```bash
curl localhost:8000/v1/lookup/0x...
curl "localhost:8000/v1/lookup/0x...?memory=off"   # the same call, memory bypassed
```

---

## Memory runtime

Cairn's every claim rests on Sibyl Memory behaving as an offline, credential-free
store with isolated tenants. That is checked rather than assumed:

```bash
python scripts/verify_memory.py
```

The probe blocks outbound sockets before it starts, so "works offline" is proven,
not asserted. It exercises all five tiers and tenant isolation against a fresh
database:

```
  tenant id accepts our cp:<chain>:<address> scheme   ok
  HOT   set_state / get_state                         ok
  WARM  set_entity / get_entity                       ok
  COLD  write_event / read_events                     ok
  REFERENCE set_reference / get_reference             ok
  ARCHIVE archive_entity moves the row out            ok
  FTS5 search returns hits                            ok
  tenant isolation holds                              ok

  tier            free
  schema version  4
  free tier       {'tier': 'free', 'db_size_bytes': 282624,
                   'soft_cap_bytes': 5242880, 'pct_used': 0.054}

  MemoryClient.local() works offline with no credentials.  PASS
```

`sibyl health` agrees:

```
  schema_version   4
  db_path          ~/.sibyl-memory/memory.db
  db_size_bytes    282624
  tier             free
  hermes_bound     False
```

Two findings from phase 0 that shape the adapter:

**The free tier caps the database at 5,242,880 bytes.** That is the CLI's own
number, not the docs', and it is what the indexed set is scoped against.

**`archive_entity` moves a row out rather than flagging it.** After archiving,
`list_entities` returns nothing under any status, `get_entity` raises
`NotFoundError`, and `archive` is not a valid search tier, so the `reason` cannot
be read back through the client at all. Archival is therefore journalled as an
event too, or a demotion would leave no auditable trace.

`sibyl status` additionally reports the server-side account tier and requires
`sibyl init`, a one-time browser activation. The local store above needs neither.

---

## Vocabulary

Used consistently in the UI, the API, the errors and the commit log.

- **observation**: one event Cairn watched happen and hashed
- **dossier**: the accumulated record for one counterparty, in its own memory tenant
- **grounding**: tying a claim to an observation Cairn holds
- **verdict**: Cairn's current judgment, carrying a **confidence** and a **basis**
- **prior**: what Cairn believed before the latest observation
- **standing**: `grounded` · `thin` · `suspect` · `dormant`

We never say *reputation score*, *rating*, *review* or *trust score*. Those are the broken things Cairn replaces.

---

## Layout

```
apps/agent/       Python. Cairn core, and the load-bearing code.
  memory/         Sibyl Memory adapter: tenancy, tiers, promotion, decay
  observe/        Base + ACP watchers that produce observations
  judge/          Verdict engine: priors → evidence → verdict + basis
  publish/        Attestation writer
  api/            FastAPI
apps/web/         Next.js 15, landing, explorer, docs
packages/chain/   web3.py, ERC-8004, USDC, x402
scripts/          deletion_test.py and friends
docs/TECH-PRIMER.md   How Cairn works, in plain language
brand/            Marks and design tokens
```

---

## Prior work declaration

Per the hackathon rules, everything that existed before the build window opened on Sep 1 2026:

- **Brand and design system**: name, marks, colour tokens, type choices and the build brief in `docs/BRIEF.md` were produced Aug 21-31 2026, before the window. Committed as `brand/`, `apps/web/src/styles/tokens.css` and `docs/`.
- **Accounts**: the ACP agent, its wallet, and the domain were registered before Sep 1. Configuration, not code.
- **Everything under `apps/` and `scripts/`** was written inside the build window. The commit history is the record.
- **Dependencies** are third-party and credited in `requirements.txt` and `package.json`. No code was carried in from a previous project.

---

## Licence

MIT. See [LICENSE](LICENSE).
