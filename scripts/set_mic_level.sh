#!/usr/bin/env bash
# Re-apply the tuned capture levels for the wired mic on the ALC897 (card 2).
# ALSA mixer state resets on reboot; run this after a reboot if the mic is too
# hot (clipping) again. Tuned 2026-06-21: input was clipping at +30dB capture
# +20dB rear-mic boost; these values give a clean speaking level for Whisper.
#
#   bash scripts/set_mic_level.sh
#
# Discover your card number with `arecord -l` if it is not card 2.
set -euo pipefail

CARD="${1:-2}"

amixer -c "$CARD" sset 'Input Source' 'Rear Mic' >/dev/null   # pink jack
amixer -c "$CARD" sset 'Rear Mic Boost' 0 >/dev/null          # no analog boost
amixer -c "$CARD" sset 'Front Mic Boost' 0 >/dev/null
amixer -c "$CARD" sset 'Capture' 12 >/dev/null                # ~19% (-8.25 dB)

echo "Mic capture tuned on card $CARD (Rear Mic, boost off, capture ~19%)."
echo "Verify with:  python mic_check.py"
