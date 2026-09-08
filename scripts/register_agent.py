"""Register Firsthand on the ERC-8004 Identity Registry, on Base.

One on-chain write, spending real ETH, so it is a deliberate command rather than
a side effect of asking a question.

    python scripts/register_agent.py --dry-run
    python scripts/register_agent.py --send

Needs FIRSTHAND_ATTESTOR_KEY in the environment: the same key that deployed the
attestation contract. It is read, never printed, never written anywhere.

The registered URI points at the agent card this repo serves at
`/.well-known/agent-card.json`, whose shape follows the registrations already in
the indexed set rather than one invented here.

The assigned agent id is recorded in Firsthand's own dossier, so the claim that
it is registered is checkable against something it holds.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.agent.env import load as load_env
from apps.agent.memory.store import MemoryStore
from apps.agent.publish.register import (
    IDENTITY_IMPLEMENTATION,
    IDENTITY_REGISTRY,
    RegistrationError,
    RegistrationRecordError,
    encode,
    registrar_from_env,
)

# Secrets live in .env.local; the scripts read os.environ. Bridge the two
# before anything asks for a key.
load_env()

DEFAULT_URI = "https://firsthand-iota.vercel.app/.well-known/agent-card.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uri", default=DEFAULT_URI, help="the agent card to register")
    parser.add_argument("--db", default=os.environ.get("SIBYL_DB") or "data/memory.db")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="encode and print the call without sending anything",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="actually send it. Spends real ETH on Base",
    )
    args = parser.parse_args(argv)

    try:
        call = encode(args.uri)
    except RegistrationError as exc:
        print(f"  refused: {exc}")
        return 1

    if args.dry_run or not args.send:
        print("  would register, nothing sent:")
        for key, value in call.as_payload().items():
            print(f"    {key:16} {value}")
        print(f"    {'abi from':16} {IDENTITY_IMPLEMENTATION} (verified implementation)")
        if not args.send:
            print()
            print("  add --send to sign and broadcast this.")
        return 0

    try:
        registrar = registrar_from_env()
    except RegistrationError as exc:
        print(f"  {exc}")
        return 1

    print(f"  registrar      {registrar.address}")
    print(f"  registry       {IDENTITY_REGISTRY}")
    print(f"  agent uri      {call.agent_uri}")

    store = MemoryStore.open(args.db)
    try:
        tx_hash, agent_id = registrar.register(call, store=store)
    except RegistrationRecordError as exc:
        # Caught before RegistrationError, which it subclasses. This one already
        # spent the money: print the hash exactly as the success path does, or
        # the only copy of it leaves with the traceback.
        print(f"  registered     https://basescan.org/tx/0x{exc.tx_hash.removeprefix('0x')}")
        print(f"  not recorded   {exc}")
        print("  the registration is on chain. Only the dossier is behind.")
        return 1
    except RegistrationError as exc:
        print(f"  refused: {exc}")
        return 1
    finally:
        store.close()

    print(f"  agent id       {agent_id}")
    print(f"  registered     https://basescan.org/tx/0x{tx_hash.removeprefix('0x')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
