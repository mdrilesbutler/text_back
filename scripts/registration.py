"""Submit and track the staged 10DLC Brand/Campaign for the pilot number.

Reads the staged payloads under ~/.config/text_back/registration/ (never git) and
the SignalWire credentials from runtime.env. Paid submissions require ``--yes``;
``--dry-run`` prints the request without sending anything. Responses are saved
beside the payloads (mode 600) so the ids are never re-derived or re-submitted.
The EIN and street address are redacted from everything printed.

    python3 scripts/registration.py brand --dry-run        # show the brand request
    python3 scripts/registration.py brand --yes            # submit it ($4.50)
    python3 scripts/registration.py brand-status
    python3 scripts/registration.py campaign --yes         # needs brand-response.json
    python3 scripts/registration.py campaign-status
    python3 scripts/registration.py assign --yes           # assigns the FROM number
    python3 scripts/registration.py numbers                # assignment state per number
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

try:
    import httpx
except ModuleNotFoundError:  # system python3: re-run under the repo venv, which has httpx
    _VENV = Path(__file__).resolve().parents[1] / ".venv"
    _VENV_PYTHON = _VENV / "bin" / "python"
    if _VENV_PYTHON.is_file() and Path(sys.prefix).resolve() != _VENV.resolve():
        os.execv(str(_VENV_PYTHON), [str(_VENV_PYTHON), *sys.argv])
    raise

REDACTED_KEYS = {"ein", "company_address"}
BRAND_REQUEST = "brand-request.json"
BRAND_RESPONSE = "brand-response.json"
CAMPAIGN_REQUEST = "campaign-request.json"
CAMPAIGN_RESPONSE = "campaign-response.json"
ORDER_RESPONSE = "order-response.json"
REGISTRY = "/api/relay/rest/registry/beta"


class RegistrationError(Exception):
    """A refused or failed step; the message is safe to print."""


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_settings(environ: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if environ is None else environ)
    needed = (
        "TEXT_BACK_SIGNALWIRE_SPACE_URL",
        "TEXT_BACK_SIGNALWIRE_PROJECT_ID",
        "TEXT_BACK_SIGNALWIRE_API_TOKEN",
        "TEXT_BACK_SIGNALWIRE_FROM_NUMBER",
    )
    if not all(env.get(key) for key in needed):
        runtime_env = Path(env.get("TEXT_BACK_RUNTIME_ENV", "~/.config/text_back/runtime.env")).expanduser()
        for key, value in _parse_env_file(runtime_env).items():
            env.setdefault(key, value)
    missing = [key for key in needed if not env.get(key)]
    if missing:
        raise RegistrationError(f"missing settings: {', '.join(missing)}")
    return {
        "space_url": env["TEXT_BACK_SIGNALWIRE_SPACE_URL"].rstrip("/"),
        "project_id": env["TEXT_BACK_SIGNALWIRE_PROJECT_ID"],
        "api_token": env["TEXT_BACK_SIGNALWIRE_API_TOKEN"],
        "from_number": env["TEXT_BACK_SIGNALWIRE_FROM_NUMBER"],
        "registration_dir": str(Path(env.get("TEXT_BACK_REGISTRATION_DIR", "~/.config/text_back/registration")).expanduser()),
    }


def redact(value):
    if isinstance(value, dict):
        return {k: ("<redacted>" if k in REDACTED_KEYS else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def _read_json(path: Path, label: str) -> dict:
    if not path.is_file():
        raise RegistrationError(f"{label} not found at {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise RegistrationError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistrationError(f"{label} must be a JSON object")
    return data


def _saved_id(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    value = data.get("id") if isinstance(data, dict) else None
    return value if isinstance(value, str) and value else None


def _write_private(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


class Registry:
    def __init__(self, settings: dict[str, str], client: httpx.Client | None = None, dry_run: bool = False, out=None):
        self.settings = settings
        self.dir = Path(settings["registration_dir"])
        self.dry_run = dry_run
        self.out = out or sys.stdout
        self.client = client or httpx.Client(
            auth=(settings["project_id"], settings["api_token"]), timeout=30, trust_env=False
        )

    # -- transport -------------------------------------------------------
    def _url(self, path: str) -> str:
        return f"{self.settings['space_url']}{REGISTRY}{path}"

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = self._url(path)
        if self.dry_run:
            print(f"DRY RUN {method} {url}", file=self.out)
            if body is not None:
                print(json.dumps(redact(body), indent=2), file=self.out)
            return {}
        response = self.client.request(method, url, json=body)
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text[:500]}
        if response.status_code >= 400:
            raise RegistrationError(f"{method} {path} -> HTTP {response.status_code}: {json.dumps(redact(data))[:800]}")
        return data if isinstance(data, dict) else {"data": data}

    def _print(self, data: dict) -> None:
        print(json.dumps(redact(data), indent=2), file=self.out)

    def _adopt_existing(self, listing_path: str, response_path: Path, label: str, status_step: str) -> None:
        """Refuse a paid POST when the registry already holds a record for it.

        A transport error after a successful POST leaves no response file; the
        listing is the provider's truth, so adopt the first record and stop.
        """
        listing = self._request("GET", listing_path)
        records = [item for item in listing.get("data", []) if isinstance(item, dict) and item.get("id")]
        if records:
            _write_private(response_path, records[0])
            raise RegistrationError(
                f"{label} already exists in the registry (id {records[0]['id']}, state {records[0].get('state')}); "
                f"saved it to {response_path.name}, run {status_step} instead"
            )

    # -- steps -----------------------------------------------------------
    def brand(self, yes: bool) -> dict:
        response_path = self.dir / BRAND_RESPONSE
        existing = _saved_id(response_path)
        if existing and not self.dry_run:
            raise RegistrationError(f"brand already submitted (id {existing}); run brand-status instead")
        body = _read_json(self.dir / BRAND_REQUEST, "brand request")
        if not yes and not self.dry_run:
            raise RegistrationError("brand submission is a paid request (~$4.50); re-run with --yes to submit")
        if not self.dry_run:
            self._adopt_existing("/brands", response_path, "a brand", "brand-status")
        data = self._request("POST", "/brands", body)
        if not self.dry_run:
            _write_private(response_path, data)
            self._print(data)
        return data

    def brand_status(self) -> dict:
        brand_id = _saved_id(self.dir / BRAND_RESPONSE)
        if not brand_id:
            raise RegistrationError("no brand-response.json yet; submit the brand first")
        data = self._request("GET", f"/brands/{brand_id}")
        if not self.dry_run:
            self._print({k: data.get(k) for k in ("id", "state", "name", "company_vertical", "created_at", "updated_at")})
        return data

    def campaign(self, yes: bool) -> dict:
        brand_id = _saved_id(self.dir / BRAND_RESPONSE)
        if not brand_id:
            raise RegistrationError("no brand-response.json yet; submit the brand first")
        response_path = self.dir / CAMPAIGN_RESPONSE
        existing = _saved_id(response_path)
        if existing and not self.dry_run:
            raise RegistrationError(f"campaign already submitted (id {existing}); run campaign-status instead")
        body = dict(_read_json(self.dir / CAMPAIGN_REQUEST, "campaign request"))
        body["brand_id"] = brand_id
        if not yes and not self.dry_run:
            raise RegistrationError("campaign submission is a paid request (~$12 incl. 3 months); re-run with --yes to submit")
        if not self.dry_run:
            self._adopt_existing(f"/brands/{brand_id}/campaigns", response_path, "a campaign", "campaign-status")
        data = self._request("POST", f"/brands/{brand_id}/campaigns", body)
        if not self.dry_run:
            _write_private(response_path, data)
            self._print({k: data.get(k) for k in ("id", "state", "name", "sms_use_case", "created_at")})
        return data

    def campaign_status(self) -> dict:
        campaign_id = _saved_id(self.dir / CAMPAIGN_RESPONSE)
        if not campaign_id:
            raise RegistrationError("no campaign-response.json yet; submit the campaign first")
        data = self._request("GET", f"/campaigns/{campaign_id}")
        if not self.dry_run:
            self._print({k: data.get(k) for k in ("id", "state", "name", "sms_use_case", "updated_at")})
        return data

    def assign(self, yes: bool) -> dict:
        campaign_id = _saved_id(self.dir / CAMPAIGN_RESPONSE)
        if not campaign_id:
            raise RegistrationError("no campaign-response.json yet; submit the campaign first")
        response_path = self.dir / ORDER_RESPONSE
        existing = _saved_id(response_path)
        if existing and not self.dry_run:
            raise RegistrationError(f"number order already placed (id {existing}); run numbers instead")
        body = {"phone_numbers": [self.settings["from_number"]]}
        if not yes and not self.dry_run:
            raise RegistrationError("assigning the number changes live messaging routing; re-run with --yes")
        data = self._request("POST", f"/campaigns/{campaign_id}/orders", body)
        if not self.dry_run:
            _write_private(response_path, data)
            self._print(data)
        return data

    def numbers(self) -> dict:
        campaign_id = _saved_id(self.dir / CAMPAIGN_RESPONSE)
        if not campaign_id:
            raise RegistrationError("no campaign-response.json yet; submit the campaign first")
        order_id = _saved_id(self.dir / ORDER_RESPONSE)
        result: dict = {}
        if order_id:
            order = self._request("GET", f"/orders/{order_id}")
            result["order"] = {k: order.get(k) for k in ("id", "state", "processed_at", "updated_at")}
        listing = self._request("GET", f"/campaigns/{campaign_id}/numbers")
        result["assignments"] = [
            {"number": (item.get("phone_number") or {}).get("number"), "state": item.get("state"), "updated_at": item.get("updated_at")}
            for item in listing.get("data", [])
            if isinstance(item, dict)
        ]
        if not self.dry_run:
            self._print(result)
        return result


def main(argv: list[str] | None = None, environ: dict[str, str] | None = None, client: httpx.Client | None = None, out=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=["brand", "brand-status", "campaign", "campaign-status", "assign", "numbers"])
    parser.add_argument("--yes", action="store_true", help="confirm a paid or routing-changing submission")
    parser.add_argument("--dry-run", action="store_true", help="print the request; send nothing, write nothing")
    args = parser.parse_args(argv)
    out = out or sys.stdout
    try:
        registry = Registry(load_settings(environ), client=client, dry_run=args.dry_run, out=out)
        action = {
            "brand": lambda: registry.brand(args.yes),
            "brand-status": registry.brand_status,
            "campaign": lambda: registry.campaign(args.yes),
            "campaign-status": registry.campaign_status,
            "assign": lambda: registry.assign(args.yes),
            "numbers": registry.numbers,
        }[args.step]
        action()
    except RegistrationError as exc:
        print(f"registration: {exc}", file=out)
        return 2
    except httpx.HTTPError as exc:
        print(f"registration: network error: {exc.__class__.__name__}", file=out)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
