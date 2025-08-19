

# 🏠 Tuya MQTT Bridge

Bridge leggero *local only* che:
- interroga i dispositivi **Tuya SmartLife** in LAN via TinyTuya
- espone/storicizza lo stato su **MQTT**
- riceve comandi MQTT e li inoltra ai device

> No cloud Tuya, zero polling dal web 👋

---

## ✨ Caratteristiche

| Funzione | Dettagli |
|----------|----------|
| **Topic by name** | `/tuya/<slug>/status` e `/tuya/<slug>/set` |
| **Cache anti-spam** | pubblica solo se lo stato cambia o ogni 60 s |
| **Thread-per-device** | un lockout non blocca gli altri |
| **Compatibilità** | TinyTuya ≥ 1.17 (`set_dps_multiple`) + fallback |
| **Log** | `[RAW]`, `[CMD]`, `[ACK]` a livello INFO |

---

## ⚡ Requisiti

* Python 3.8+
* Un broker MQTT (Mosquitto, EMQX, ecc.) in LAN
* Dispositivi Tuya “pairati” sull’app, con **ID** e **KEY** estratti

---

## 🛠️ Installazione

```bash
git clone https://github.com/il-prof-f-a/tuya_mqtt_simple_bridge.git
cd tuya_mqtt_simple_bridge
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 🔧 Configurazione
Modificare nell'intestazione dello script i parametri di connessione al server MQTT:

    # === CONFIG =============================================================
    DEVICES_FILE       = Path("devices.json")
    MQTT_BROKER        = "192.168.0.1"
    MQTT_PORT          = 1883
    MQTT_BASE_TOPIC    = "tuya"
    
    POLL_INTERVAL_SEC  = 1
    FORCE_REFRESH_SEC  = 60
    LOG_LEVEL          = logging.INFO
    TINYTUYA_DEBUG     = False
    # ========================================================================

### Recupero **ID**, **LocalKey** e file **devices.json**

Prima di tutto devi estrarre l’`id` e la `key` locale di ciascun dispositivo Tuya.  
Segui l’ottima guida ufficiale di TinyTuya:

▶️ **Setup Wizard – Getting Local Keys**  
<https://github.com/jasonacox/tinytuya#setup-wizard---getting-local-keys>

Il wizard genera automaticamente (o ti fornisce i dati per compilare) il file `devices.json` **che dovrà essere aggiunto alla root dello script**.

---

## Esempio di `devices.json`

```json
[
  {
    "name": "Pulsante Per Tapparella (Wi-Fi BLE)",
    "id":   "-----------------",
    "key":  "-----------------",
    "ip":   "192.168.0.2",
    "version": "3.3",
	.
	.
	.
	.
  }
]
```

## 🔍 Test rapidi

### 1. Invia un comando (`mosquitto_pub`)

```bash
mosquitto_pub -h 192.168.0.1 \
  -t 'tuya/pulsante_per_tapparella_wi-fi_ble/set' \
  -m '{"1":"open"}'
```

> **Windows CMD**
>
> ```cmd
> mosquitto_pub -h 192.168.0.1 ^
>   -t "tuya/pulsante_per_tapparella_wi-fi_ble/set" ^
>   -m "{\"1\":\"open\"}"
> ```

### 2. Ascolta gli **stati** pubblicati

```bash
mosquitto_sub -h 192.168.0.1 -t "tuya/+/status" -v
```

### 3. Ascolta i **comandi** che transitano

```bash
mosquitto_sub -h 192.168.0.1 -t "tuya/+/set" -v
```

### 3. Oppure ascolta **tutti** i messaggi che transitano

```bash
mosquitto_sub -h 192.168.0.1 -t "tuya/#" -v
```
---

Se tutto è ok, nel log del bridge vedrai:

```text
[RAW] tuya/pulsante_per_tapparella_wi-fi_ble/set -> {"1":"open"}
[CMD] pulsante_per_tapparella_wi-fi_ble <- {1: 'open'}
[ACK] pulsante_per_tapparella_wi-fi_ble -> {'Err': 0, ...}
```
e la tapparella si muoverà.


## Device testati

### -Pulsante Per Tapparella (Wi-Fi BLE)
IXTRIMA Pulsante saliscendi tapparella connesso Smart Wifi Tuya frutto modulo compatibile con supporti Vimar plana bianco
https://www.amazon.it/dp/B0F48V6RXJ?ref=ppx_yo2ov_dt_b_fed_asin_title
 
### -Doppio interruttore per tapparelle (Wi-Fi + 433Mhz)
Jane Eyre Modulo Relè Wireless WiFi Interruttore Remoto a 2 Canali, Relè Momentaneo/Autobloccante, Interblocco per APP Tuya/Smart Life con Telecomando RF 433MHz Compatibile con Alexa e Google Home
https://www.amazon.it/Jane-Eyre-Interruttore-Autobloccante-Interblocco/dp/B09STY1S2G/
