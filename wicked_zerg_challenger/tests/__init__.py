# -*- coding: utf-8 -*-
"""Test package init.

unittest's discover loader does not automatically import `conftest.py`
(that's a pytest-only convention), so we do the sc2 fake-module install
here from `__init__.py`. This guarantees the same stub classes are
visible to both production source and the tests themselves *before* any
`test_*.py` module is imported.
"""

from . import conftest  # noqa: F401  (side-effect import)
