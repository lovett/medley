"""Send an email when one of the application's systemd services failes."""

import email.mime.text
import subprocess
import sys

try:
    SERVICE = sys.argv[1]
    RECIPIENT = sys.argv[2]
except IndexError:
    print(
        "Did not receive service and recipient as arguments",
        file=sys.stderr
    )
    sys.exit(2)

JOURNAL_PROCESS = subprocess.run(
    ("/usr/bin/env", "journalctl", "-u", "medley", "--since", "-12 hours"),
    capture_output=True,
    text=True,
    check=True
)

MESSAGE = email.mime.text.MIMEText(JOURNAL_PROCESS.stdout)
MESSAGE["TO"] = RECIPIENT
MESSAGE["Subject"] = f"[medley] {SERVICE} failed"

subprocess.run(
    ("/usr/sbin/sendmail", "-t", "-oi"),
    input=MESSAGE.as_bytes(),
    check=True
)
