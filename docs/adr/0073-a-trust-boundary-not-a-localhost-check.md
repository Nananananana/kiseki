# ADR-0073: A trust boundary, not a localhost check

## Status

Accepted. Groundwork for v0.11: a model that may live on another
machine.

## Context

Captioning sends a photograph. Not a description of one, not a
reference: the reduced copy itself, base64 in an HTTP body. The
library has always sent it to `localhost`, `kiseki privacy` has always
said nothing leaves the machine, and both were true at once.

The realistic deployment is not always a laptop. A household or a team
has one machine with a GPU, and the adapters have carried a `host`
parameter since v0.2 -- with nothing wiring it, so the parameter was a
promise nobody could keep. The moment it can be set, the two
statements above stop being the same statement.

An external endpoint is a different thing here than in a tool that
sends text somebody chose to send. A photograph was taken, not
composed for sending. The default has to be stricter than the
convenient one.

## Decision

An endpoint is judged before anything is sent to it. Three boundaries,
the strictest by default:

    same_host        only this machine        (the default)
    private_network  and a machine on the LAN
    anywhere         and anything

A host in `trusted_hosts` is admitted under all of them. Widening the
boundary is a shrug that outlives the reason for it; naming a host is
a sentence somebody wrote, and it stays readable in `kiseki privacy`.

Locality is judged from the host's own shape: loopback addresses and
`localhost`, private ranges and link-local, a single-label name, and
the suffixes that only exist inside a network. Everything else is
UNKNOWN, and UNKNOWN is refused.

Nothing here resolves a name. Resolution is a network call, and a
module whose job is to decide whether to make a network call must not
make one to decide. A wrong refusal costs a line of configuration; a
wrong admission costs the photographs.

`private_network` is not offered as the default even though it is the
convenient one. A home network holds a television, a games console and
whatever a guest brought; an office network is a different judgement,
and the owner is the one who can make it.

## Consequences

- `kiseki privacy` can stop claiming that no network call exists, and
  say instead where the photographs go. It has been inaccurate since
  captioning existed.
- v0.11's web-history producer inherits the same question: a
  classifier reads the page before the URL is thrown away, so where
  that classifier runs is the whole privacy argument.
- The wiring, the `kiseki llm` command and the corrected privacy
  wording follow in their own change; this one is the decision and its
  arithmetic.
