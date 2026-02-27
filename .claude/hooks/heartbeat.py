#!/usr/bin/env python3
"""Notification hook: write heartbeat timestamps for running team agents.

If a .shutdown signal file is detected for any agent, outputs a JSON message
telling the agent to wrap up gracefully.
"""

import glob
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _osc_utils import DIR_OSC, find_repo_root, read_hook_input


def main():
    hook_input = read_hook_input()

    if hook_input.get("hook_event_name") != "Notification":
        print(json.dumps({}))
        return

    repo = find_repo_root()
    if not repo:
        print(json.dumps({}))
        return

    teams_dir = os.path.join(str(repo), DIR_OSC, "teams")
    if not os.path.isdir(teams_dir):
        print(json.dumps({}))
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    shutdown_messages = []

    for team_json_path in glob.glob(os.path.join(teams_dir, "*", "team.json")):
        try:
            with open(team_json_path) as f:
                team = json.load(f)
        except Exception:
            continue

        if team.get("status") != "running":
            continue

        team_dir = os.path.dirname(team_json_path)
        agents_dir = os.path.join(team_dir, "agents")
        if not os.path.isdir(agents_dir):
            continue

        for agent_file in glob.glob(os.path.join(agents_dir, "*.json")):
            try:
                with open(agent_file) as f:
                    agent = json.load(f)
            except Exception:
                continue

            if agent.get("status") != "running":
                continue

            name = os.path.splitext(os.path.basename(agent_file))[0]

            # Write heartbeat
            hb_path = os.path.join(agents_dir, f"{name}.heartbeat")
            try:
                with open(hb_path, "w") as f:
                    f.write(now + "\n")
            except Exception:
                pass

            # Check shutdown signal
            shutdown_path = os.path.join(agents_dir, f"{name}.shutdown")
            if os.path.exists(shutdown_path):
                shutdown_messages.append(
                    f"Agent '{name}' has a shutdown signal. Please wrap up current work and exit gracefully."
                )

    if shutdown_messages:
        print(json.dumps({"message": " ".join(shutdown_messages)}))
    else:
        print(json.dumps({}))

    # Output success marker to stderr
    sys.stderr.write("Notification:heartbeat hook success\n")
    sys.stderr.flush()


if __name__ == "__main__":
    main()
