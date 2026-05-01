"""Quick test: pingt Anthropic API um zu pruefen ob der API-Key funktioniert."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import anthropic

# .env aus dem Projekt-Root laden
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
if not api_key or api_key.startswith("sk-ant-api03-HIER"):
    print("[FEHLER] ANTHROPIC_API_KEY nicht gesetzt oder noch Platzhalter.", file=sys.stderr)
    sys.exit(1)

client = anthropic.Anthropic(api_key=api_key)

print("[*] Sende Test-Request an Claude API...", file=sys.stderr)
try:
    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Sag in genau einem kurzen deutschen Satz: Hallo Mario, deine API-Verbindung funktioniert."}
        ],
    )
except anthropic.AuthenticationError as e:
    print(f"[FEHLER] API-Key ungueltig: {e}", file=sys.stderr)
    sys.exit(2)
except anthropic.APIStatusError as e:
    print(f"[FEHLER] API-Fehler {e.status_code}: {e.message}", file=sys.stderr)
    sys.exit(3)

# Antwort ausgeben
for block in msg.content:
    if block.type == "text":
        print(block.text)

# Token-Verbrauch ausgeben
usage = msg.usage
print(
    f"\n[Verbrauch] input={usage.input_tokens} output={usage.output_tokens} "
    f"-> ca. ${(usage.input_tokens * 5 + usage.output_tokens * 25) / 1_000_000:.6f}",
    file=sys.stderr,
)
