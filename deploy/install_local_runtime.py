"""Install the reviewed localhost service and Google configuration in stub mode.

Does not change telecom credentials, signing key, sender, or public routing.
Creates the operator API secret only if none exists; never prints it.
"""
from pathlib import Path
import os
import argparse
import subprocess
import secrets
import tempfile


def atomic_write(path, content, mode):
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.text-back-')
    try:
        os.fchmod(fd,mode)
        with os.fdopen(fd,'w') as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--google-calendar-id',required=True)
    parser.add_argument('--restart',action='store_true')
    args=parser.parse_args()
    if '\n' in args.google_calendar_id or '\r' in args.google_calendar_id:
        raise SystemExit('Invalid calendar ID')
    home=Path.home()
    config=home/'.config/text_back'
    runtime=config/'runtime.env'
    content=runtime.read_text()
    values=dict(line.split('=',1) for line in content.splitlines() if '=' in line and not line.lstrip().startswith('#'))
    if values.get('TEXT_BACK_TELECOM_MODE','').strip().strip('\"\'')!='stub':
        raise SystemExit('Installer requires existing stub telecom mode')
    if values.get('TEXT_BACK_PUBLIC_BASE_URL','').strip().strip('\"\'')!='http://127.0.0.1:8000':
        raise SystemExit('Installer requires existing localhost endpoint')
    if not (config/'google_token.json').is_file():
        raise SystemExit('Google credential file missing')
    updates={'TEXT_BACK_CALENDAR_PROVIDER':'google',
        'TEXT_BACK_GOOGLE_CALENDAR_ID':args.google_calendar_id,
        'TEXT_BACK_GOOGLE_TOKEN_FILE':str(config/'google_token.json')}
    if not values.get('TEXT_BACK_OPERATOR_API_KEY','').strip():
        updates['TEXT_BACK_OPERATOR_API_KEY']=secrets.token_urlsafe(32)
    lines=[line for line in content.splitlines() if line.partition('=')[0] not in updates]
    lines += [key+'='+value for key,value in updates.items()]
    backup=config/'runtime.env.before-recovery'
    if not backup.exists():
        atomic_write(backup,content,0o600)
    atomic_write(runtime,'\n'.join(lines)+'\n',0o600)
    unit=home/'.config/systemd/user/text-back.service'
    old=unit.with_suffix('.service.before-recovery')
    if not old.exists():
        atomic_write(old,unit.read_text(),0o600)
    template=Path(__file__).parent/'systemd/text-back.service'
    atomic_write(unit,template.read_text(),0o644)
    if args.restart:
        subprocess.run(['systemctl','--user','daemon-reload'],check=True)
        subprocess.run(['systemctl','--user','restart','text-back.service'],check=True)
    print('Localhost unit and Google configuration installed; telecom remains stub; secrets preserved.')


if __name__=='__main__':
    main()
