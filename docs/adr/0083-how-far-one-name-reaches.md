# ADR-0083: How far one name reaches

## Status

Accepted. Extends ADR-0072, after measuring it.

## Context

ADR-0072 settled that one name standing for sixteen places is not
sixteen duplicates, and that a listing should say how many. It did not
say how far apart they are, and a count alone cannot tell two very
different things apart.

Measured against a real library of 213 places under 75 names:

```text
places   widest gap
    16      16.3 km
    16       4.3 km
    13       6.3 km
    12       1.2 km
    11       9.3 km
     7      20.4 km
```

Twelve places inside 1.2 km is one suburb, correctly named. Seven
places across 20.4 km is a name borrowed from further away than anyone
would call a place. Both printed as *one name, N places* and read
alike.

The obvious remedy was tried first and does not work. `kiseki places`
folds by the nearest gazetteer entry, and the gazetteer **already
answers with the nearest entry it holds**, so narrowing the search
radius folds no fewer names -- it only leaves places unnamed:

```text
radius     named / distinct names / unnamed
25,000m     213 /  75 /   0     (today)
15,000m     205 /  74 /   8
10,000m     195 /  72 /  18
 5,000m     169 /  60 /  44
```

Halving the radius twice costs 44 places their names and removes 15
names, most of them because their only member went unnamed. Several
clusters genuinely share their nearest entry, and no radius separates
them: `cities500.txt` holds populated places of 500 or more and has
nothing finer to offer in between.

## Decision

The listing gives the widest distance between the places a name stands
for: *and 15 more within 16.3 km*.

The widest pair rather than the distance from the first, which
understates a line of places running away from it. Metres below a
kilometre, kilometres above -- a place is not located to the metre and
a fold is not measured to one.

`NAME_WITHIN` stays at 25 km. It was never the lever, and lowering it
trades names for nothing.

## Consequences

- A reader can tell a correctly named suburb from a borrowed name
  without leaving the listing, which is the same standard ADR-0066 set:
  show enough to read, and say what was kept back.
- `fold_by_name` now returns the rows folded into each line rather than
  a count of them. The count is `len`, and the caller can measure what
  it holds. One call site, and the history listings are unaffected.
- **This could stop being true.** A denser gazetteer would give the
  tight folds real names of their own and shrink the fold to the point
  where the distance stops being interesting. GeoNames
  `allCountries.txt` carries `PPLX`, a section of a populated place,
  at 1.5 GB against 40 MB. If the owner ever downloads one, measure
  again before deciding this line still earns its place.
- Nothing about the clustering changes. A hundred and fifty metres
  apart is still two places, and the measurement gives no reason to
  revisit it.
