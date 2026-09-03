# Cairn

**Cairn is a memory-native trust layer for agent commerce.** When one agent is about to pay
another, it answers the only question that matters, *has this counterparty done what it said it
would before?*, and shows the observations the answer came from. Every verdict is arithmetic over
a record Cairn witnessed itself, never a rating somebody self-reported.

[Run it locally](#run-it-locally) · [Methodology](#the-methodology-is-generated-from-the-engine) · [Where memory is load-bearing](#where-memory-is-load-bearing) · [What is real and what is not](#what-is-real-and-what-is-not)

> Submission for the Sibyl Labs Memory Hackathon, Sep 1-10 2026. There is no hosted deployment and
> no demo video yet; both are day 10. Everything below runs from a clean clone today.

---

## Live deployments

| What | Where |
|---|---|
| ACP agent | `Cairn`, wallet [`0x484eeb2aa5e97c374375018b08581d62c7769e0a`](https://basescan.org/address/0x484eeb2aa5e97c374375018b08581d62c7769e0a) on Base 8453, agent id `01a06098-ef45-7e55-8ad6-21970291edb3` |
| ACP offering | `Counterparty dossier`, `01a060b1-cb39-77b7-8024-f511e2c31b1e`, 0.01 USDC, 10 minute SLA, visible |
| Identity registry read | [`0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`](https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432) |
| Reputation registry read | [`0x8004BAa17C55a88189AE136b182e5fdA19dE9b63`](https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63) |
| Indexed set | Base 8453, blocks 50,763,849 to 50,783,850 (20,002 blocks), 107 agents |
| Attestation contract | Not deployed. Compiles and encodes; the deploy is one command and real ETH, see [what is real](#what-is-real-and-what-is-not) |
| Public lookup API | Runs locally on port 8000. Free, no auth, no wallet connection to read |

The lookup endpoint takes no key and returns the basis with the verdict:

```bash
curl -s localhost:8000/v1/lookup/0x01f90369170c917a2c0e9d26d54c6a3a400984d3 | jq
curl -s "localhost:8000/v1/lookup/0x01f90369170c917a2c0e9d26d54c6a3a400984d3?memory=off" | jq
```

The second call is the same endpoint with the memory layer genuinely removed, server side. Compare
the two.

---

## Where memory is load-bearing

> **Judges: this is the two-minute answer.** Every row is a real file and line.

| What | Where |
|---|---|
| The only module that imports the SDK | [`apps/agent/memory/store.py`](apps/agent/memory/store.py) |
| That rule, enforced by parsing imports rather than trusting it | [`tests/test_boundary.py:51`](tests/test_boundary.py#L51) |
| Tenancy, one isolated dossier per counterparty and per claimant | [`store.py:227`](apps/agent/memory/store.py#L227) `use()` |
| Writes, every observation lands in the COLD journal | [`store.py:238`](apps/agent/memory/store.py#L238) `record_observation()` |
| Promotion to a WARM entity at three occurrences | [`store.py:281`](apps/agent/memory/store.py#L281) `_promote_if_due()` |
| Demotion, archived with a reason once evidence ages out | [`store.py:469`](apps/agent/memory/store.py#L469) `archive_stale()` |
| Contradiction, overwrites the entity and journals both values | [`store.py:430`](apps/agent/memory/store.py#L430) `assert_fact()` |
| `forward` as the session baton, drained on boot | [`store.py:551`](apps/agent/memory/store.py#L551) `drain_forward()` |
| Reads, the verdict pulls prior and evidence back out | [`judge/verdict.py:446`](apps/agent/judge/verdict.py#L446) `evaluate()` |
| Reviewer weighting, the layer ERC-8004 says is missing | [`verdict.py:225`](apps/agent/judge/verdict.py#L225) `reviewer_weight()` |
| Cairn with its memory removed | [`store.py:577`](apps/agent/memory/store.py#L577) `NullStore` |
| Proof it is load-bearing | [`scripts/deletion_test.py`](scripts/deletion_test.py) |

### The deletion test

The hackathon's gate is: remove the memory layer, does it still do what it claims? Cairn ships the
tool that answers it.

```bash
python scripts/deletion_test.py --agent 0x01f90369170c917a2c0e9d26d54c6a3a400984d3 --db data/memory.db
```

Real output against the indexed set:

```
  memory ON      standing=grounded  confidence=0.84  basis=3  observations
  memory OFF     standing=thin      confidence=-     basis=0  observations
                 ↳ verdict engine returned NO_BASIS

  Cairn's core function is unavailable without the memory layer.  PASS
```

It exits non-zero if the memory-off run ever produces a usable verdict. The swap is one line at the
call site, because `evaluate()` takes a `Store` and cannot tell the two apart.

---

## What is real and what is not

Volunteering the limits is what makes the rest credible.

| Capability | How it is backed |
|---|---|
| Five-tier promotion, demotion and archival | **Real.** [`store.py`](apps/agent/memory/store.py), 21 tests, exercised over the live indexed set. Mutation-checked: removing the promotion journal, the tenant switch or the archival record each fails the test that guards it |
| Tenant isolation | **Real.** Two dossiers cannot see each other's rows, asserted directly |
| Deterministic verdict, no model in the decision path | **Real.** [`verdict.py`](apps/agent/judge/verdict.py), 27 tests. No LLM is called anywhere in this repo; [`tests/test_boundary.py`](tests/test_boundary.py) parses the judge package to keep it that way |
| Base registry reads | **Real.** 20,002 blocks, 364 observations, 107 agents. The feedback event ABI is unpublished and was derived from the wire, decoding 549 of 549 live logs |
| Reviewer weighting | **Real over the indexed set.** 13 of 14 claimants are below the corroboration threshold, so their weights are provisional and the API returns them flagged |
| ACP agent and offering | **Real and live.** Registered on Base 8453 with a visible offering. **No job has been run**: that needs USDC in the agent wallet |
| ACP Evaluator role | **Code complete and tested, never exercised.** [`observe/acp.py`](apps/agent/observe/acp.py), 13 tests against a fake CLI runner |
| Base attestation write | **Not landed.** The contract compiles, the call encodes, and `--dry-run` prints exactly what would be sent. Deploying spends real ETH and has not been done |
| Indexed coverage | **Scoped, not truncated.** 20,002 blocks, not the full ERC-8004 set, because the free tier caps the database at 5,242,880 bytes. Stated here rather than hidden |
| `suspect` standing | **Unreachable on current data, by design.** No agent in the indexed set has two conflicting owner records. Part 21 forbids accusing without a contradiction we can name, so the honest count is zero |
| Hosted deployment, demo video, CI | **None yet.** No badge is shown for a check that does not exist |

---

## The public scan

An aggregate finding about how the ERC-8004 reputation layer is used, computed from what Cairn
witnessed and checkable against the same chain data. It runs at `/scan`, with the raw numbers at
`/scan.json`, and regenerates with:

```bash
python scripts/scan.py --db data/memory.db --out apps/web/public/scan.json
```

**16 of 22 subjects carrying feedback have exactly one party speaking about them.** Of the rest,
five have two and one has three. The largest single claimant spoke 100 times.

A layer that counts feedback cannot tell that apart from several parties agreeing. That is the
claim, and it is about the registry's design. No agent is named, ranked or accused anywhere in the
scan: one party speaking repeatedly is not proof of bad conduct, and the record cannot support that.

There is no waitlist and there are no design partners. Both would be inventions today, and an
invented one is worth less than none.

## Documentation

`/docs`, eighteen pages: what Cairn is, quickstart, the concepts, the memory architecture, the API
read out of `apps/agent/api` rather than imagined, and the two partner stacks. The webhooks page
exists to say there are none, because omitting it would imply one.

## What the indexed set actually shows

Cairn read 20,002 blocks of the ERC-8004 registries on Base and judged every counterparty it found.

| | |
|---|---|
| Counterparty dossiers | 70 |
| Claimant dossiers | 14 |
| Observations | 364 (139 feedback, 139 claims, 86 registrations) |
| Registration files | 55 resolved, 24 unavailable |
| Rows by tier | COLD 564, WARM 7, HOT 11, REFERENCE 2, ARCHIVE 0 |
| Standings | grounded 1, thin 69, suspect 0, dormant 0 |

**One counterparty in seventy has enough independent corroboration to be grounded.** The busiest
dossier in the set holds 100 pieces of feedback from a single claimant, all about the same agent,
all tagged the same way. Cairn reads it as `thin`, because a hundred repetitions by one party is
not corroboration.

This is a finding about the registry's design, not a list of bad actors. Cairn cannot support the
claim that any individual agent behaved badly, and does not make it. What it can support is that a
reputation layer where one party can speak a hundred times and move a score is one where the score
does not mean what a reader assumes.

---

## How memory made this possible

Cairn is not a product that uses memory. It is a product made of memory.

The thing being sold is an accumulated, grounded record of what agents have actually done. Strip the
record and there is no product, not a degraded one. A stateless model asked "should I pay `0x...`?"
can only guess, because the answer lives entirely in what was observed before this moment.

**Tenancy is the coordination pattern.** `set_tenant()` gives every counterparty and every claimant
a fully isolated dossier inside one database file. A single verdict reads three tenants, the
counterparty's, each claimant's, and Cairn's own, and writes back to two. Memory is the substrate
three parties coordinate through, not a cache in front of something else.

**The tier is a decision, revised over time.** An observation seen once stays in the COLD journal.
Seen three times inside the window, Cairn promotes it to a WARM entity and journals the promotion
itself, so the migration is part of the record. When the evidence ages out the entity is archived
with a reason. Where a fact lives is information.

**`forward` is the session baton.** `write_event(evaluated=..., acted=..., forward=...)` carries what
the next session must pick up. Cairn's first act on boot is to drain it. Handing the same work
forward on every sweep would grow an append-only journal without bound, so the baton carries news:
an unchanged verdict hands nothing.

**The free tier taught us where to reclaim space.** At 5,242,880 bytes the cap is real and fires.
When space has to come back it comes out of HOT, which is arithmetic over the journal and can be
recomputed exactly, never out of COLD, which is the record. That distinction is the whole product in
one operational decision.

---

## Partner stacks

| Stack | What it does here | Where |
|---|---|---|
| **Base** | Reads the ERC-8004 Identity and Reputation registries on 8453; publishes a verdict as an attestation | [`observe/base.py`](apps/agent/observe/base.py), [`publish/attest.py`](apps/agent/publish/attest.py), [`CairnAttestations.sol`](packages/chain/contracts/CairnAttestations.sol) |
| **Virtuals ACP** | Registered agent with a live offering, taking the neutral Evaluator role, driven by subprocess with `--json` | [`observe/acp.py`](apps/agent/observe/acp.py) |

Neither is decorative. Without Base there is nothing to observe; without ACP there is no evaluator
role to occupy.

---

## Engineering decisions, and the problems behind them

**Confidence counted volume, and volume was purchasable.** The first formula followed the spec
literally and scored the busiest dossier at 0.65. Almost all of it came from raw observation count,
the one quantity on this chain that costs a median of $0.0027 to manufacture. The formula was paying
for exactly the behaviour Cairn exists to catch. Volume now counts distinct sources, saturating at
five, and the same dossier scores 0.33. Any term in a trust score has to be priced by what it costs
an adversary to fake, not by how easy it is to count.

**A test passed under the bug it was written to catch.** The test guarding that Sybil hole compared
a fake dossier against an honest one and asserted the honest one scored higher. It passed, and it
also passed when the hole was deliberately reopened, because the honest case won on a different term
regardless. Mutation testing caught it. The replacement holds sources fixed at one and asserts that
adding observations changes nothing. A comparison test can pass for a reason unrelated to the thing
it claims to check.

**A read that writes is a read that fails.** The lookup endpoints briefly recorded their verdict, on
the reasoning that a lookup is what makes one live. With the database at its cap that turned a full
disk into a 500 on every dossier request. Reads are read-only now, and verdicts persist only where a
cap error can be handled.

**The reputation registry's write path was rejected rather than guessed.** Its implementation is
unverified and the selector observed on the wire, `0x3c036a7e`, matched none of several thousand
signatures reconstructed from the calldata shape. Calling an unverified contract with a guessed
signature, spending real ETH, to publish a judgment about a named third party, is the one mistake
that would outlive this hackathon. The verdict goes into a contract small enough to read in a minute
instead.

**Three observation kinds, not the four the plan assumed.** The design called for ACP jobs, escrow
rejections and x402 settlements alongside registry events. The indexer reads the registries, so
those are what exist, and the site says three rather than showing four with one invented.

---

## The methodology is generated from the engine

The promotion threshold, decay window, confidence weights and standing rules are constants in the
code. [`apps/agent/judge/methodology.py`](apps/agent/judge/methodology.py) imports them from the
module that uses them and exports them as the published methodology, so the documentation cannot
drift from the engine that decides.

```
standing    grounded  3 or more corroborated observations, nothing contradicting itself
            suspect   the record contradicts itself, and the observations can be named
            thin      fewer than 3 corroborated observations
            dormant   nothing witnessed for 90 days

confidence  clamp(0.40 * min(distinct_sources / 5, 1)
                + 0.35 * (corroborated / n)
                + 0.25 * max(0, 1 - age_days / 90)
                - 0.25 * contradictions)
```

`confidence: null` means there was no record. A confidence of `0.0` means Cairn looked and found the
record worthless. The two never render the same.

---

## Project layout

```
apps/agent/       Python. Cairn core, and the load-bearing code.
  memory/store.py   The only module that imports sibyl_memory_client
  observe/base.py   ERC-8004 registry reads on Base
  observe/acp.py    Virtuals ACP, provider and Evaluator
  judge/verdict.py  The verdict engine, arithmetic over the record
  publish/attest.py Attestation encoding and publishing
  api/main.py       FastAPI, read-only, with ?memory=off
apps/web/         Next.js 15. Landing page and explorer
packages/chain/   CairnAttestations.sol
scripts/          deletion_test, summarise, acp_job, publish_attestation
tests/            113 tests
```

## Run it locally

Requires Python 3.12+, Node 18+, and a Base RPC URL.

```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt

python scripts/verify_memory.py                    # proves the store works offline
python -m apps.agent.observe.base --bootstrap      # index the counterparty set
python scripts/summarise.py --db data/memory.db    # judge it, and record what is held
python -m uvicorn apps.agent.api.main:app --port 8000

cd apps/web && npm install && npm run dev          # http://localhost:3000
```

`scripts/verify_memory.py` blocks outbound sockets before it starts, so "works offline with no
credentials" is proven rather than asserted.

## Tests

```bash
python -m pytest        # 113 tests
ruff check .
mypy
```

| Area | Tests |
|---|---|
| Memory adapter and tiers | 21 |
| Verdict engine and standings | 27 |
| Read API and the memory bypass | 17 |
| Base indexer | 14 |
| ACP driver and Evaluator | 13 |
| Attestation encoding | 13 |
| Deletion test gate | 5 |
| Adapter and model-client boundaries | 3 |

---

## Vocabulary

- **observation**: one event Cairn watched happen and hashed
- **dossier**: the accumulated record for one counterparty, in its own memory tenant
- **grounding**: tying a claim to an observation Cairn holds
- **verdict**: Cairn's current judgment, carrying a **confidence** and a **basis**
- **prior**: what Cairn believed before the latest observation
- **standing**: `grounded` · `thin` · `suspect` · `dormant`

We never say *reputation score*, *rating*, *review* or *trust score*. Those are the broken things
Cairn replaces.

## Fair judgment

Cairn publishes judgments about real, named third parties. Four rules are enforced in code, not
policy. Absence is never evidence: a source that was not ingested makes its checks skip rather than
count against anyone. `suspect` requires a contradiction the engine can name, and reaching it with
an empty basis raises rather than downgrading quietly. The language stays neutral everywhere, in the
UI, the API and the attestation payload. And an adversarial suite feeds the engine malformed bodies,
empty responses and prose where an identifier belongs, asserting that none of it ever produces
`suspect`.

Any agent can request removal from the indexed set, and it is honoured.

## Prior work declaration

Per the hackathon rules, everything that existed before the build window opened on Sep 1 2026:

- **Brand and design system**: the name, marks, colour tokens, type choices and the build brief were
  produced Aug 21-31 2026, before the window. The marks and tokens are committed under `brand/` and
  `apps/web/src/styles/tokens.css`. The brief itself is not published.
- **Accounts**: the ACP agent, its wallet and the domain were registered before the window as
  configuration, not code.
- **Everything under `apps/`, `packages/`, `scripts/` and `tests/`** was written inside the window.
  The commit history is the record.
- **Dependencies** are third-party and credited in `requirements.txt` and `package.json`.

## Licence

MIT. See [LICENSE](LICENSE).
