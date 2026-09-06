# The gazetteer

Place naming resolves coordinates to names offline, from a GeoNames
file you download yourself. Nothing is bundled and nothing is ever
fetched: no file simply means no names, and everything else works
unchanged (ADR-0040).

1. Download `cities500.zip` from
   https://download.geonames.org/export/dump/
2. Unzip `cities500.txt` to `<data root>/gazetteer/cities500.txt`,
   or point `KISEKI_GAZETTEER_PATH` anywhere you like (a larger
   GeoNames file such as `allCountries.txt` works too).

GeoNames data is licensed CC BY 4.0, (c) GeoNames.org. The file
stays on your machine and is only ever read.

Names are resolved at presentation time and never stored, so the
file can be replaced or deleted at any moment. Anchors -- the places
that look like home or work -- are never named.

With the file in place, `kiseki profile` and `kiseki view` label the
place topics: the name alone when blurred, the name beside the
reference when raw. `kiseki tell` lets the named places speak, with
the single captions photographed beside them (ADR-0041); `/tell`
over HTTP stays place-silent.

## Why `cities500` and not something finer

`cities500.txt` holds populated places of 500 people or more, and it
is what the naming is measured against: on a real library of 213
places it named every one of them, under 75 names.

Its coarseness is visible in the fold. Several clusters share their
nearest entry -- twelve inside a kilometre and a half in one case,
seven across twenty in another -- and no search radius separates them,
because the file has nothing in between. Narrowing the radius only
leaves places unnamed (ADR-0083).

The finer file is GeoNames `allCountries.txt`, which carries `PPLX`,
a section of a populated place. It is 1.5 GB against 40 MB, and this
library has no need of it yet: the listing says how far a name
reaches, which is what the coarseness actually costs a reader. If you
download one, `kiseki places` will use it without any change here --
the loader reads the same columns.

## It is read once

`cities500.txt` is 235,000 rows and 40 MB. The first command that
names a place parses it and writes a compact copy under
`<cache>/gazetteer/` -- coordinates as a flat array, names as text,
nothing that can execute -- keyed by the file's size and modification
time. Every later command reads the copy in a fraction of the time,
and a command that names places twice reads it once. Download a
newer file and the old copy is replaced on the next run; delete the
directory to force a re-read. Measured on one library of 4,950
photographs: `suggest` went from 2.3 seconds to 0.9, `places` from
1.7 to 0.8, and the first run after a download takes 1.2 seconds to
write the copy. About half a second of what remains is Python starting.
