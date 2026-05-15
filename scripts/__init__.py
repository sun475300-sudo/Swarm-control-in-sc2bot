"""Top-level scripts package.

Declared explicitly (instead of relying on implicit namespace-package
discovery) so that ``from scripts.<module> import ...`` resolves to this
directory deterministically — even when other ``scripts/`` directories
on ``sys.path`` (notably ``wicked_zerg_challenger/scripts/`` which only
holds shell utilities) would otherwise win as namespace-package roots.
"""
