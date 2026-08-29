# ADR-0067: One reading of a theme set

## Status

Accepted. Found by the first run of the history commands against two
years of real photographs; extends ADR-0053 to every reader.

## Context

Trend, lifecycle and comparison each turn a theme set into a mapping
from member label to theme name, and each had written the same line to
do it. Written three times, it was corrected in none of them, and two
faults rode through it.

The naming model can produce a generic theme name. The real library
holds a theme called "text" (members: text, document) and one called
"object" (members: object, digital object). The profile refuses those
(ADR-0053) and every history feature reported them as topics -- the
same word treated as evidence in one place and as noise in another.

A theme set can also hold two themes with the same name. The real one
holds "transport" twice, "text" twice, "vegetable" twice and "code"
twice. The old line silently kept whichever came last for a shared
member, which is a decision nobody made.

## Decision

`theme_mapping` is the one place a theme set becomes a mapping. It
leaves out themes whose name is generic, and it merges themes that
share a name rather than letting one overwrite the other. A member
belonging to several themes keeps the first mapping: arbitrary, but
stable, and the same for every reader.

`merged_themes` offers the same reading as themes, for callers that
need the set rather than the mapping.

## Consequences

- A rule about theme names now applies wherever theme names are read,
  which is what ADR-0053 meant and did not achieve.
- The duplicate names remain in storage. They are what the model
  produced, and the library reads them honestly rather than rewriting
  what was said -- the posture of ADR-0044 and ADR-0054.
- The overlap between theme names and members of other themes --
  "plant" is a theme and a member of "nature" -- is a separate fault,
  visible in the profile as a theme and its member both ranking. It is
  not fixed here.
