# Concept

## The problem

People cannot describe their own preferences accurately. Asked what sort of day
out they enjoy, most give an answer that their calendar contradicts. The gap is
not dishonesty; it is that habits are invisible from inside them.

A photo library is a record of where somebody actually chose to spend their
time, kept without any intention of being analysed. It is more truthful than an
answer to a question, and almost nobody reads it that way.

## The claim

> A sequence of photographs says something about a person that no single
> photograph does.

One photograph of a temple says a temple was in front of somebody. Four
photographs, timed and placed, say they left at nine, spent the morning outdoors,
ate at midday, and finished somewhere warm. The second is a fact about a person.

Everything in this library follows from taking that seriously.

## What follows from it

### Sequence before content

Stop extraction, outing assembly and anchor estimation all run on time and place
alone, before any image is opened. Image understanding arrives in v0.2, and by
then the structure it describes already exists.

This ordering also keeps the expensive part small. Captioning every photograph
in a library is prohibitive; captioning one representative image per stop is not.

### Measure, then interpret

The analytics count and summarise. They never write a sentence. Interpretation
belongs to a language model in v0.2, reading those numbers.

The seam matters. Measures can be asserted against exact values; sentences
cannot. With the split, changing a prompt cannot silently change what was
measured, and a poor profile can be diagnosed as either bad numbers or a bad
reading of them.

### Observe, do not categorise

The first design classified places as home, workplace or second base. Run against
a real library it got all three wrong, because it assumed one shape of life.

Reporting `night 6%, weekday 100%, daytime 90%` instead is both more accurate and
more informative than the label `workplace` would have been. See ADR-0012.

### What is not measured cannot be claimed

A profile in v0.2 can only say what the measures support, and must cite the
outings behind each statement. A guess about somebody is only useful if they can
check it.

## What this is not

It is not a photo organiser, a map of where you have been, or a travel journal.
Those describe photographs. This describes a person.

It is not a recommender that has read the internet. Its only knowledge is one
person's own record, which is the point: the suggestions it eventually makes are
derived from evidence the user can inspect.

## Where it is heading

A question answered from your own history, with its reasoning shown:

> **"Somewhere to go this Saturday?"**
>
> Somewhere green, an hour or so out, arriving late morning.
>
> Based on: you go out most Saturdays, usually leaving around eleven; your
> median outing covers under two kilometres but you make an exception for
> gardens; and of the places you have returned to, four of the top five are
> outdoors. Drawn from 47 outings over two years.

Every clause there is a measure this library already computes. What v0.2 adds is
the sentence, and what v1.0 adds is knowing whether it will rain.
