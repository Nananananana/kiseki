"""Turns a folder of notes the owner named into NoteRecord v1 documents.

A producer, outside the core. It reads the notes, decides a category
and a handful of labels, and discards everything else -- the text, the
file name, the path -- before anything reaches a library. A core that
read the text and then dropped it could not prove it had dropped it;
a core that never receives it has nothing to prove. See ADR-0075.
"""
