"""Test-suite configuration for known third-party compatibility notices."""

import warnings

from starlette._utils import StarletteDeprecationWarning

warnings.filterwarnings("ignore", category=StarletteDeprecationWarning)
