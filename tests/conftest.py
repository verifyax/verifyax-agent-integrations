"""Put the scripts/ dir on sys.path so tests can import verifyax_transforms."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
