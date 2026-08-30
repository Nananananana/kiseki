# ADR-0085: The producer is given an address, and fetches nothing

## Status

Accepted. Corrects `docs/web-record.md`, which was settled before the
producer existed (#307) and got this wrong.

## Context

The contract said the page's text reaches the classifier. It does not,
and it cannot: **a browser history holds a URL, a title and visit
times, and no page.** The sentence was written by somebody -- me --
who had settled a contract without asking where its first input comes
from.

Three ways to get the text, and only one of them is a way.

**Fetch each URL.** A producer that re-requests every page the owner
visited is a second browsing session: visible in the sites' logs,
dated today, from the owner's address, and made by a program rather
than a person. It sees nothing behind a login, so it would classify
the sign-in page where the owner read their bank statement. And the
page has changed since they read it, sometimes into something else
entirely.

**Read the browser cache.** `cache2` and its Chromium equivalent are
undocumented, versioned, partial, and evicted. Most of what matters is
not there, and the parsing would be a library reading the owner's
browsing -- the same objection `docs/note-record.md` makes to `.docx`.

**Do not get it.** Classify from the address and the title, which the
history already holds.

## Decision

The producer is given the address and the title. **It never makes a
request to a site**, not to fetch, not to check, not to resolve a
name.

The record is unchanged: no URL, no title, no text, no host. What
changes is the honest description of what the trust boundary protects.
`https://<a clinic>/appointments/cancel`, and the title beside it, are
the most revealing strings in this system -- routinely more revealing
than the page body, because a body is prose and an address is a
statement of what the owner went there to do. *The text reaches the
classifier* understated it. *The address and the title reach the
classifier* is true and worse, and it is what the boundary is for.

## Consequences

- **The classification is thinner, and sometimes wrong.** An address
  that says nothing -- an opaque identifier, a single-page application,
  a shortened link -- classifies from a title alone, and a page with
  neither lands in `other` or `private`. That is the price, and it is
  paid in usefulness rather than in exposure, which is the direction
  this library prefers.
- **The producer needs no network of its own**, other than the model.
  `kiseki privacy` can therefore say the same thing about the web
  source that it says about captioning: what leaves is what goes to the
  model, and the trust boundary decides where the model is.
- A later producer that added fetching to be helpful would break a
  promise the owner cannot check from the record -- the records look
  identical either way. That is why this is a decision rather than a
  sentence in a docstring.
- **This could stop being true** only if a browser began exporting
  page text the owner already has, which is a different source and a
  different contract. Fetching does not become acceptable because the
  classification would improve.
