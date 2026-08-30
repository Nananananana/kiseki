"""One table of cases, and every implementation of the trust boundary.

ADR-0073 put a boundary between the library and the model: the text of
a note, or a reduced copy of a photograph, may be sent to this machine,
or to the local network, or anywhere, and the default is the strictest.

The rule is implemented more than once **on purpose**. A producer that
imported the core's version would be a producer that could not be
rewritten in Swift by somebody who has never read this code, and the
record contract -- which is all the two sides are supposed to share --
would become decorative. `kiseki_notes/trust.py` says so at the top,
and names the debt that comes with it:

    A copy that must agree with another copy is a debt, and the debt
    is paid the only honest way -- by saying so here, and by the
    conformance kit checking both against the same table when it grows
    one.

This is the table.

**It checks the decision, not the words.** The core answers with a
`Locality` and a `Verdict` carrying a reason; a producer answers with
three predicates and a sentence. Two implementations that refuse the
same host for reasons phrased differently both conform, and that
difference is the whole reason there is more than one of them.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import pytest

SAME_HOST = "same_host"
PRIVATE_NETWORK = "private_network"
ANYWHERE = "anywhere"


@dataclass(frozen=True)
class Case:
    """One endpoint, one boundary, and whether the text may be sent."""

    endpoint: str
    boundary: str
    admitted: bool
    why: str
    trusted: tuple[str, ...] = field(default=())

    @property
    def label(self) -> str:
        named = " +named" if self.trusted else ""
        return f"{self.endpoint or '<empty>'}@{self.boundary}{named}"


CASES: tuple[Case, ...] = (
    # This machine, however it is written.
    Case("http://localhost:11434", SAME_HOST, True, "localhost is this machine"),
    Case("localhost", SAME_HOST, True, "a bare name is still a name"),
    Case("http://127.0.0.1:11434", SAME_HOST, True, "the loopback address"),
    Case("127.0.0.1", SAME_HOST, True, "with no scheme and no port"),
    Case("http://[::1]:11434", SAME_HOST, True, "loopback in six groups"),
    # The strictest boundary admits nothing else.
    Case("192.168.1.10", SAME_HOST, False, "a machine on the network is not this one"),
    Case("llm01", SAME_HOST, False, "a single-label name is not this machine"),
    Case("gpu.local", SAME_HOST, False, "nor is a name that only exists on it"),
    Case("8.8.8.8", SAME_HOST, False, "and certainly not the internet"),
    Case("api.example.com", SAME_HOST, False, "or a name on it"),
    Case("", SAME_HOST, False, "an endpoint with no host at all"),
    # The network boundary admits the network, and only by shape.
    Case("127.0.0.1", PRIVATE_NETWORK, True, "the stricter case still passes"),
    Case("192.168.1.10", PRIVATE_NETWORK, True, "a private range"),
    Case("10.0.0.5", PRIVATE_NETWORK, True, "another private range"),
    Case("172.16.0.1", PRIVATE_NETWORK, True, "and the third"),
    Case("169.254.10.1", PRIVATE_NETWORK, True, "link-local is not the internet"),
    Case("llm01", PRIVATE_NETWORK, True, "a single-label name is a local name"),
    Case("gpu.local", PRIVATE_NETWORK, True, "mDNS"),
    Case("box.lan", PRIVATE_NETWORK, True, "a router's idea of a domain"),
    Case("host.internal", PRIVATE_NETWORK, True, "and a container's"),
    Case("thing.home.arpa", PRIVATE_NETWORK, True, "the name reserved for exactly this"),
    Case("nas.localdomain", PRIVATE_NETWORK, True, "an old default"),
    Case("8.8.8.8", PRIVATE_NETWORK, False, "a public address is refused"),
    Case("llm01.example.com", PRIVATE_NETWORK, False, "a name that cannot be placed is refused"),
    Case("api.openai.example", PRIVATE_NETWORK, False, "refusing costs a line of configuration"),
    Case("", PRIVATE_NETWORK, False, "and admitting costs the notes"),
    # Anywhere means anywhere, which is why it is not the default.
    Case("8.8.8.8", ANYWHERE, True, "the owner said anywhere"),
    Case("api.example.com", ANYWHERE, True, "including what cannot be placed"),
    # A host the owner named is a decision, and outranks the boundary.
    Case(
        "https://api.example.com",
        SAME_HOST,
        True,
        "naming a host is a sentence somebody wrote; widening a boundary is a shrug",
        trusted=("api.example.com",),
    ),
    Case(
        "https://GPU-BOX.example.com:11434",
        SAME_HOST,
        True,
        "and the naming is not case-sensitive, nor is it whitespace-sensitive",
        trusted=("  gpu-box.example.com ",),
    ),
    Case(
        "https://other.example.com",
        SAME_HOST,
        False,
        "a host that was not the one named is not named",
        trusted=("api.example.com",),
    ),
)

Admits = Callable[[str, str, Sequence[str]], bool]
"""Whether the text may be sent: endpoint, boundary, hosts the owner named."""


class TrustBoundaryConformance:
    """Checks every implementation of ADR-0073's boundary must pass.

    Supply one callable and the table does the rest:

        class TestMyProducer(TrustBoundaryConformance):
            @pytest.fixture
            def admits(self):
                return lambda endpoint, boundary, trusted: my.admitted(
                    my.host_of(endpoint), boundary, tuple(trusted)
                )
    """

    @pytest.fixture
    def admits(self) -> Admits:
        raise NotImplementedError("Override the 'admits' fixture with your implementation")

    @pytest.mark.parametrize("case", CASES, ids=lambda case: case.label)
    def test_the_boundary_is_decided_the_same_way(self, admits: Admits, case: Case) -> None:
        decided = admits(case.endpoint, case.boundary, case.trusted)
        assert decided == case.admitted, (
            f"{case.label}: expected {'admitted' if case.admitted else 'refused'} "
            f"because {case.why}"
        )
