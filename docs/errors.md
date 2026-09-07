# kiseki-errors v1

*What is true now.* The catalogue of everything that can go wrong here,
written for a program that has to fold failures across several
libraries. The decision is [ADR-0094](adr/0094-a-failure-says-its-name.md).

```bash
kiseki errors --json
```

It reads nothing: no database, no paths, no model. A catalogue that
needed the library to exist would be one nobody could read while
deciding whether it does.

## The document

```json
{
  "schema": "kiseki-errors",
  "version": 1,
  "contract": "kiseki.errors/1-draft",
  "by": "kiseki/0.11.0",
  "errors": [
    {
      "kind": "ModelUnavailable",
      "exit_code": 4,
      "outcome": "unavailable",
      "retryable": true,
      "detail": "The model could not be reached. Running again later continues from here.",
      "detail_ja": "モデルに届かなかった。あとで実行し直せば、ここから続く。"
    }
  ],
  "open_namespaces": []
}
```

Two names, and both are meant. `contract` is what the family calls this
document, so that a consumer reading several libraries reads one shape.
`schema` and `version` are how every document here names itself
(ADR-0081). The version inside the contract name is the served version,
and a test refuses them drifting apart.

| field | what it is |
|---|---|
| `kind` | the stable identifier, exactly as it appears before the colon on the first line of stderr |
| `exit_code` | the code that always accompanies this kind, or `null` where it varies |
| `outcome` | one of `refused`, `unavailable`, `failed`, `timed_out` |
| `retryable` | may the same request be made again, unchanged. Only this library knows |
| `detail` | one line of English |
| `detail_ja` | the same, in Japanese, written here rather than translated elsewhere |

## What can go wrong

| kind | exit | outcome | ask again? |
|---|---|---|---|
| `ModelRefused` | 3 | refused | no |
| `ModelUnavailable` | 4 | unavailable | yes |
| `ModelTimedOut` | 5 | timed_out | yes |
| `ModelTooFarAway` | 2 | refused | no |
| `RecordsUnreadable` | 2 | failed | no |
| `ArgumentsConflict` | 2 | failed | no |
| `ArgumentUnreadable` | 2 | failed | no |
| `SettingUnusable` | 2 | failed | no |
| `NothingStored` | 2 | failed | no |
| `StageStopped` | — | failed | yes |

`open_namespaces` is empty and is expected to stay so. Every name this
library prints is in the table; a reader may take the set as closed.

## What `retryable` means

**May the same request be made again, unchanged?** Not *could a second
attempt succeed*. A failure where asking again is itself a new event --
something leaves the machine, something is charged, something is
written -- is `false` even when a second attempt would work, because a
consumer should not be handed a reason to send it twice. The wording
is the family's, arrived at by two libraries separately.

The three that are `true` here were checked against it rather than
carried over:

- `ModelUnavailable`: nothing was written for the readings that were
  never answered, and the next run asks for exactly those.
- `ModelTimedOut`: the request did leave this machine, which is why it
  needed checking. A timeout is an unavailability here, so nothing was
  written for it; the model is the owner's own, on a host the owner
  allowed (ADR-0073); and this library retries it on the next run
  whatever a consumer decides, so `false` would be a claim the
  library itself contradicts.
- `StageStopped`: the routine resumes rather than repeats, because
  every stage does only the work not already done. It rests on
  keeping a profile being the last stage, so a run that stopped never
  kept one and a rerun cannot keep a second (ADR-0070). A test holds
  that order.

## Two things a consumer should not assume

**An outcome is not a function of the exit code.** Six kinds share exit
2 and one of them, `ModelTooFarAway`, is a refusal rather than a
failure: the model is further away than the owner allowed (ADR-0073), a
decision that no amount of waiting changes. A map from code to outcome
is the right thing to fall back on when no name could be read, and the
wrong thing to check this catalogue against. What holds is that every
code here appears in such a map, not that the outcomes agree.

**The first line of stderr is not always the failure.** When
`--data-root` displaces a path named in a weaker layer, that is said on
stderr, deliberately, because a setting silently ignored is the same
failure as one silently applied (ADR-0079); on a run that then fails,
that advisory comes first. It cannot be mistaken for a name — it begins
with spaces and a dash — so the rule that holds is *the first line that
parses as a name*.

## On stderr

On a non-zero exit, the first line that parses as a name is
`Kind: sentence`. Everything after the colon is this library's to write
and the reader's to keep or discard, so it may name the file that could
not be read. `argparse`'s own refusals are named too, ahead of the usage
block it prints.
