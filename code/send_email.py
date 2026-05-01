"""
SMTP-Versand fuer die POP-UP Routine.

Liest SMTP-Konfiguration aus .env und versendet die HTML+Text-Mail
als multipart/alternative.

Erwartete .env-Variablen:
    SMTP_SERVER          z.B. smtp.office365.com (FHNW), smtp.gmail.com
    SMTP_PORT            i.d.R. 587 (STARTTLS) oder 465 (SSL)
    SMTP_USER            Login-Username (oft = E-Mail-Adresse)
    SMTP_PASSWORD        Passwort oder App-Passwort
    SMTP_FROM            Absender-Adresse
    SMTP_TO              Empfaenger, mehrere durch Komma getrennt
    SMTP_USE_SSL         "true" fuer Port 465 SSL, sonst STARTTLS

Verwendung:
    python send_email.py <html_path> <text_path>
"""

from __future__ import annotations

import os
import smtplib
import ssl
import sys
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)


def send_mail(html_path: Path, text_path: Path) -> bool:
    server = os.environ.get("SMTP_SERVER", "").strip()
    port_str = os.environ.get("SMTP_PORT", "587").strip() or "587"
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    from_addr = os.environ.get("SMTP_FROM", "").strip() or user
    to_field = os.environ.get("SMTP_TO", "").strip()
    use_ssl = os.environ.get("SMTP_USE_SSL", "").strip().lower() in {"1", "true", "yes"}

    if not server or not to_field:
        print(
            "[FEHLER] SMTP_SERVER und SMTP_TO muessen in .env gesetzt sein.",
            file=sys.stderr,
        )
        return False

    try:
        port = int(port_str)
    except ValueError:
        print(f"[FEHLER] SMTP_PORT '{port_str}' ist keine Zahl.", file=sys.stderr)
        return False

    recipients = [r.strip() for r in to_field.split(",") if r.strip()]
    if not recipients:
        print("[FEHLER] SMTP_TO enthaelt keine Empfaenger.", file=sys.stderr)
        return False

    html_body = html_path.read_text(encoding="utf-8")
    text_body = text_path.read_text(encoding="utf-8")

    msg = EmailMessage()
    msg["Subject"] = f"POP-UP Routine — Neue FHNW-Events ({date.today().isoformat()})"
    msg["From"] = from_addr
    msg["To"] = ", ".join(recipients)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    print(
        f"[*] Sende Mail: server={server}:{port} ssl={use_ssl} from={from_addr} -> {recipients}",
        file=sys.stderr,
    )

    try:
        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, port, context=context, timeout=30) as smtp:
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg, from_addr=from_addr, to_addrs=recipients)
        else:
            with smtplib.SMTP(server, port, timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg, from_addr=from_addr, to_addrs=recipients)
    except smtplib.SMTPAuthenticationError as e:
        print(f"[FEHLER] SMTP-Authentifizierung fehlgeschlagen: {e}", file=sys.stderr)
        return False
    except smtplib.SMTPException as e:
        print(f"[FEHLER] SMTP-Fehler: {e}", file=sys.stderr)
        return False
    except OSError as e:
        print(f"[FEHLER] Netzwerk-/Verbindungsfehler: {e}", file=sys.stderr)
        return False

    print("[+] Mail erfolgreich versendet.", file=sys.stderr)
    return True


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: python send_email.py <html_path> <text_path>", file=sys.stderr)
        return 1
    ok = send_mail(Path(argv[1]), Path(argv[2]))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
