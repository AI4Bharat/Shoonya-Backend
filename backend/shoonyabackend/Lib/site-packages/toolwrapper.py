"""A module for interfacing with external text tools.

Copyright ® 2015-2017 Luís Gomes <luismsgomes@gmail.com>
"""


import io
import logging
import os
import shutil
import subprocess


__version__ = "2.1.0"


class ToolException(Exception):
    """Base class for exceptions raised by ToolWrapper objects"""

    pass


class ToolWrapper:
    """A base class for interfacing with a command line tool via stdin/stdout.

    Communicates with a process via stdin/stdout pipes. When the ToolWrapper
    instance is no longer needed, the close() method should be called to
    free system resources. The class supports the context manager interface; if
    used in a with statement, the close() method is invoked automatically.

    Example usage:

    >>> sed = ToolWrapper(['/bin/sed', 's/Hello/Hi/'])
    >>> sed.writeline('Hello there!')
    >>> sed.readline()
    'Hi there!'
    >>> sed.close()
    """

    @property
    def _full_class_name_(self):
        return ".".join([self.__class__.__module__, self.__class__.__name__])

    def __init__(
        self,
        argv,
        encoding="utf-8",
        start=True,
        cwd=None,
        stdbuf=True,
        stderr=None,
        env=None,
    ):
        self.argv = argv
        self.encoding = encoding
        self.cwd = cwd
        self.stdbuf = stdbuf
        self.stderr = stderr
        self.env = env
        self.proc = None
        self.closed = True
        self.logger = logging.getLogger(self._full_class_name_)
        if start:
            self.start()

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __repr__(self):
        return (
            "{self._full_class_name_}({self.argv!r}, "
            "encoding={self.encoding!r}, cwd={self.cwd!r})".format(self=self)
        )

    def _get_real_argv(self):
        if not self.stdbuf:
            return self.argv
        if shutil.which("stdbuf") is None:  # pragma: no cover
            self.logger.warning(
                f"stdbuf was not found; communication with {self.argv[0]} may "
                "hang due to stdio buffering."
            )
            return self.argv
        return ["stdbuf", "-i0", "-o0"] + self.argv

    def start(self):
        """Launch the sub-process in background"""
        if not self.closed:
            raise ToolException("not closed")
        self.logger.info(f"executing argv {self.argv!r}")
        if self.env:
            env = dict(**os.environ)
            env.update(self.env)
        else:
            env = None
        self.proc = subprocess.Popen(
            self._get_real_argv(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr if self.stderr else subprocess.DEVNULL,
            cwd=self.cwd,
            env=env,
        )
        self.stdin = io.TextIOWrapper(
            self.proc.stdin, encoding=self.encoding, line_buffering=True
        )
        self.stdout = io.TextIOWrapper(
            self.proc.stdout, encoding=self.encoding, line_buffering=True
        )
        self.closed = False
        self.logger.info(f"spawned process {self.proc.pid}")

    def restart(self):
        """Terminates the existing sub-process and launches a new one"""
        self.close()
        self.start()

    def close(self):
        """Closes the pipe to the sub-process."""
        if hasattr(self, "closed") and not self.closed:
            self.logger.info(f"killing process {self.proc.pid}")
            self.proc.kill()
            self.proc.wait()
            self.closed = True
            for attr in "stdin", "stdout":
                if hasattr(self, attr):
                    getattr(self, attr).close()
                    delattr(self, attr)

    def writeline(self, line):
        """Write a line to the sub-process stdin"""
        if self.closed:
            raise ToolException("closed")
        self.logger.debug(f"<< {line}")
        self.stdin.write(line + "\n")
        self.stdin.flush()

    def readline(self):
        """Read a line from the sub-process stdout"""
        if self.closed:
            raise ToolException("closed")
        self.logger.debug("readline()")
        line = self.stdout.readline().rstrip("\n")
        self.logger.debug(f">> {line}")
        return line


if __name__ == "__main__":  # pragma: no cover
    from doctest import testmod

    testmod()
