"""Test environment: temporary database, no background scheduler."""

import os
import tempfile
from pathlib import Path

os.environ["NETSHOW_DISABLE_SCHEDULER"] = "1"
os.environ.setdefault("NETSHOW_DB", str(Path(tempfile.mkdtemp(prefix="netshow-")) / "test.db"))
