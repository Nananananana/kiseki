# 0017 Read interests from the return pattern, not from the anchors

## Status

Accepted

## Context

ADR-0016 fixed the shape of an interest before any derivation existed.
This record decides the first derivation: which measured facts become
interests, and by what rule.

Two candidate sources exist in v0.1. Anchors are the places a life is
anchored to, visited on enough separate days to include homes and
workplaces. The place summary (`summarise_places`) groups the stops of
outings and measures the return pattern of the places someone chose to
go to.

## Decision

**Derive from the place summary, not from the anchors.** An anchor
with a high visit count is very often where someone lives or works,
and "you are strongly interested in your own home" is not a finding.
The return pattern of outings describes choices; the anchors describe
circumstances.

**Only returned-to places become interests.** Going back is the
clearest statement of having liked somewhere. A place seen on a
single day stays out: single visits and single photographs are a
different source of evidence and arrive with captioning (FR-507).

**The rule is deterministic and the constants are named.** The score
is `visit_days / (visit_days + 1)`. The confidence is the product of
two saturating factors, `visit_days / (visit_days + 3)` and
`span_days / (span_days + 30)` where the span runs from first to last
visit. The same score can carry very different confidence: twelve
visits over two years and two visits last week point equally hard at
their places, and deserve nothing like the same trust. No model is
consulted; the tests pin the numbers exactly.

**The topic is a coordinate reference, not a label.** An interest is
named `place:{lat},{lon}` at five decimal places, keeping ADR-0012's
refusal to categorise places. Human-readable topics arrive with
captioning, where a label describes what was photographed rather
than what a place is for. References stay inside the library;
coordinate blurring on export applies to them as to everything else.

**Evidence points at the two ends of the pattern.** The place summary
keeps only the first and last visit days, so those are what the
evidence can honestly reference. Recording every visit day would need
the measures to carry more, and can be revisited when something needs
it.

## Consequences

- The derivation is a pure domain service; wiring it into the
  pipeline and storing the resulting profile through the
  ProfileRepository port is the next issue.
- Captioning will add PHOTOGRAPH evidence to the same Interest shape,
  including for places this rule excludes.
- Ranking is preserved from the measures. Interpretation reads what
  was measured; it does not quietly reorder it.
