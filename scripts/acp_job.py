"""Run one ACP job with Cairn as provider and Evaluator.

Everything here drives `@virtuals-protocol/acp-cli` by subprocess with --json.

    python scripts/acp_job.py status
    python scripts/acp_job.py fulfil   --job-id <id> --agent 0x...
    python scripts/acp_job.py evaluate --job-id <id>

`fulfil` builds the dossier from the record and submits it as the deliverable.
`evaluate` reads the deliverable back off the job and decides, using the same
rule the rest of the product uses: a deliverable is accepted when it names the
observations it rests on, and refused with a reason when it does not.

Funding is not here on purpose. Moving USDC is the buyer's action, and this
script prints the command rather than running it for you.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.agent.memory.store import MemoryStore
from apps.agent.observe.acp import (
    CHAIN_ID,
    OFFERING,
    Acp,
    AcpError,
    build_deliverable,
    evaluate_deliverable,
)


def _deliverable_of(history: dict[str, Any]) -> object:
    """Pull the submitted deliverable out of a job's history."""
    for key in ("deliverable", "memo", "result"):
        found = history.get(key)
        if found is None:
            continue
        if isinstance(found, str):
            try:
                return json.loads(found)
            except json.JSONDecodeError:
                return found
        return found
    return None


def _print_create_hint(provider: str) -> None:
    """The buyer's side of the lifecycle, which is not ours to run."""
    print("    none yet. A buyer creates one with:")
    print(f"      acp client create-job --provider {provider}")
    print(f'        --offering-name "{OFFERING}"')
    print('        --requirements \'{"address":"0x..."}\'')
    print(f"      acp client fund --job-id <id> --amount 0.01 --chain-id {CHAIN_ID} --json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "fulfil", "evaluate"))
    parser.add_argument("--job-id")
    parser.add_argument("--agent", help="counterparty the dossier is about")
    parser.add_argument("--db", default=os.environ.get("SIBYL_DB") or "data/memory.db")
    args = parser.parse_args(argv)

    acp = Acp()

    try:
        if args.action == "status":
            who = acp.whoami()
            print(f"  agent      {who.get('name')} {who.get('walletAddress', '')}")
            for offering in acp.offerings():
                print(f"  offering   {offering.get('name')} at {offering.get('priceValue')} USDC")
            jobs = acp.jobs()
            print(f"  jobs       {len(jobs)} active on chain {CHAIN_ID}")
            for job in jobs[:5]:
                print(f"    {job.get('id')}  {job.get('status')}")
            if not jobs:
                _print_create_hint(str(who.get("walletAddress", "<cairn>")))
            return 0

        if args.action == "fulfil":
            if not (args.job_id and args.agent):
                parser.error("fulfil needs --job-id and --agent")
            store = MemoryStore.open(args.db)
            try:
                deliverable = build_deliverable(store, args.agent)
            finally:
                store.close()
            print(f"  standing   {deliverable.standing}")
            print(f"  basis      {len(deliverable.basis)} observations")
            acp.submit(args.job_id, deliverable)
            print(f"  submitted  job {args.job_id}")
            return 0

        if not args.job_id:
            parser.error("evaluate needs --job-id")
        history = acp.history(args.job_id)
        decision = evaluate_deliverable(_deliverable_of(history))
        print(f"  decision   {'accept' if decision.accept else 'reject'}")
        print(f"  reason     {decision.reason}")
        if decision.accept:
            acp.complete(args.job_id, decision.reason)
        else:
            acp.reject(args.job_id, decision.reason)
    except AcpError as exc:
        print(f"  {exc}")
        return 1
    else:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
