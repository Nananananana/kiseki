# Algorithms: what decided this, and how to change it

Separating stays from journeys is a judgement, not a calculation.
Seven algorithms are available and they disagree, on purpose. This
page is what to choose between and what choosing costs.

```bash
kiseki algorithms          # what is chosen, and what else exists
```

---

## The choices

| name | what it asks | needs | from |
|---|---|---|---|
| `sequential` | is this still the same stay | nothing | this library, [ADR-0006](adr/0006-detect-stops-by-proximity-and-speed.md) |
| `staypoint` | is this still within the radius of where the stay began | nothing | Li, Zheng, Xie, Chen, Ma, Wang — ACM GIS 2008 |
| `dbscan` | where is this person densely present | nothing | Ester, Kriegel, Sander, Xu — KDD 1996 |
| `stdbscan` | the same, with a radius in time as well | nothing | Birant, Kut — DKE 2007 |
| `dbscan-indexed` | the same as `dbscan`, with the search done properly | `clustering` | as above, on scikit-learn |
| `hdbscan` | where is this person densely present, **at any scale** | `clustering` | Campello, Moulavi, Sander — PAKDD 2013 |
| `optics` | the same, ordered by how dense | `clustering` | Ankerst, Breunig, Kriegel, Sander — SIGMOD 1999 |

The first four are written in plain Python inside
`kiseki.domain.services.detectors`, from each paper's published
description. The domain declares no dependency and a check against a
built wheel keeps it that way.

The last three live in `kiseki.adapters.clustering` and arrive with an
extra:

```bash
pip install "kiseki[clustering]"
```

scikit-learn and NumPy are both BSD-3-Clause, so the extra is usable
in commercial work.

---

## Changing it

The same five layers as every other setting, each beating the one
above it:

```text
1  the default                     sequential
2  kiseki.toml                     [algorithm]
                                   stops = "hdbscan"
3  .env                            KISEKI_ALGORITHM_STOPS=hdbscan
4  the environment                 KISEKI_ALGORITHM_STOPS=hdbscan
5  the command line                kiseki --stop-detector hdbscan build
```

An unrecognised **setting** is refused rather than ignored, and so is
an unrecognised **name**. Nothing silently falls back to the default:
a reader who mistyped an algorithm and got `sequential` would be told
their answers came from a detector they did not choose, which is worse
than an error and much harder to notice.

---

## What choosing costs

**Changing the detector changes what the word *stop* means** in every
answer above it — how many outings there were, which places are
anchors, what `suggest` thinks is overdue. Two libraries built with
different detectors are not comparable, however alike the numbers
look. `kiseki build` prints which one it used for exactly that reason.

Rebuilding is safe and cheap: derived data is replaced wholesale
([ADR-0013](adr/0013-derived-data-is-replaced-not-amended.md)), so
switching and switching back costs one rebuild each way and loses
nothing.

---

## Which to use

**`sequential`, unless you have a reason.** It is the default because
it is the only one whose thresholds were measured against somebody's
real photo library. The rest are correct implementations of published
algorithms handed this library's numbers, which is a weaker claim and
worth saying plainly.

**`staypoint`** if you want a stay to mean *near where it started*.
`sequential` measures from the moving centre of the group, so a slow
walk across a park stays one visit; `staypoint` measures from the
first photograph and never moves, so it cuts. Neither is more correct
— it depends on whether *I was at the park* or *I was at the bench by
the pond* is the answer you wanted.

**`hdbscan`** if your life happens at more than one scale. Every other
detector takes a single `stay_radius` and applies it everywhere, so a
dense city centre and a sparse hillside cannot both be right. HDBSCAN
asks for no radius at all, only how small a place may be.

**`dbscan` — for reading, not for running.** Measured on this machine:

```text
photographs   sequential   dbscan (pure)   dbscan-indexed   hdbscan
       500       0.004 s         0.190 s          *              0.010 s
      2000       0.049 s         3.912 s        0.016 s          0.084 s
      5000       0.021 s        20.092 s        0.058 s          0.439 s

* the first scikit-learn call in a process pays about a second of
  import and warm-up; it is not the algorithm.
```

The pure DBSCAN compares every photograph with every other, because a
spatial index is a dependency and the domain has none. At five
thousand photographs that is **twenty seconds against six
hundredths** — three hundred times slower for the same answer. It
earns its place as a readable reference implementation and as the
thing `dbscan-indexed` is checked against; it is not what to point at
a real library.

That check is worth knowing about: the two are the same algorithm
written twice, once in plain Python and once on scikit-learn's ball
tree, and a test asserts they group the photographs **identically**.
Two implementations of one specification agreeing is the strongest
evidence available that either is right.

---

## A note on distance

The scikit-learn detectors work in radians on the **haversine**
metric. Clustering latitude and longitude with a Euclidean metric
treats a degree of longitude as a degree of latitude, which at this
library's default latitude is an 18% error before anything else
happens — and produces plausible clusters nobody can fault. If you
add a detector, do the same.

---

## Adding one

A detector is a module with `NAME` and `extract(observations,
settings)` returning a `StopExtraction`. Put a pure one in
`kiseki/domain/services/detectors/` and add it to `DETECTORS`; put one
that needs a library in `kiseki/adapters/clustering/` and add it to
`ACCELERATED`.

Both lists are written out rather than discovered by walking the
package. A registry built by a walk is a registry that quietly holds
nothing on the day the walk stops matching.

The shared contract is checked for every detector at once
(`tests/unit/domain/test_the_algorithm_is_a_choice.py`): every
photograph appears exactly once, nothing in gives nothing out, a
photograph with no coordinates is set aside, and two runs over one
library give the same answer.
