"""
deletion_test.py, proof that Cairn's memory layer is load-bearing.

The Sibyl Labs Hackathon gate is: remove the memory layer, does the project
still do what it claims? If yes it is a wrapper and it is disqualified.

This script answers that question in public. It runs the full verdict pipeline
twice against the same counterparty, once normally, once with the memory
adapter replaced by a null adapter whose every read returns empty and every
write is a no-op, and prints both results side by side.

It exits non-zero if the memory-off run ever produces a usable verdict, so it
can sit in CI and fail the build the day someone accidentally makes Cairn work
without its memory.

    python scripts/deletion_test.py --agent 0x...

Expected output:

    memory ON      standing=grounded  confidence=0.87  basis=41 observations
    memory OFF     standing=thin      confidence=-     basis=0  observations
                   ↳ verdict engine returned NO_BASIS

    Cairn's core function is unavailable without the memory layer.  PASS

------------------------------------------------------------------------------
STATUS: contract only. Implement in phase 3, after judge/verdict.py exists.
------------------------------------------------------------------------------

Implementation notes for phase 3:

  * The swap must happen at the adapter boundary, not inside the verdict
    engine. `apps/agent/memory/store.py` is the ONLY module that imports
    sibyl_memory_client, which is what makes this a two-line change:
    instantiate NullStore instead of MemoryStore and hand it to the same
    verdict call.

  * NullStore must implement the full MemoryStore interface. Every read
    returns an empty result, every write is a no-op that returns a fake id.
    It must not raise, we are testing absence of memory, not absence of a
    module.

  * Do not special-case the verdict engine for the null path. If the engine
    needs an `if store is None` branch to survive, the boundary is wrong.

  * The memory-off run is "usable", and therefore a FAIL, if it returns
    any standing other than `thin`/`NO_BASIS`, or any non-null confidence,
    or a non-empty basis.

  * Print the counterparty and a UTC timestamp in the header so a frame from
    the demo video can be matched to a run.
"""

from __future__ import annotations

import argparse
import sys

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_NOT_IMPLEMENTED = 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prove Cairn's core function requires the memory layer."
    )
    parser.add_argument("--agent", required=True, help="counterparty address or agent id")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    print(
        f"deletion_test: not implemented yet, asked about {args.agent}.\n"
        "Implement in phase 3 against apps/agent/judge/verdict.py.\n"
        "See the module docstring for the contract.",
        file=sys.stderr,
    )
    return EXIT_NOT_IMPLEMENTED


if __name__ == "__main__":
    raise SystemExit(main())
