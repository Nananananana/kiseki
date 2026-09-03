# ADR-0087: Which algorithm decides a stay is the owner's choice

## Status

Accepted.

## Context

Stop extraction had one algorithm, and it was the library. ADR-0006
chose proximity plus drift and measured its thresholds against a real
photo library, which is more than most such numbers get. But the
choice was invisible: nothing named it, nothing else was offered, and
no answer said which algorithm had produced it.

Two things made that worth changing.

**The single radius is a real limitation, not a stylistic one.**
`stay_radius` is 300 metres everywhere, so a dense city centre and a
sparse hillside are judged the same way. There is no value that is
right for both, and no amount of tuning finds one. Every algorithm
that takes a single radius has this problem; the ones that do not are
published, well understood, and could not be written against the
standard library alone.

**A derivation that cannot say what produced it cannot be argued
with.** A reader comparing this year with last year is comparing two
runs, and if the algorithm changed between them the comparison is
meaningless in a way nothing would have shown.

## Decision

The algorithm is a setting, resolved through the same five layers as
the storage paths and the model host, and named in the build report.

Seven detectors, in two places for one reason:

- **Four in the domain**, in plain Python, from each paper's published
  description. `sequential` (this library), `staypoint` (Li et al.
  2008), `dbscan` (Ester et al. 1996), `stdbscan` (Birant and Kut
  2007). The domain declares no dependency, and a check against a
  built wheel's `Requires-Dist` keeps it that way.
- **Three in the adapters**, behind an optional extra:
  `dbscan-indexed`, `hdbscan` (Campello et al. 2013) and `optics`
  (Ankerst et al. 1999), on scikit-learn.

`sequential` stays the default, because it is the only one whose
thresholds came from anybody's actual photographs.

**Resolution happens at the interface layer**, not in the pipeline.
The accelerated detectors live above the application in the layering,
so an application that resolved a name would invert the dependency —
`lint-imports` refused exactly that when this was first written the
other way. The interface resolves and hands down the callable, with
the name beside it for the report.

**An unrecognised name is refused and never falls back.** A reader who
mistyped an algorithm and silently got the default would be told their
answers came from a detector they did not choose.

## Consequences

- The library can answer what its neighbours answer. Varying-density
  clustering was not reachable from the standard library, and pretending
  otherwise would have meant a worse answer with a purer dependency list.
- **Two libraries built with different detectors are not comparable**,
  however alike the numbers look. `kiseki build` prints the detector so
  that is visible rather than inferred. Rebuilding is cheap and total
  (ADR-0013), so switching costs one rebuild and loses nothing.
- The pure `dbscan` is a reference implementation and a correctness
  oracle, not something to run: 20.1 seconds against 0.058 for the
  indexed one at five thousand photographs, measured. Saying so is part
  of shipping it.
- **The two DBSCANs are a cross-check nothing else in this repository
  has.** One specification implemented twice, independently, with a test
  asserting they group photographs identically. Where two such
  implementations disagree, one is wrong and reading either would not
  say which.
- The extra is scikit-learn and NumPy, both BSD-3-Clause, chosen partly
  for that.
- More algorithms is more surface. The shared contract — every
  photograph appears exactly once, nothing in gives nothing out, an
  unlocated photograph is set aside, two runs agree — is checked for
  every detector at once, so adding one costs a registry entry rather
  than a test suite.

## Alternatives considered

**Leave it alone.** The measured default is genuinely good and nobody
had complained. Declined because the limitation is structural: no
single radius fits a life lived at two scales, and the reader with
that problem would never know why their answers were poor.

**Depend on scikit-learn outright.** Simpler, and it would have
deleted three hundred lines. Declined because `kiseki` declaring no
runtime dependency is a promise this repository checks against a built
wheel, and it is the reason the package can be installed anywhere.

**Ship only the accelerated ones and require the extra.** Declined for
the same reason, and for a second: a reference implementation you can
read beside the paper is worth having even when it is too slow to use.
