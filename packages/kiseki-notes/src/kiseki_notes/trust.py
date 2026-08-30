"""Where the model is, judged from its own name.

The core makes the same judgement, for the same reason, in
`kiseki.domain.trust` (ADR-0073). This is a second copy on purpose.
Importing the first would make the record contract decorative: the two
sides share a document format and nothing else, which is what lets a
producer be rewritten in another language by somebody who has never
read this code.

A copy that must agree with another copy is a debt, and the debt is
paid the only honest way -- by saying so here, and by the conformance
kit checking both against the same table. It has one now
(`kiseki_conformance.trust`), and on its first run it found two places
where this copy had drifted: an empty host was read as a local name,
and a host the owner named was matched only if the caller had
normalised it.

Nothing here resolves a name. Resolution is a network call, and this
decides whether to make one.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

LOCAL_SUFFIXES = (".local", ".lan", ".internal", ".home.arpa", ".localdomain")


def host_of(endpoint: str) -> str:
    text = endpoint.strip()
    if "//" not in text:
        text = "//" + text
    return (urlsplit(text).hostname or "").lower()


def is_this_machine(host: str) -> bool:
    name = host.strip().lower()
    if name == "localhost":
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def is_your_network(host: str) -> bool:
    name = host.strip().lower()
    if not name:
        # An endpoint with no host is not a local name. It was read as
        # one, because a name with no dots is local and "" has no dots,
        # and the note's text would have gone to it.
        return False
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return "." not in name or any(name.endswith(suffix) for suffix in LOCAL_SUFFIXES)
    return bool(address.is_private or address.is_link_local)


def describe(host: str) -> str:
    if is_this_machine(host):
        return "this machine"
    if is_your_network(host):
        return "a machine on your network"
    return "a machine this producer cannot place"


def admitted(host: str, boundary: str, trusted: tuple[str, ...] = ()) -> bool:
    """Whether a note's text may be sent to this host."""
    # Normalised here rather than trusted to the caller. A host the
    # owner named is a decision, and a decision that depends on who
    # lowercased it is not one.
    if host.strip().lower() in {name.strip().lower() for name in trusted if name.strip()}:
        return True
    if boundary == "anywhere":
        return True
    if boundary == "private_network":
        return is_this_machine(host) or is_your_network(host)
    return is_this_machine(host)
