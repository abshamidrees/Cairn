"""Deploy the attestation contract, and publish one verdict on Base.

Two on-chain writes, both spending real ETH, so they are deliberate commands
rather than a side effect of asking a question.

    python scripts/publish_attestation.py --deploy
    python scripts/publish_attestation.py --agent 0x... --contract 0x...

Needs CAIRN_ATTESTOR_KEY in the environment: a key that holds a few dollars of
ETH on Base and nothing else. It is read, never printed, never written anywhere.

The published transaction hash is recorded in the counterparty's own dossier, so
the explorer shows what Cairn said about an agent next to the observations it
said it from.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.agent.judge.verdict import evaluate
from apps.agent.memory.store import MemoryStore
from apps.agent.publish.attest import AttestationError, attestor_from_env, encode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deploy", action="store_true", help="deploy the attestation contract")
    parser.add_argument("--agent", help="counterparty to publish a verdict about")
    parser.add_argument("--contract", help="attestation contract address")
    parser.add_argument("--db", default=os.environ.get("SIBYL_DB") or "data/memory.db")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="encode and print the call without sending anything",
    )
    args = parser.parse_args(argv)

    if args.dry_run:
        if not args.agent:
            parser.error("--dry-run needs --agent")
        store = MemoryStore.open(args.db)
        try:
            verdict = evaluate(store, "base", args.agent, write=False)
            call = encode(verdict)
        finally:
            store.close()
        print("  would publish, nothing sent:")
        for key, value in call.as_payload().items():
            print(f"    {key:16} {value}")
        return 0

    if args.contract:
        os.environ["CAIRN_ATTESTATION_CONTRACT"] = args.contract

    try:
        attestor = attestor_from_env()
    except AttestationError as exc:
        print(f"  {exc}")
        return 1

    print(f"  attestor       {attestor.address}")

    if args.deploy:
        tx_hash, address = attestor.deploy()
        print(f"  deployed       {address}")
        print(f"  transaction    https://basescan.org/tx/0x{tx_hash.removeprefix('0x')}")
        print("  Put that address in CAIRN_ATTESTATION_CONTRACT.")
        return 0

    if not args.agent:
        parser.error("give --agent, or --deploy")

    store = MemoryStore.open(args.db)
    try:
        verdict = evaluate(store, "base", args.agent, write=False)
        print(f"  verdict        {verdict.standing} confidence={verdict.confidence}")
        print(f"  basis          {len(verdict.basis)} observations")
        tx_hash = attestor.publish(verdict, store=store)
    except AttestationError as exc:
        print(f"  refused: {exc}")
        return 1
    finally:
        store.close()

    print(f"  published      https://basescan.org/tx/0x{tx_hash.removeprefix('0x')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
