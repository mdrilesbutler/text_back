"""scripts/registration.py: staged 10DLC submission with refusals, redaction and dry runs."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

import httpx
import pytest

SPEC = importlib.util.spec_from_file_location(
    "registration", Path(__file__).resolve().parents[1] / "scripts" / "registration.py"
)
registration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registration)

ENV = {
    "TEXT_BACK_SIGNALWIRE_SPACE_URL": "https://example.signalwire.com",
    "TEXT_BACK_SIGNALWIRE_PROJECT_ID": "proj",
    "TEXT_BACK_SIGNALWIRE_API_TOKEN": "PTsecret",
    "TEXT_BACK_SIGNALWIRE_FROM_NUMBER": "+17045695600",
}
BRAND = {
    "name": "FluxWorks", "company_name": "FluxWorks, LLC", "contact_email": "o@example.com",
    "contact_phone": "+19805550000", "ein_issuing_country": "US", "legal_entity_type": "PRIVATE_PROFIT",
    "ein": "12-3456789", "company_address": "1 Private St, Charlotte, NC", "company_website": "https://example.com",
    "company_vertical": "TECHNOLOGY",
}
CAMPAIGN = {"name": "Recover", "sms_use_case": "LOW_VOLUME_MIXED", "sub_use_cases": ["CUSTOMER_CARE"], "description": "d",
            "sample1": "a", "sample2": "b", "message_flow": "f", "opt_out_message": "o", "help_message": "h",
            "number_pooling_required": False, "direct_lending": False, "embedded_link": True, "embedded_phone": False,
            "age_gated_content": False, "lead_generation": True, "terms_and_conditions": True}


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, json=None):
        self.calls.append((method, url, json))
        status, body = self.responses.pop(0)
        return httpx.Response(status, json=body, request=httpx.Request(method, url))


@pytest.fixture
def staged(tmp_path):
    (tmp_path / "brand-request.json").write_text(json.dumps(BRAND))
    (tmp_path / "campaign-request.json").write_text(json.dumps(CAMPAIGN))
    return tmp_path


def run(step, staged, client=None, *flags):
    out = io.StringIO()
    env = dict(ENV, TEXT_BACK_REGISTRATION_DIR=str(staged))
    code = registration.main([step, *flags], environ=env, client=client, out=out)
    return code, out.getvalue()


def test_settings_fall_back_to_runtime_env_file(tmp_path):
    env_file = tmp_path / "runtime.env"
    env_file.write_text("\n".join(f"{k}={v}" for k, v in ENV.items()) + "\n# comment\n")
    settings = registration.load_settings({"TEXT_BACK_RUNTIME_ENV": str(env_file)})
    assert settings["project_id"] == "proj" and settings["from_number"] == "+17045695600"
    with pytest.raises(registration.RegistrationError):
        registration.load_settings({"TEXT_BACK_RUNTIME_ENV": str(tmp_path / "missing.env")})


def test_brand_dry_run_redacts_ein_and_address_and_writes_nothing(staged):
    client = FakeClient([])
    code, out = run("brand", staged, client, "--dry-run")
    assert code == 0 and client.calls == []
    assert "DRY RUN POST https://example.signalwire.com/api/relay/rest/registry/beta/brands" in out
    assert "12-3456789" not in out and "Private St" not in out and '"ein": "<redacted>"' in out
    assert not (staged / "brand-response.json").exists()


def test_brand_requires_yes_then_saves_response_privately(staged):
    client = FakeClient([(200, {"data": []}), (201, {"id": "brand-1", "state": "pending", "ein": "12-3456789"})])
    code, out = run("brand", staged, client)
    assert code == 2 and "--yes" in out and client.calls == []
    code, out = run("brand", staged, client, "--yes")
    assert code == 0
    assert client.calls[0][:2] == ("GET", "https://example.signalwire.com/api/relay/rest/registry/beta/brands")
    method, url, body = client.calls[1]
    assert (method, url) == ("POST", "https://example.signalwire.com/api/relay/rest/registry/beta/brands")
    assert body == BRAND
    saved = staged / "brand-response.json"
    assert json.loads(saved.read_text())["id"] == "brand-1"
    assert oct(saved.stat().st_mode & 0o777) == "0o600"
    assert "12-3456789" not in out and "brand-1" in out


def test_brand_refuses_a_second_paid_submission(staged):
    (staged / "brand-response.json").write_text(json.dumps({"id": "brand-1"}))
    client = FakeClient([])
    code, out = run("brand", staged, client, "--yes")
    assert code == 2 and "already submitted" in out and client.calls == []


def test_campaign_needs_brand_and_injects_brand_id_into_body_and_path(staged):
    client = FakeClient([])
    code, out = run("campaign", staged, client, "--yes")
    assert code == 2 and "submit the brand first" in out
    (staged / "brand-response.json").write_text(json.dumps({"id": "brand-1", "state": "approved"}))
    client = FakeClient([(200, {"data": []}), (201, {"id": "camp-1", "state": "pending", "name": "Recover"})])
    code, out = run("campaign", staged, client, "--yes")
    assert code == 0
    assert client.calls[0][:2] == ("GET", "https://example.signalwire.com/api/relay/rest/registry/beta/brands/brand-1/campaigns")
    method, url, body = client.calls[1]
    assert (method, url) == ("POST", "https://example.signalwire.com/api/relay/rest/registry/beta/brands/brand-1/campaigns")
    assert body["brand_id"] == "brand-1" and body["sms_use_case"] == "LOW_VOLUME_MIXED"
    assert json.loads((staged / "campaign-response.json").read_text())["id"] == "camp-1"


def test_status_calls_use_saved_ids(staged):
    (staged / "brand-response.json").write_text(json.dumps({"id": "brand-1"}))
    (staged / "campaign-response.json").write_text(json.dumps({"id": "camp-1"}))
    client = FakeClient([(200, {"id": "brand-1", "state": "approved"})])
    assert run("brand-status", staged, client)[0] == 0
    assert client.calls[0][:2] == ("GET", "https://example.signalwire.com/api/relay/rest/registry/beta/brands/brand-1")
    client = FakeClient([(200, {"id": "camp-1", "state": "pending"})])
    code, out = run("campaign-status", staged, client)
    assert code == 0 and '"state": "pending"' in out
    assert client.calls[0][:2] == ("GET", "https://example.signalwire.com/api/relay/rest/registry/beta/campaigns/camp-1")


def test_assign_posts_the_from_number_once_and_numbers_reports_state(staged):
    (staged / "campaign-response.json").write_text(json.dumps({"id": "camp-1"}))
    client = FakeClient([(200, {"id": "order-1", "state": "pending"})])
    code, out = run("assign", staged, client)
    assert code == 2 and "--yes" in out
    code, out = run("assign", staged, client, "--yes")
    assert code == 0
    assert client.calls[0] == ("POST", "https://example.signalwire.com/api/relay/rest/registry/beta/campaigns/camp-1/orders",
                               {"phone_numbers": ["+17045695600"]})
    code, out = run("assign", staged, FakeClient([]), "--yes")
    assert code == 2 and "already placed" in out
    client = FakeClient([
        (200, {"id": "order-1", "state": "complete"}),
        (200, {"data": [{"state": "complete", "phone_number": {"number": "+17045695600"}}]}),
    ])
    code, out = run("numbers", staged, client)
    assert code == 0 and "+17045695600" in out and '"state": "complete"' in out
    assert client.calls[0][:2] == ("GET", "https://example.signalwire.com/api/relay/rest/registry/beta/orders/order-1")
    assert client.calls[1][:2] == ("GET", "https://example.signalwire.com/api/relay/rest/registry/beta/campaigns/camp-1/numbers")


def test_http_errors_are_reported_without_the_token_and_without_saving(staged):
    client = FakeClient([(200, {"data": []}), (422, {"errors": [{"detail": "ein invalid"}]})])
    code, out = run("brand", staged, client, "--yes")
    assert code == 2 and "HTTP 422" in out and "PTsecret" not in out
    assert not (staged / "brand-response.json").exists()


def test_paid_steps_adopt_a_record_the_registry_already_holds(staged):
    client = FakeClient([(200, {"data": [{"id": "brand-9", "state": "pending", "company_name": "FluxWorks, LLC"}]})])
    code, out = run("brand", staged, client, "--yes")
    assert code == 2 and "already exists" in out and "brand-9" in out
    assert [c[0] for c in client.calls] == ["GET"]
    assert json.loads((staged / "brand-response.json").read_text())["id"] == "brand-9"
    client = FakeClient([(200, {"data": [{"id": "camp-9", "state": "pending"}]})])
    code, out = run("campaign", staged, client, "--yes")
    assert code == 2 and "camp-9" in out and [c[0] for c in client.calls] == ["GET"]
    assert json.loads((staged / "campaign-response.json").read_text())["id"] == "camp-9"
