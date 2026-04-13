"""Allow running the converter as ``python -m energy_wallet.dspm_converter``."""

from .cli import main

raise SystemExit(main())
