"""Read-only provider checks; never sends SMS, creates events, or edits routing.

OAuth access-token refresh may atomically update the supplied credential file.
Prints readiness flags only, never credentials, messages, or phone numbers.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shlex
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from text_back.calendars.credentials import GoogleCredentials
from text_back.calendars.google import GoogleCalendarProvider
from text_back.calendars.transport import urllib_transport
from text_back.config import load_config


def load_env(path):
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or not key.strip().startswith('TEXT_BACK_'):
            continue
        parts=shlex.split(value,comments=True)
        os.environ[key.strip()]=parts[0] if parts else ''


def signalwire_details(config):
    """Read owned-number and project metadata; emit only selected safe fields."""
    report = {}
    base = config.signalwire_space_url.rstrip('/')
    with httpx.Client(timeout=15, follow_redirects=False,
                      auth=(config.signalwire_project_id, config.signalwire_api_token)) as client:
        response = client.get(base+'/api/relay/rest/phone_numbers',
                              params={'filter_number': config.signalwire_from_number})
        report['signalwire_number_details_http_status'] = response.status_code
        if response.is_success:
            number = next((n for n in response.json().get('data', [])
                           if n.get('number') == config.signalwire_from_number), None)
            if number:
                report['signalwire_number_type'] = number.get('number_type')
                report['signalwire_number_capabilities'] = number.get('capabilities', [])
        response = client.get(base+'/api/projects/'+config.signalwire_project_id)
        report['signalwire_project_http_status'] = response.status_code
        if response.is_success:
            project = response.json()
            report['signalwire_signing_key_matches'] = (
                project['signing_key'] == config.webhook_secret
                if project.get('signing_key') else 'not_exposed')
            report['signalwire_trial_status'] = project.get('is_trial', 'not_exposed')
        response = client.get(base+'/api/relay/rest/registry/beta/brands')
        report['signalwire_brands_http_status'] = response.status_code
        if response.is_success:
            data = response.json()
            report['signalwire_brand_states'] = [b.get('state') for b in data.get('data', [])]
            report['signalwire_brands_more_pages'] = bool(data.get('links', {}).get('next'))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',action='append',default=[])
    parser.add_argument('--providers',action='store_true')
    parser.add_argument('--health',action='store_true')
    parser.add_argument('--google-token-file')
    parser.add_argument('--google-calendar-id')
    args=parser.parse_args()
    for path in args.env_file:
        load_env(path)
    config=load_config()
    report={'telecom_mode':config.telecom_mode, 'calendar_provider':config.calendar_provider,
        'persistent_database':config.db_path!=':memory:',
        'public_https':config.public_base_url.startswith('https://'),
        'operator_delivery_configured':config.handoff_delivery_channel!='disabled',
        'operator_api_configured':bool(config.operator_api_key),
        'real_phone_pilot':'not_verified'}
    if args.health:
        try:
            with httpx.Client(timeout=5,trust_env=False) as client:
                health=client.get('http://127.0.0.1:8000/health')
            health.raise_for_status()
            payload=health.json()
            report['runtime_health']={key:payload.get(key) for key in (
                'status','telecom','calendar','calendar_credentials','worker_running','worker_errors',
                'worker_last_run','persistent_database','sms_queue','inbound_dead_letters')}
        except Exception as exc:
            report['runtime_health_error']=type(exc).__name__
    if args.providers:
        token_path=args.google_token_file or config.google_token_file
        calendar_id=args.google_calendar_id or config.google_calendar_id
        if token_path and not calendar_id:
            # The authorized-user account field is read privately, never emitted.
            try:
                calendar_id=json.loads(Path(token_path).read_text()).get('account','')
            except (OSError,ValueError):
                pass
        if token_path and calendar_id:
            try:
                credentials=GoogleCredentials(token_path,client_file=config.google_client_file)
                calendar=GoogleCalendarProvider(calendar_id,credentials,urllib_transport)
                now=datetime.now(timezone.utc)
                calendar.is_free(now,now+timedelta(minutes=5))
                report['google_access']='verified'
                report['google_credentials']=credentials.status()
            except Exception as exc:
                report['google_access']='failed'
                report['google_error_type']=type(exc).__name__
                try:
                    report['google_credentials']=credentials.status()
                except Exception:
                    report['google_credentials']='unavailable'
        else:
            report['google_access']='configuration_missing'
        if config.signalwire_space_url and config.signalwire_project_id and config.signalwire_api_token:
            try:
                url=f'{config.signalwire_space_url.rstrip("/")}/api/laml/2010-04-01/Accounts/{config.signalwire_project_id}/IncomingPhoneNumbers'
                with httpx.Client(timeout=15,follow_redirects=False) as client:
                    response=client.get(url,auth=(config.signalwire_project_id,config.signalwire_api_token),params={'PhoneNumber':config.signalwire_from_number})
                report['signalwire_http_status']=response.status_code
                if response.is_success:
                    numbers=response.json().get('incoming_phone_numbers',[])
                    number=next((n for n in numbers if n.get('phone_number')==config.signalwire_from_number),None)
                    report['signalwire_number_found']=number is not None
                    if number:
                        report['voice_handler_attached']=bool(number.get('voice_url') or number.get('voice_application_sid'))
                        report['sms_handler_attached']=bool(number.get('sms_url') or number.get('sms_application_sid'))
                        report['voice_handler_matches']=number.get('voice_url')==config.public_base_url.rstrip('/')+'/webhooks/voice'
                        report['sms_handler_matches']=number.get('sms_url')==config.public_base_url.rstrip('/')+'/webhooks/sms'
                        report['number_verification_status']=number.get('verification_status','not_exposed')
                report.update(signalwire_details(config))
            except Exception as exc:
                report['signalwire_error_type']=type(exc).__name__
        else:
            report['signalwire_access']='configuration_missing'
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0


if __name__=='__main__':
    sys.exit(main())
