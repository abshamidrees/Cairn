# apps/agent

Python. Cairn's core, and the load-bearing code for the hackathon's memory
criterion. Runs as one process on one machine with a real disk, because
Sibyl Memory is a local SQLite file that never leaves the box.

| Package | Responsibility |
|---|---|
| `memory/` | The only place `sibyl_memory_client` is imported. Tenancy, the five-tier policy, promotion, decay, archival, the `forward` baton |
| `observe/` | Watchers that turn real events on Base and ACP into observations |
| `judge/` | The verdict engine. Deterministic arithmetic over the record, never an LLM call in the decision path |
| `publish/` | Writes verdicts back to Base as attestations |
| `api/` | FastAPI. Serves the web app, and implements the real `?memory=off` bypass |

The import boundary at `memory/store.py` is not a style preference. It is what
makes `scripts/deletion_test.py` a two-line swap, and it is the first thing a
judge will check.
