#!/usr/bin/env python3
"""
Bridge MQTT ⇆ TinyTuya (slug topic, cache, thread-per-device)

Compatibile con TinyTuya ufficiale ≥1.7:
 - usa set_dps_multiple(); se non presente, fallback a set_value()
 - payload '...' o "..." decapsulato automaticamente
"""

import json, time, logging, threading, unicodedata, re
from pathlib import Path
from typing import Dict, Any
import tinytuya
import paho.mqtt.client as mqtt

# === CONFIG =============================================================
DEVICES_FILE       = Path("devices.json")
MQTT_BROKER        = "localhost"
MQTT_PORT          = 1883
MQTT_BASE_TOPIC    = "tuya"

POLL_INTERVAL_SEC  = 1
FORCE_REFRESH_SEC  = 60
LOG_LEVEL          = logging.INFO
TINYTUYA_DEBUG     = False
# ========================================================================

# ---------- Logger ------------------------------------------------------
log = logging.getLogger("tuya_mqtt_bridge")
log.setLevel(LOG_LEVEL)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
log.addHandler(sh)

if TINYTUYA_DEBUG:
    tinytuya.set_debug(True)

# ---------- Helpers -----------------------------------------------------
def slugify(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9_-]+", "_", t.strip())
    return t.lower().strip("_")

def clean_payload(raw: bytes) -> str:
    """Toglie eventuali apici esterni dal JSON."""
    s = raw.decode(errors="replace").strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    return s

# ---------- Carica dispositivi -----------------------------------------
with DEVICES_FILE.open(encoding="utf-8") as f:
    cfg_list: list[Dict[str, Any]] = json.load(f)

slug_to_id, id_to_slug, tt_devices = {}, {}, {}
for cfg in cfg_list:
    slug = slugify(cfg["name"])
    if slug in slug_to_id:
        log.error(f"Slug duplicato '{slug}'. Skippato.")
        continue
    dev = tinytuya.Device(cfg["id"], cfg["ip"], cfg["key"])
    dev.set_version(cfg.get("version", "3.3"))
    dev.set_socketTimeout(2)
    dev.set_socketRetryLimit(1)
    dev.set_socketRetryDelay(0.3)
    slug_to_id[slug], id_to_slug[cfg["id"]] = cfg["id"], slug
    tt_devices[cfg["id"]] = dev
log.info(f"Device caricati: {len(tt_devices)}")

# ---------- MQTT setup --------------------------------------------------
client = mqtt.Client()

def t_status(slug): return f"{MQTT_BASE_TOPIC}/{slug}/status"
def t_cmd(slug):    return f"{MQTT_BASE_TOPIC}/{slug}/set"

def on_connect(cl, *_):
    log.info(f"MQTT connesso a {MQTT_BROKER}:{MQTT_PORT}")
    for slug in slug_to_id:
        cl.subscribe(t_cmd(slug))
        log.info(f"[SUB] {t_cmd(slug)}")

def on_message(cl, userdata, msg):
    log.info(f"[RAW] {msg.topic} -> {msg.payload.decode(errors='replace')}")
    slug = msg.topic.split("/")[1]
    dev_id = slug_to_id.get(slug)
    if not dev_id:
        log.warning(f"Slug sconosciuto {slug}")
        return
    try:
        dps_map = json.loads(clean_payload(msg.payload))
        dps_map = {int(k): v for k, v in dps_map.items()}
    except Exception as e:
        log.error(f"JSON non valido su {msg.topic}: {e}")
        return

    log.info(f"[CMD] {slug} <- {dps_map}")
    dev = tt_devices[dev_id]

    try:
        if hasattr(dev, "set_dps_multiple"):
            result = dev.set_dps_multiple(dps_map, nowait=False)
        else:                           # fallback one-by-one
            result = {d: dev.set_value(d, v, nowait=False) for d, v in dps_map.items()}
        log.info(f"[ACK] {slug} -> {result}")
    except Exception as e:
        log.error(f"Errore invio {slug}: {e}")

client.on_connect, client.on_message = on_connect, on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

# ---------- Thread polling ---------------------------------------------
class PollWorker(threading.Thread):
    def __init__(self, dev_id: str):
        super().__init__(daemon=True)
        self.dev, self.slug = tt_devices[dev_id], id_to_slug[dev_id]
        self._last_js, self._last_ts = "", 0.0

    def run(self):
        while True:
            t0 = time.time()
            try:
                st = self.dev.status()
                payload = json.dumps(st["dps"], separators=(",", ":"))
                now = time.time()
                if payload != self._last_js or now - self._last_ts >= FORCE_REFRESH_SEC:
                    client.publish(t_status(self.slug), payload, retain=True)
                    self._last_js, self._last_ts = payload, now
                    log.debug(f"[PUB] {self.slug} -> {payload}")
            except Exception as e:
                log.warning(f"{self.slug} offline? {e}")
            time.sleep(max(0, POLL_INTERVAL_SEC - (time.time() - t0)))

# ---------- Avvio -------------------------------------------------------
if __name__ == "__main__":
    log.info("== Topic disponibili ==")
    for slug in slug_to_id:
        log.info(f"[PUB] {t_status(slug)}")
        log.info(f"[SUB] {t_cmd(slug)}")
    log.info("================================")

    for dev_id in tt_devices:
        PollWorker(dev_id).start()

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log.info("Arresto bridge…")
        client.loop_stop()
        client.disconnect()
