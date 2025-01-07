"""
A module for interfacing with ``split-sentences.perl`` from Moses toolkit.

Copyright ® 2016-2017, Luís Gomes <luismsgomes@gmail.com>
"""

usage = """
Usage:
    moses-sentence-splitter [options] <lang> [<inputfile> [<outputfile>]]
    moses-sentence-splitter --selftest [--verbose]

Options:
    --selftest, -t  Run selftests.
    --verbose, -v   Be more verbose.
    --unwrap, -u    Assume that the text is wrapped and try to unwrap it.
                    Note that this option will cause all consecutive non-empty
                    lines to be buffered in memory.  If you give this option
                    make sure that you have empty lines separating paragraphs.
                    When this option is not given, each line is assumed to be
                    an independent paragraph or sentence and thus will not be
                    joined with other lines.
    --more          Also split on colons and semi-colons.
    --even-more     Also split on extra unicode characters.

2016, Luís Gomes <luismsgomes@gmail.com>
"""


import re
import sys
from os import path

from docopt import docopt
from openfile import openfile

from toolwrapper import ToolWrapper
from ucenum import ucenum
from ucinfo import ucinfo


UNICODE_TERMINATORS = "".join(
    c.printable for c in map(ucinfo, ucenum('P'))
    if c.printable != '.' and c.name.endswith("FULL STOP")
    or "INVERTED" not in c.name and
    ("QUESTION MARK" in c.name or "EXCLAMATION MARK" in c.name)
)


class MosesSentenceSplitter(ToolWrapper):
    """
    A class for interfacing with ``split-sentences.perl`` from Moses toolkit.

    This class communicates with split-sentences.perl process via pipes. When
    the MosesSentenceSplitter object is no longer needed, the close() method
    should be called to free system resources. The class supports the context
    manager interface. If used in a with statement, the close() method is
    invoked automatically.

    When attribute ``more`` is True, colons and semi-colons are considered
    sentence separators.

    When attribute ``even_more`` is True, all unicode full stop characters,
    exclamation marks and question marks are considered sentence separators.
    Note: this option is not available in the original Moses Tokenizer.

    >>> split_sents = MosesSentenceSplitter('en')
    >>> split_sents(['Hello World! Hello', 'again.'])
    ['Hello World!', 'Hello again.']

    """

    def __init__(self, lang="en", more=True, even_more=False):
        self.lang = lang
        program = path.join(
            path.dirname(__file__),
            "split-sentences.perl"
        )
        argv = ["perl", program, "-q", "-b", "-l", self.lang]
        if more:
            argv.append("-m")
        self.even_more = even_more
        super().__init__(argv)

    def __str__(self):
        return "MosesSentenceSplitter(lang=\"{lang}\")".format(lang=self.lang)

    def __call__(self, paragraph):
        """Splits sentences within a paragraph.
        The paragraph is a list of non-empty lines.  XML-like tags are not
         allowed.
        """
        assert isinstance(paragraph, (list, tuple))
        if not paragraph:  # empty paragraph is OK
            return []
        assert all(isinstance(line, str) for line in paragraph)
        paragraph = [line.strip() for line in paragraph]
        assert all(paragraph), "blank lines are not allowed"
        for line in paragraph:
            self.writeline(line)
        self.writeline("<P>")
        sentences = []
        while True:
            sentence = self.readline().strip()
            if sentence == "<P>":
                break
            sentences.append(sentence)
        if self.even_more:
            sentences = MosesSentenceSplitter._split_even_more(sentences)
        return sentences

    @staticmethod
    def _split_even_more(sentences):
        result = []
        for s in sentences:
            parts = re.split(f'([{UNICODE_TERMINATORS}])', s)
            if len(parts) == 1:
                result.append(s)
            else:
                for new_s, term in zip(parts[:-1:2], parts[1::2]):
                    result.append(new_s + term)
        return result


def read_paragraphs(inputfile, wrapped=True):
    lines = map(str.strip, inputfile)
    if wrapped:
        paragraph = []
        for line in lines:
            if line:
                paragraph.append(line)
            elif paragraph:
                yield paragraph
                paragraph = []
        if paragraph:
            yield paragraph
    else:
        for line in lines:
            yield [line] if line else []


def write_paragraphs(paragraphs, outputfile, blank_sep=True):
    for paragraph in paragraphs:
        for sentence in paragraph:
            print(sentence, file=outputfile)
        if blank_sep or not paragraph:
            print(file=outputfile)  # paragraph separator


def main():
    args = docopt(usage)
    if args["--selftest"]:
        import doctest
        import mosestokenizer.sentsplitter
        doctest.testmod(mosestokenizer.sentsplitter)
        if not args["<lang>"]:
            sys.exit(0)
    split_sents = MosesSentenceSplitter(args["<lang>"], more=args["--more"],
        even_more=args["--even-more"])
    inputfile = openfile(args["<inputfile>"])
    outputfile = openfile(args["<outputfile>"], "wt")
    with inputfile, outputfile:
        paragraphs = read_paragraphs(inputfile, wrapped=args["--unwrap"])
        paragraphs = map(split_sents, paragraphs)
        write_paragraphs(paragraphs, outputfile, blank_sep=args["--unwrap"])


if __name__ == "__main__":
    main()
