"""The suite must never write to the application's real log files."""
import os

import config
from tools.ehr_tool import get_all_patients


def test_tool_calls_log_to_a_disposable_file():
    real = os.path.join(config.LOGS_DIR, "tool_logs.json")
    before = os.path.getsize(real) if os.path.exists(real) else None
    get_all_patients()  # logs a tool call
    after = os.path.getsize(real) if os.path.exists(real) else None
    assert before == after
    assert os.path.dirname(config.TOOL_LOGS_FILE) != config.LOGS_DIR
    assert os.path.dirname(config.AGENT_TRACES_FILE) != config.LOGS_DIR
