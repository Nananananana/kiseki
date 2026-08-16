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
