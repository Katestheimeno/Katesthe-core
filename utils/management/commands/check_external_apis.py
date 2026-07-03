"""
Management command: generic health-check scaffold for external API dependencies.

Probes each registered service endpoint directly (no DB side effects) and
reports configuration status, HTTP response code, latency, and response
shape. Ships with an EMPTY `SERVICES` registry — this is a CI-friendly
template, not a set of domain probes. Register a probe by adding an entry
to `SERVICES` (see the comment above its declaration below).

Usage:
  manage.py check_external_apis                   # all registered services
  manage.py check_external_apis --service my_api   # a single service
  manage.py check_external_apis --verbose          # show response bodies
  manage.py check_external_apis --timeout 10       # override timeout
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

# SERVICES maps a service key to a probe callable, e.g.:
#   SERVICES = {"my_api": _probe_my_api}
# where a probe callable has signature (timeout: int, verbose: bool) -> list[ProbeResult].
# Ships EMPTY — projects register their own probes.
SERVICES: Dict[str, Callable[[int, bool], "List[ProbeResult]"]] = {}


class ProbeStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    MOCK = "MOCK"


@dataclass
class ProbeResult:
    service: str
    endpoint: str
    status: ProbeStatus
    duration_ms: float = 0.0
    http_status: Optional[int] = None
    response_preview: str = ""
    error_message: str = ""
    warnings: list = field(default_factory=list)


@dataclass
class ConfigCheck:
    service: str
    base_url: str = ""
    base_url_ok: bool = False
    api_key_ok: bool = False
    enabled: bool = False
    flag_name: str = ""
    warnings: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _build_headers(api_key: str) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def _run_timed(make_request, timeout: int):
    """Run `make_request()` and time it. Returns (response_or_none, duration_ms, error_str)."""
    t0 = time.perf_counter()
    try:
        resp = make_request()
        return resp, (time.perf_counter() - t0) * 1000, ""
    except requests.exceptions.Timeout:
        return None, (time.perf_counter() - t0) * 1000, f"Timeout after {timeout}s"
    except requests.exceptions.ConnectionError as e:
        return None, (time.perf_counter() - t0) * 1000, f"Connection error: {e}"
    except Exception as e:
        return None, (time.perf_counter() - t0) * 1000, str(e)


def _timed_post(url: str, payload: dict, headers: dict, timeout: int):
    """POST with timing. Returns (response_or_none, duration_ms, error_str)."""
    return _run_timed(
        lambda: requests.post(url, json=payload, headers=headers, timeout=timeout),
        timeout,
    )


def _timed_get(url: str, headers: dict, timeout: int):
    """GET with timing. Returns (response_or_none, duration_ms, error_str)."""
    return _run_timed(
        lambda: requests.get(url, headers=headers, timeout=timeout),
        timeout,
    )


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Health-check registered external API integrations. "
        "Ships with an empty registry — see module docstring to add probes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--service",
            type=str,
            choices=list(SERVICES) + ["all"],
            default="all",
            help="Which service to check (default: all).",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show response bodies and extra detail.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=10,
            help="HTTP timeout in seconds (default: 10).",
        )

    def handle(self, *args, **options):
        verbose = options["verbose"]
        timeout = options["timeout"]
        services = list(SERVICES) if options["service"] == "all" else [options["service"]]

        self._print_banner()

        if not services:
            self.stdout.write(self.style.WARNING(
                "No services registered — nothing to probe. "
                "See the module docstring to register a probe."
            ))
            return

        self._print_config_section(self._run_config_checks(services))
        probe_results = self._run_probes(services, timeout, verbose)
        has_failure = self._print_results_section(probe_results, verbose)

        if has_failure:
            sys.exit(1)

    def _run_config_checks(self, services: List[str]) -> List[ConfigCheck]:
        # Ships empty — no domain-specific config to check. Projects that
        # register probes may extend this to build a ConfigCheck per service.
        return []

    def _run_probes(self, services: List[str], timeout: int, verbose: bool) -> List[ProbeResult]:
        all_results: Dict[str, List[ProbeResult]] = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(SERVICES[svc], timeout, verbose): svc for svc in services}
            for future in as_completed(futures):
                svc = futures[future]
                try:
                    all_results[svc] = future.result()
                except Exception as e:
                    all_results[svc] = [ProbeResult(
                        service=svc, endpoint="*", status=ProbeStatus.FAIL,
                        error_message=f"Probe crashed: {e}",
                    )]
        ordered: List[ProbeResult] = []
        for svc in services:
            ordered.extend(all_results.get(svc, []))
        return ordered

    # ------------------------------------------------------------------
    # Output formatting
    # ------------------------------------------------------------------

    def _print_banner(self):
        project_name = getattr(settings, "PROJECT_NAME", "Project")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS(f"  {project_name} External API Health Check"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")

    def _print_config_section(self, checks: List[ConfigCheck]):
        if not checks:
            return
        self.stdout.write(self.style.WARNING("[CONFIG] Checking credentials and configuration..."))
        for c in checks:
            self.stdout.write(f"  {c.service}:")
            for label, ok, extra in (
                ("Base URL", c.base_url_ok, c.base_url),
                ("API Key", c.api_key_ok, "configured"),
                ("Enabled", c.enabled, f"{c.flag_name}={c.enabled}"),
            ):
                mark = self.style.SUCCESS("Y") if ok else self.style.ERROR("N")
                self.stdout.write(f"    {label + ':':<10} {extra:<40} [{mark}]")
            for w in c.warnings:
                self.stdout.write(self.style.WARNING(f"    ! {w}"))
        self.stdout.write("")

    def _print_results_section(self, results: List[ProbeResult], verbose: bool) -> bool:
        self.stdout.write(self.style.WARNING("[PROBES] Testing endpoints..."))
        self.stdout.write("")

        has_failure = False
        current_service = None
        for r in results:
            if r.service != current_service:
                current_service = r.service
                self.stdout.write(f"  {current_service}")

            status_str = self._format_status(r.status)
            timing = f"{r.duration_ms / 1000:.2f}s" if r.duration_ms > 0 else "  -  "
            http = f"HTTP {r.http_status}" if r.http_status else ""
            self.stdout.write(f"    {r.endpoint} {status_str}  ({timing})  {http}")

            has_failure = has_failure or r.status == ProbeStatus.FAIL
            if r.error_message:
                for line in r.error_message.splitlines():
                    self.stdout.write(self.style.ERROR(f"      {line}"))
            for w in r.warnings:
                self.stdout.write(self.style.WARNING(f"      ! {w}"))
            if verbose and r.response_preview:
                self.stdout.write(f"      Response: {r.response_preview[:300]}")
            self.stdout.write("")

        overall = self.style.ERROR("FAIL") if has_failure else self.style.SUCCESS("OK")
        self.stdout.write(f"  Overall: {overall}")
        self.stdout.write("")
        return has_failure

    def _format_status(self, status: ProbeStatus) -> str:
        if status == ProbeStatus.PASS:
            return self.style.SUCCESS("PASS")
        elif status == ProbeStatus.FAIL:
            return self.style.ERROR("FAIL")
        elif status == ProbeStatus.MOCK:
            return self.style.WARNING("MOCK")
        return self.style.WARNING("SKIP")
