"""Test setup: isolated temp data folder and simulated-offline mode (deterministic, no network)."""
import os
import tempfile

os.environ["TD_DATA_DIR"] = tempfile.mkdtemp(prefix="td_test_")
os.environ["TD_FORCE_OFFLINE"] = "1"
