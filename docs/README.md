# The documents, and what each one is for

KISEKI's documentation is written so that three different things
never get mistaken for one another:

- **what is true now** -- the current architecture and rules;
- **why it became true** -- the decisions, as they were made;
- **what might become true** -- proposed and planned work.

A reader who cannot tell these apart will implement a proposal as
though it shipped, or "fix" an ADR to match today's code and erase
the reasoning that produced it. Both have a cost that grows with the
project, so the separation is structural: each document says at the
top which of the three it is.

## Responsibilities

| Document | Responsibility |
|---|---|
| `README.md` | For anyone outside: what KISEKI is, what it solves, what it can do |
| `AGENTS.md` | For contributors and AI agents: the current rules, constraints and state |
| `docs/architecture.md` | The current architecture, its dependencies and its principles |
| `docs/concept.md` | The conceptual model and the whole picture |
| `docs/context-map.md` | The current boundaries of responsibility |
| `docs/ubiquitous-language.md` | The domain words in current use, defined |
| `docs/records.md` | What every input contract shares, and the gate a new one passes |
| `docs/photo-record.md` | PhotoRecord and the producer contract |
| `docs/activity-record.md` | ActivityRecord and the producer contract |
| `docs/note-record.md` | NoteRecord and the producer contract |
| `docs/interest-export.md` | The interest export, the one contract that leaves |
| `docs/conformance.md` | The producer conformance specification |
| `docs/cli.md` | The commands as they behave today |
| `docs/adr/` | Decisions as they were made, with their reasons -- history |
| `docs/proposals/` | Proposed or planned work -- not necessarily implemented |
| `docs/requirements-addendum.md` | Requirements and how far they are implemented |
| `docs/releases/` | What each released version contains |
| `CHANGELOG.md` | The released history, briefly |

## The rules that keep them apart

- An ADR is not edited to match the present. A decision that no
  longer holds is superseded by a later ADR that says so; the
  original stays as it was written, because the reasoning is the
  point.
- A proposal is never cited as evidence that something exists. When
  a proposal lands, the current-state documents change and the
  proposal stays where it is, describing what was proposed.
- The current-state documents describe what the code does today. If
  one of them disagrees with the code, one of the two is wrong and
  the disagreement is a defect -- not a difference of opinion.
- An architecture document says why, not only what. A rule without
  its reason is a rule the next reader will break for good reasons
  of their own.
