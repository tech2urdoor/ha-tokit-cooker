# The protocol

What the cooker understands, as far as it has been worked out. Everything here was read from one
Induction Cooker Pro (`chunmi.ihcooker.cbhw`, firmware 2.2.0_0002) or from its published spec.

## Transport

Xiaomi's miIO, on UDP port 54321. Each packet is a 32-byte header and an AES-128-CBC payload. The
key is the MD5 of the device's token, and the IV is the MD5 of key + token. A plain hello packet
gets back the device id and a timestamp, which every later packet must carry.

Inside is JSON using the "MIoT spec" methods `get_properties`, `set_properties` and `action`. Every
value has a service number and a property number, written here as `3.7`. The numbers come from the
cooker's published spec, `urn:miot-spec-v2:device:induction-cooker:0000A033:chunmi-cbhw:1`.

[miio.py](../custom_components/tokit_induction_cooker/miio.py) is the whole client, in about 130 lines.

## Properties

| Property | Meaning |
|---|---|
| 2.1 status | 0 idle, 1 cooking, 2 cooking with timer, 3 scheduled, 4 paused, 5 off |
| 2.2 fault | 0 none, 2 no pan, 3 and 4 mains voltage high and low, 5 surface too hot, 7 electronics too hot, 8 and 10 sensor faults, 11 internal communication, 12 coil disconnected |
| 2.5 left-time, 2.6 working-time | Minutes left on the timer, minutes cooked |
| 3.1 menu | The selected program, as hex. See below |
| 3.2 phase | Not worked out |
| 3.3 work-status | A finer status: 1 idle, 2 cooking, 4 scheduled, 8 error, 10 cooking with timer, 11 off, 12 paused |
| 3.6 pause-time | A countdown in seconds while paused. It started at 598 |
| 3.7 temperature, 3.8 target-temperature | °C |
| 3.9 fire-gears | Power level, 0 to 99 |
| 3.15 recipe-type | 0 built-in mode, 1 fixed power, 2 stepped power, 3 fixed temperature, 4 recipe |
| 3.24 finish-push | By its name, a notification through the cloud when a cook ends. Not used here |
| 3.25 buzzer-mark | The beeper setting, behind the `Mute` switch. A write of the value it already had was accepted with code 0. Which way round it is hasn't been checked |
| 3.29 move-temperature | A second temperature some modes carry. Soup has 90 |
| 3.35 hotpot-mode | 0 boil, 1 warm. Not used here |

3.24, 3.25 and 3.35 are the only properties the spec lets you write with `set_properties`.

## Actions

Inputs are a list of `{"piid": n, "value": v}` objects.

| Action | Inputs | What happened |
|---|---|---|
| 2.1 start-cook | 2.8 cook mode, 1 to 5 | Wakes the cooker and selects the mode. **It doesn't heat.** The cooker asks for a press on its own button |
| 2.2 cancel-cooking | none | Stops the cook. Status goes to 0, idle, not 5, off |
| 2.3 pause | none | Status goes to 4 |
| 3.3 pause-recover | 3.20, 3.19 | Status goes back to 1 |
| 3.13 set-fire | 3.9 power level, 3.20, 3.19 | Changes the power while cooking. Answers code 1 and does nothing while idle |
| 3.14 set-temperature | 3.8 target temperature, 3.20, 3.19 | Changes the target while cooking. 80 was accepted |
| 3.1 start-cooking, 3.5 set-menu | Recipe data | Format unknown. Not used here |
| 3.11 get-error-recorded | none | Read-only: the stored error log. Not used here |

3.20 is "information" and 3.19 is "user id". Empty strings work for both.

Every accepted action answered with code 0 within a second or two.

## Cook modes

The spec names modes 3 to 5 as simmer, stir fry and deep fry. The cooker disagrees: the names
below are the ones it reports for each mode, and they are what the integration follows.

| Mode | On the cooker | Target | Timer |
|---|---|---|---|
| 1 | 火锅, hotpot | 185 °C | 10 min |
| 2 | 蒸煮, steam or boil | 180 °C | 5 min |
| 3 | 炒菜, stir fry | 199 °C | 30 min |
| 4 | 煎炸, fry | 199 °C | 20 min |
| 5 | 汤粥, soup or congee | 155 °C | 15 min |

The menu property, 3.1, reads back as hex: four bytes, a menu number, the name in GBK, then `00`.
The first byte has been seen as 03 and 05. Menu numbers aren't mode numbers: modes 3, 4 and 5 are
menus 04, 05 and 03.

## Setup mode

After a Wi-Fi reset the cooker restarts and opens a network of its own, with no password. It is that
network's router, at `10.10.1.1`. There a hello gets back the token in full, and `miIO.info` works
with it.

`miIO.config_router` with `ssid`, `passwd` and `uid` gets no reply. The cooker closes its network,
joins the one named, and from that moment answers only to a new token it has made for itself.
[What that means for setup](setup-without-the-app.md).

## Traps

- **Code 0 from start-cook doesn't mean it's heating.** It means the mode was selected. Watch
  status, 2.1, for 1 or 2.
- **Plain values break the reply.** Send an action's inputs as bare values instead of
  `{"piid": n, "value": v}` objects and the cooker answers with JSON that doesn't parse.
- **A wrong token gets silence, not an error.** It looks the same as the cooker being unplugged.
- **The temperature reading wanders while idle.** With nothing cooking it read anywhere from 5 to
  42 °C. It was steady when off and believable while heating. Don't trigger anything on it unless
  the status says cooking.
- **A hello shows nothing about the token** on a cooker that's on Wi-Fi: that field comes back as 16
  bytes of `ff`.

## Not worked out

- Recipes and stepped programs (3.1 start-cooking, 3.5 set-menu).
- Scheduling.
- The limits of the target temperature. 80 was accepted, and the built-in modes use 155 to 199.
