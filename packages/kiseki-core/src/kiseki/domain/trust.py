"""Where a model is, and whether it is allowed to be there.

Captioning sends a photograph. Not a description of one, not a
reference to one: the reduced copy itself, base64 in an HTTP body. The
library has always sent it to `localhost`, and `kiseki privacy` has
always said nothing leaves the machine, and both were true together.

The moment a model may live on another machine -- the realistic
deployment is one GPU box a household or a team shares -- those two
stop being the same statement. So the endpoint gets a boundary, and
the boundary is checked before a photograph is sent rather than after.

Three boundaries, and the default is the strictest:

    same_host        only this machine
    private_network  and a machine on the local network
    anywhere         and anything the owner names

A host named in `trusted_hosts` is admitted under all of them, because
an owner naming a host is making a decision, and a decision is what
this is for. Widening the boundary is a shrug; naming a host is a
sentence somebody wrote.

Nothing here resolves a name. Resolution is a network call, and a
module whose job is to decide whether to make a network call must not
make one to decide. A name that cannot be judged from its own shape is
UNKNOWN, and unknown is refused: a wrong refusal costs a configuration
line, and a wrong admission costs the photographs. See ADR-0073.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, unique
from urllib.parse import urlsplit

LOCAL_SUFFIXES = (".local", ".lan", ".internal", ".home.arpa", ".localdomain")
"""Names that only exist inside a network. A single-label name --
`llm01` with no dots at all -- is local for the same reason."""


@unique
class Locality(Enum):
    """Where a host is, as far as its own name can say."""

    LOOPBACK = "this machine"
    PRIVATE = "a machine on your network"
    PUBLIC = "a machine on the internet"
    UNKNOWN = "a machine this library cannot place"


@unique
class TrustBoundary(Enum):
    """How far the owner allows a model to be."""

    SAME_HOST = "same_host"
    PRIVATE_NETWORK = "private_network"
    ANYWHERE = "anywhere"


ALLOWED: dict[TrustBoundary, frozenset[Locality]] = {
    TrustBoundary.SAME_HOST: frozenset({Locality.LOOPBACK}),
    TrustBoundary.PRIVATE_NETWORK: frozenset({Locality.LOOPBACK, Locality.PRIVATE}),
    TrustBoundary.ANYWHERE: frozenset(
        {Locality.LOOPBACK, Locality.PRIVATE, Locality.PUBLIC, Locality.UNKNOWN}
    ),
}


def host_of(endpoint: str) -> str:
    """The bare host in an endpoint, however it was written."""
    text = endpoint.strip()
    if "//" not in text:
        text = "//" + text
    return (urlsplit(text).hostname or "").lower()


def locality_of(host: str) -> Locality:
    """Where a host is, judged from its own shape and nothing else."""
    name = host.strip().lower()
    if not name:
        return Locality.UNKNOWN
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        pass
    else:
        if address.is_loopback:
            return Locality.LOOPBACK
        if address.is_private or address.is_link_local:
            return Locality.PRIVATE
        return Locality.PUBLIC
    if name == "localhost":
        return Locality.LOOPBACK
    if "." not in name:
        return Locality.PRIVATE
    if any(name.endswith(suffix) for suffix in LOCAL_SUFFIXES):
        return Locality.PRIVATE
    return Locality.UNKNOWN


@dataclass(frozen=True)
class Verdict:
    """Whether the model may be spoken to, and why."""

    host: str
    locality: Locality
    boundary: TrustBoundary
    trusted: bool

    @property
    def admitted(self) -> bool:
        return self.trusted or self.locality in ALLOWED[self.boundary]

    @property
    def reason(self) -> str:
        """What to tell the owner, in either direction."""
        if self.trusted:
            return f"{self.host} is one of the hosts you named"
        if self.admitted:
            return f"{self.host} is {self.locality.value}"
        if self.locality is Locality.UNKNOWN:
            return (
                f"'{self.host}' cannot be placed from its name alone, and this"
                " library will not resolve it to find out. Name it in"
                " trusted_hosts if it is yours"
            )
        return (
            f"'{self.host}' is {self.locality.value}, which is outside the"
            f" {self.boundary.value} boundary. A photograph would be sent there"
        )


def judge(
    endpoint: str,
    boundary: TrustBoundary = TrustBoundary.SAME_HOST,
    trusted_hosts: Sequence[str] = (),
) -> Verdict:
    """Decide about an endpoint before anything is sent to it."""
    host = host_of(endpoint)
    trusted = host in {name.strip().lower() for name in trusted_hosts if name.strip()}
    return Verdict(
        host=host,
        locality=locality_of(host),
        boundary=boundary,
        trusted=trusted,
    )
