boxing
======

Draw boxes like never before! Python porting of `boxen <https://github.com/sindresorhus/boxen>`_.

Install
-------

``pip install boxing``

or

``pipenv install boxing``

Usage
-----

``boxing(text, style='single', margin=1, padding=1)``

.. code-block:: python

    >>> from boxing import boxing
    >>> boxing("Hello, world!")

        ┌───────────────────┐
        │                   │
        │   Hello, world!   │
        │                   │
        └───────────────────┘

    >>> boxing("boxing", style="double", padding=2, margin=1)

        ╔══════════════════╗
        ║                  ║
        ║                  ║
        ║      boxing      ║
        ║                  ║
        ║                  ║
        ╚══════════════════╝


