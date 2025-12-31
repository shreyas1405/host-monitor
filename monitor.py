from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
from typing import Literal, List, Optional

import csv
from datetime import datetime
from collections import deque
from pathlib import Path
import os

from flask import Flask, render_template_string
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from icmplib import ping
import yaml


CheckType = Literal["ping", "tcp"]


@dataclass
class Target:
    name: str
    host: str
    type: CheckType
    port: Optional[int] = None

    status: str = field(default="UNKNOWN")  # UP/DOWN/UNKNOWN
    last_rtt_ms: Optional[float] = field(default=None)
    last_checked: Optional[float] = field(default=None)
    last_error: Optional[str] = field(default=None)
    history: deque[str] = field(default_factory=lambda: deque(maxlen=100))


CONFIG_PATH = Path("targets.yaml")
LOG_PATH = Path("logs") / "status_log.csv"


def load_targets() -> List[Target]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    targets_conf = data.get("targets", [])
    targets: List[Target] = []
    for entry in targets_conf:
        targets.append(
            Target(
                name=entry["name"],
                host=str(entry["host"]),
                type=entry["type"],
                port=entry.get("port"),
            )
        )
    return targets


TARGETS: List[Target] = load_targets()


def log_result(target: Target) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_new = not LOG_PATH.exists()
    with LOG_PATH.open(mode="a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(
                [
                    "timestamp",
                    "name",
                    "host",
                    "type",
                    "port",
                    "status",
                    "rtt_ms",
                    "error",
                ]
            )
        writer.writerow(
            [
                datetime.utcnow().isoformat(),
                target.name,
                target.host,
                target.type,
                target.port or "",
                target.status,
                f"{target.last_rtt_ms:.3f}"
                if target.last_rtt_ms is not None
                else "",
                target.last_error or "",
            ]
        )


def check_ping(target: Target, count: int = 1, timeout: float = 1.0) -> None:
    prev_status = target.status
    try:
        result = ping(
            target.host,
            count=count,
            timeout=timeout,
            interval=0.2,
            privileged=False,
        )
        target.status = "UP" if result.packet_loss < 1.0 else "DOWN"
        target.last_rtt_ms = result.avg_rtt
        target.last_error = None
        target.history.append(target.status)
    except Exception as e:
        target.status = "DOWN"
        target.last_rtt_ms = None
        target.last_error = str(e)
        target.history.append(target.status)
    finally:
        target.last_checked = time.time()
        log_result(target)


def check_tcp(target: Target, timeout: float = 1.0) -> None:
    prev_status = target.status

    if target.port is None:
        target.status = "DOWN"
        target.last_error = "TCP check requires port"
        target.last_checked = time.time()
        target.history.append(target.status)
        log_result(target)
        return

    start = time.perf_counter_ns()
    try:
        with socket.create_connection((target.host, target.port), timeout=timeout):
            end = time.perf_counter_ns()
            target.status = "UP"
            target.last_rtt_ms = (end - start) / 1e6
            target.last_error = None
            target.history.append(target.status)
    except Exception as e:
        target.status = "DOWN"
        target.last_rtt_ms = None
        target.last_error = str(e)
        target.history.append(target.status)
    finally:
        target.last_checked = time.time()
        log_result(target)


def run_one_cycle() -> None:
    for t in TARGETS:
        if t.type == "ping":
            check_ping(t)
        elif t.type == "tcp":
            check_tcp(t)


def uptime_percent(target: Target) -> float:
    if not target.history:
        return 0.0
    up = sum(1 for s in target.history if s == "UP")
    return (up / len(target.history)) * 100.0


app = Flask(__name__)

# ---------- Basic Auth setup ----------

auth = HTTPBasicAuth()

# Change this to your own username/password
users = {
    "admin": generate_password_hash("ChangeThisPassword")
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

# ---------- HTML Template with Bootstrap ----------

TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Host & Service Monitor</title>
    <meta http-equiv="refresh" content="10">

    <!-- Bootstrap CSS -->
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/css/bootstrap.min.css"
      integrity="sha384-GTVjCwVYxZ1dQc5sKXc5teLoI0lp4rWuIwoMvVJE9idh+NROGy4nQJ5c8NyEJD7B"
      crossorigin="anonymous"
    />

    <style>
      body { padding-top: 20px; }
      .status-pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        color: #fff;
      }
      .status-up { background-color: #28a745; }
      .status-down { background-color: #dc3545; }
      .status-unknown { background-color: #6c757d; }
      .small-text { font-size: 0.8rem; color: #666; }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h1 class="h3 mb-0">Host & Service Monitor</h1>
          <p class="small-text mb-0">Auto-refreshes every 10 seconds.</p>
        </div>
        <div class="text-right small-text">
          <div>Total targets: {{ targets|length }}</div>
        </div>
      </div>

      <div class="table-responsive">
        <table class="table table-hover table-sm">
          <thead class="thead-light">
            <tr>
              <th>Name</th>
              <th>Host</th>
              <th>Type</th>
              <th>Port</th>
              <th>Status</th>
              <th>RTT (ms)</th>
              <th>Uptime (%)</th>
              <th>Last Checked (epoch)</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {% for t in targets %}
            <tr
              class="
                {% if t.status == 'UP' %}table-success
                {% elif t.status == 'DOWN' %}table-danger
                {% else %}table-secondary
                {% endif %}
              "
            >
              <td>{{ t.name }}</td>
              <td><code>{{ t.host }}</code></td>
              <td>{{ t.type }}</td>
              <td>{{ t.port if t.port else '-' }}</td>
              <td>
                {% if t.status == 'UP' %}
                  <span class="status-pill status-up">UP</span>
                {% elif t.status == 'DOWN' %}
                  <span class="status-pill status-down">DOWN</span>
                {% else %}
                  <span class="status-pill status-unknown">UNKNOWN</span>
                {% endif %}
              </td>
              <td>{{ '%.2f'|format(t.last_rtt_ms) if t.last_rtt_ms is not none else '-' }}</td>
              <td>{{ '%.1f'|format(uptime_percent(t)) }}</td>
              <td>
                {% if t.last_checked %}
                  {{ t.last_checked | int }}
                {% else %}
                  -
                {% endif %}
              </td>
              <td>{{ t.last_error if t.last_error else '-' }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Optional Bootstrap JS -->
    <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"
            integrity="sha384-DfXdXrZBOqVakiobP6KyHR+Y6z3Y0JVpaz6RtZpmjHtkobaN6D+PfYZ7R6pujISi"
            crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/js/bootstrap.bundle.min.js"
            integrity="sha384-Fy6S3B9q64WdZWQUiU+q4/2LcT9gC1XwjlzAIXazhbugzuDUFcPRl1bQY70dNDO7"
            crossorigin="anonymous"></script>
  </body>
</html>
"""


@app.route("/")
@auth.login_required
def index():
    run_one_cycle()
    return render_template_string(TEMPLATE, targets=TARGETS, uptime_percent=uptime_percent)


def print_status():
    print(f"{'Name':<20}{'Host':<16}{'Type':<6}{'Status':<8}{'RTT (ms)':<10}")
    print("-" * 70)
    for t in TARGETS:
        rtt = f"{t.last_rtt_ms:.2f}" if t.last_rtt_ms is not None else "-"
        print(f"{t.name:<20}{t.host:<16}{t.type:<6}{t.status:<8}{rtt:<10}")


def main():
    run_one_cycle()
    print_status()


if __name__ == "__main__":
    main()
