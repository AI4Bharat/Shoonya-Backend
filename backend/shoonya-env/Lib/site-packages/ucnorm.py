import sys
import unicodedata

USAGE = "usage: {prog} [--help] (NFC|NFKC|NFD|NFKD) < INPUT > OUTPUT"

HELP = """This program reads UTF-8 text from stdin and writes it to 
stdout after applying the specified normalization algorithm.

The Unicode standard defines various normalization forms of a Unicode 
string, based on the definition of canonical equivalence and 
compatibility equivalence. In Unicode, several characters can be 
expressed in various way. For example, the character U+00C7 (LATIN
CAPITAL LETTER C WITH CEDILLA) can also be expressed as the sequence
U+0043 (LATIN CAPITAL LETTER C) U+0327 (COMBINING CEDILLA).

Even if two unicode strings look the same to a human reader, if one
has combining characters and the other doesn’t, they may not compare
equal.

For each character, there are two normal forms:

- Normal form D (NFD) is also known as canonical decomposition, and
  translates each character into its decomposed form.

- Normal form C (NFC) first applies a canonical decomposition, then 
  composes pre-combined characters again.

In addition to these two forms, there are two additional normal forms
based on compatibility equivalence:

- Normal form KD (NFKD) will apply the compatibility decomposition,
  i.e. replace all compatibility characters with their equivalents.

- Normal form KC (NFKC) first applies the compatibility decomposition,
  followed by the canonical composition.

Compatibility decomposition ensures that equivalent characters will
compare equal (i.e. have the same codepoints). In Unicode, certain
characters are supported which normally would be unified with other
characters. For example, U+2160 (ROMAN NUMERAL ONE) is really the
same thing as U+0049 (LATIN CAPITAL LETTER I). However, it is 
supported in Unicode for compatibility with existing character sets
(e.g. gb2312).

This program uses the normalization algorithms implemented in Python's
standard library. See:
https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize

"""

def _main():
    for arg in sys.argv:
        if arg in ["--help", "-h", "-?"]:
            print(USAGE)
            print()
            print(HELP)
            sys.exit(0)

    if len(sys.argv) != 2:
        print(USAGE.format(prog=sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    algo = sys.argv[1].upper()
    if algo not in ["NFC", "NFKC", "NFD", "NFKD"]:
        print(f"Invalid normalization algorithm '{algo}'", file=sys.stderr)
        print(USAGE.format(prog=sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    for line in sys.stdin:
        sys.stdout.write(unicodedata.normalize(algo, line))


if __name__ == "__main__":
    _main()

