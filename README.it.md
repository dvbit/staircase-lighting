# Staircase Lighting

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Integrazione custom per Home Assistant che gestisce l'illuminazione automatica di scale con timer a zona, controllo lux e modalità luminosità ridotta. Ogni scala è un'istanza indipendente configurata via UI.

## Funzionalità

- **Rilevamento movimento a due zone**: sensori indipendenti per zona bassa e alta
- **Timer a zona**: le luci restano accese finché entrambi i timer non sono scaduti
- **Controllo lux**: verifica opzionale della luminosità ambientale prima dell'accensione
- **Modalità ridotta**: luminosità ridotta tramite fascia oraria o entità esterna
- **Regolabile a runtime**: tutti i parametri modificabili dalla dashboard senza riavvio
- **Multi-istanza**: configura quante scale vuoi, completamente isolate
- **Localizzata**: inglese, italiano, francese, spagnolo, tedesco

## Requisiti

- Home Assistant 2024.1 o successivo
- HACS installato

## Installazione

### HACS (consigliato)

1. Apri HACS → Integrazioni → menu 3 puntini → Repository personalizzati
2. Aggiungi `https://github.com/dvbit/staircase_lighting` come **Integrazione**
3. Cerca "Staircase Lighting" e installa
4. Riavvia Home Assistant

### Manuale

1. Scarica lo zip dell'ultima release
2. Estrai `custom_components/staircase_lighting/` nella cartella `config/custom_components/` di HA
3. Riavvia Home Assistant

## Configurazione

Vai su **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Staircase Lighting**.

### Step 1 — Nome
| Campo | Descrizione |
|---|---|
| Nome | Nome descrittivo per questa scala (es. "Scala Piano 1") |

### Step 2 — Entità
| Campo | Descrizione |
|---|---|
| Sensore movimento zona basso | `binary_sensor` alla base della scala |
| Sensore movimento zona alto | `binary_sensor` in cima alla scala |
| Luce zona basso | Entità `light` in basso |
| Luce zona alto | Entità `light` in alto |
| Sensore luminosità ambientale | `sensor` opzionale con device class `illuminance` |

### Step 3 — Parametri
| Campo | Range | Default | Descrizione |
|---|---|---|---|
| Ritardo spegnimento | 10–300 s | 60 | Secondi prima della scadenza del timer |
| Luminosità normale | 1–100 % | 100 | Luminosità in modalità normale |
| Luminosità ridotta | 1–100 % | 20 | Luminosità in modalità ridotta |
| Soglia lux | 0–1000 lx | 50 | Sotto questo valore le luci si accendono |
| Abilita controllo lux | on/off | on | Attiva/disattiva il controllo lux |

### Step 4 — Modalità ridotta
Scegli tra:
- **Disabilitata**: sempre luminosità normale
- **Fascia oraria**: ridotta in una finestra temporale (supporta cavallo mezzanotte, es. 23:00–07:00)
- **Entità esterna**: ridotta quando un `binary_sensor` o `input_boolean` è ON

## Entità esposte

Per ogni scala configurata (esempio: "Scala Ingresso"):

| Entità | Tipo | Descrizione |
|---|---|---|
| `binary_sensor.scala_ingresso_motion_bottom` | binary_sensor | Stato sensore movimento basso in tempo reale |
| `binary_sensor.scala_ingresso_motion_top` | binary_sensor | Stato sensore movimento alto in tempo reale |
| `sensor.scala_ingresso_state` | sensor | `idle` o `active` |
| `sensor.scala_ingresso_mode` | sensor | `normal` o `dim` |
| `sensor.scala_ingresso_time_remaining` | sensor | Secondi rimanenti allo spegnimento (0 quando inattivo) |
| `sensor.scala_ingresso_current_brightness` | sensor | Luminosità attuale % dall'entità luce |
| `sensor.scala_ingresso_ambient_lux` | sensor | Lux ambientale in tempo reale (solo se sensore lux configurato) |
| `number.scala_ingresso_turn_off_delay` | number | Ritardo runtime (slider) |
| `number.scala_ingresso_brightness` | number | Luminosità normale runtime |
| `number.scala_ingresso_brightness_dim` | number | Luminosità ridotta runtime |
| `number.scala_ingresso_lux_threshold` | number | Soglia lux runtime |
| `switch.scala_ingresso_lux_control` | switch | Abilita/disabilita controllo lux |
| `button.scala_ingresso_set_lux_threshold` | button | Imposta soglia lux al valore ambientale attuale |

## Esempi di utilizzo

### Esempio 1 — Scala base (senza lux, senza dim)

Configura con due sensori PIR e due luci. Lascia il sensore lux vuoto, imposta la modalità ridotta su "Disabilitata". Le luci si accendono al 100% al rilevamento del movimento e si spengono dopo 60 secondi di inattività.

### Esempio 2 — Scala con controllo lux

Aggiungi un sensore di illuminamento (es. `sensor.lux_corridoio`). Imposta la soglia a 30 lx. Le luci si accendono solo quando la luce ambientale è sotto 30 lx. Disabilita il controllo lux dallo switch in dashboard per override temporaneo.

### Esempio 3 — Modalità notturna con fascia oraria

Imposta la modalità ridotta su "Fascia oraria", inizio 23:00, fine 07:00. Di notte le luci si accendono al 20%. Di giorno si applica la luminosità normale. Regola `number.scala_ingresso_brightness_dim` dalla dashboard per perfezionare.

### Esempio 4 — Ridotta tramite entità esterna

Crea un helper `input_boolean.modalita_notte`. Imposta la modalità ridotta su "Entità esterna" e selezionalo. Attiva il boolean da un'automazione o manualmente. Quando è ON, la scala usa la luminosità ridotta.

## Logica operativa

1. **Movimento rilevato** su uno dei sensori di zona
2. **Controllo lux**: se abilitato e il sensore legge sopra la soglia → evento ignorato
3. **Determinazione modalità**: verifica condizione dim (fascia oraria o entità) → imposta `normal` o `dim`
4. **Accensione** entrambe le luci alla luminosità determinata (forza la luminosità anche se già accese)
5. **Avvio/riavvio** del timer della zona attivata
6. **Scadenza timer**: alla scadenza, verifica se anche l'altro è scaduto
   - Entrambi scaduti → spegnimento luci, stato = `idle`
   - Uno ancora attivo → nessuna azione, stato rimane `active`

La modalità viene fissata all'accensione e non cambia durante il ciclo.

## Specifica

Questa integrazione è stata costruita dal seguente requisito consolidato:

- Config flow: 4 step (nome, entità, parametri, modalità dim)
- Modalità dim: mutuamente esclusiva — none / time_range / external_entity
- Singola fascia oraria per istanza, supporto cavallo mezzanotte
- Controllo lux con fail-safe (sensore assente/non disponibile = permetti)
- Timer a zona via `async_call_later`, spegnimento solo quando entrambi scaduti
- Entità number/switch bidirezionali — effetto immediato al prossimo ciclo
- Sensori di movimento (bottom/top) e lux specchiati nel device virtuale in tempo reale
- Sensore countdown tempo rimanente (aggiornamento ogni 1s)
- Sensore luminosità attuale (legge attributo brightness reale dall'entità light)
- Pulsante per impostare la soglia lux al valore ambientale corrente
- Options flow replica step 2-4 del config flow, senza riavvio
- Isolamento completo delle istanze
- Compatibilità minima: Home Assistant 2024.1

## Licenza

MIT
