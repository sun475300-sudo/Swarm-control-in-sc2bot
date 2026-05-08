"""Re-export shim for `utils.logger`.

The SC2 bot code under `wicked_zerg_challenger/` widely uses
`from utils.logger import get_logger` — that import resolves at runtime
because the bot is launched from inside `wicked_zerg_challenger/`. When
pytest runs from the project root, however, the top-level `utils/`
package shadows it, breaking the import. This shim forwards the request
to the real implementation so both layouts work without touching ~93
production files.
"""

from wicked_zerg_challenger.utils.logger import *  # noqa: F401,F403
from wicked_zerg_challenger.utils.logger import get_logger  # noqa: F401
