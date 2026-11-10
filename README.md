<img src="custom_components/tokit_cooker/brand/icon.png" alt="" width="96" align="right">

# TOKIT Induction Cooker for Home Assistant

Read and control a TOKIT Induction Cooker Pro from Home Assistant over your own network, with no
app, account or cloud. It's a community project and is [not affiliated with TOKIT](#disclaimer).

> [!WARNING]
> **Status: early, and run on one cooker only.** On an Induction Cooker Pro (TCL02M-3A, firmware
> 2.2.0_0002) an earlier build of this read the cooker through a cook and selected a mode from Home
> Assistant. With a pot of water heating, power level, target temperature, pause, resume and stop
> all worked when sent from a script using the same protocol code.
> Not done yet on a real cooker: pressing those controls from Home Assistant while it heats.
> [Setting it up without the app](docs/setup-without-the-app.md) **doesn't work yet**: tried on the
> real cooker, it put the cooker on the Wi-Fi and left it answering to no known token. Apart from
> that attempt, the code in this release has run against a simulated cooker only. The table under
> [What has been seen](#what-has-been-seen) keeps score.

**It can't start the heat, and that is the cooker's doing.** A start command over the network only
wakes the cooker and selects a mode. It then waits for a press on its own button before it heats.
Once someone has pressed it, everything else can be done from Home Assistant.

## What you get

| Entity | What it is |
|---|---|
| `Status` | Off, idle, cooking, cooking with timer, scheduled or paused |
| `Heating` | On while it is cooking |
| `Temperature`, `Target temperature` | In °C. See the note on [idle readings](docs/protocol.md#traps) |
| `Power level` | 0 to 99, the cooker's own scale |
| `Time remaining`, `Cooking time` | In minutes |
| `Fault`, `Problem` | No pan, mains voltage too high or low, surface or electronics too hot, sensor faults, coil disconnected |
| `Power level` and `Target temperature` controls | A slider and a box. They work only while the cooker is cooking or paused, and refuse otherwise |
| `Stop`, `Pause`, `Resume` buttons | Stop ends the cook and leaves the cooker idle. It doesn't switch it off |
| `tokit_cooker.select_mode` action | Wakes the cooker and selects hotpot, steam or boil, stir fry, fry, or soup or congee. The cooker then waits for its button |

Three more diagnostic sensors (`Detailed status`, `Program type`, `Phase`) are there but disabled.

It polls every 30 seconds, and every 5 while the cooker is cooking.

## What it doesn't do

- **Start the heat.** See above.
- **Switch the cooker on or off.** There's no command for it. `select_mode` does wake it from off.
- **Recipes and stepped programs.** The cooker has commands for them, but their data format isn't
  understood.
- **Scheduling.** Not looked at.
- **Other models.** Setup refuses any model but `chunmi.ihcooker.cbhw`, on purpose: the same command
  numbers can mean something else on a different hob. If you have another one,
  [say so](#report-your-cooker).

## Safety

It's a hob, and this lets software change how hard it heats. What stands between that and a
mistake:

- The cooker won't heat until someone presses its button, whatever is sent to it. This integration
  doesn't try to get around that and won't.
- The power and temperature controls refuse unless the cooker is already cooking or paused, so
  neither can be the first thing sent.
- The target temperature is capped at 200 °C. The built-in modes use 155 to 199.
- Selecting a mode is an action, not a switch, so nothing can turn it on as part of a group or a
  scene.

An automation can still raise the power of something that is already cooking. Think about that
before you write one, and prefer automations that only lower the heat, pause or stop.

## Getting the cooker ready

Home Assistant needs two things: the cooker's address on your network, and its **token**, a
32-character key every device of this family has. There are two ways to get there.

- **Without the app.** Reset the cooker's Wi-Fi, join the network it opens, and run a script from
  this repository. It reads the token and puts the cooker on your Wi-Fi, with no account anywhere.
  [How it's meant to go](docs/setup-without-the-app.md). **It doesn't work yet**, so read the
  warning there before you try it.
- **With a cooker already set up in the TOKIT app.** It stays as it is, and you
  [read its token from an Android phone](docs/token.md). This is how the one cooker here was done.

Either way, give the cooker a fixed address in your router afterwards.

## Install

Needs Home Assistant 2025.6 or newer. It has only been run on 2026.10.

### With HACS

1. In HACS, open the menu, choose **Custom repositories**, and add
   `https://github.com/tech2urdoor/ha-tokit-cooker` as an **Integration**.
2. Find **TOKIT Induction Cooker** in HACS and download it.
3. Restart Home Assistant.

### By hand

Copy `custom_components/tokit_cooker` into the `custom_components` folder of your Home Assistant
configuration, then restart.

### Then

**Settings → Devices & services → Add integration → TOKIT Induction Cooker**, and give it the
address and the token. If the token ever changes, add the integration again with the new one: it
updates the cooker that's already there.

## Keeping it local

Nothing in this integration talks to anything but the cooker. The cooker is another matter: on
Wi-Fi with internet access it still calls its maker's cloud by itself. To stop that, block its
internet access at your router and leave it reachable on your network. That hasn't been tried here
yet, and it will stop the TOKIT app working with it.

## What has been seen

"Seen" means on a real cooker, the one in the status box.

| | Seen | How |
|---|---|---|
| Reading status, temperature, target, power level and time | Yes | In Home Assistant, with an earlier build |
| Selecting each of the five modes | Yes | Hotpot from Home Assistant, all five from a script |
| The cooker waiting for its button after a mode is selected | Yes | Every time |
| Power level and target temperature while heating | Yes | From a script. Not yet from Home Assistant |
| Pause, resume and stop while heating | Yes | From a script. Not yet from Home Assistant |
| Power and temperature refused while idle | Yes | In Home Assistant, and the cooker itself refuses too |
| Setup without the app | No | Tried once. The cooker joined the Wi-Fi, then stopped answering to the token it had shown |
| Fault reporting | No | No fault has happened yet |
| Working with the cooker's internet access blocked | No | |

## Report your cooker

If you have this model, an [issue](https://github.com/tech2urdoor/ha-tokit-cooker/issues) saying
what worked and what didn't, with the firmware version from the device page, is the most useful
thing you can send. If you have a different TOKIT or Chunmi hob, open one with the model name setup
showed you when it refused.

## Docs

- [Setting it up without the app](docs/setup-without-the-app.md)
- [Reading the token from a cooker already in the app](docs/token.md)
- [The protocol](docs/protocol.md): what the cooker understands, and the traps

To run the tests: `python tests/test_miio.py` and `python tests/test_setup_wifi.py` need only
`cryptography`. `pytest` needs `pytest-homeassistant-custom-component`. None of them touches a real
cooker: they talk to a pretend one in [tests/fake_cooker.py](tests/fake_cooker.py).

## Disclaimer

This project is not affiliated with, endorsed by, or supported by TOKIT, Chunmi or Xiaomi. Their
names are used here only to say which cooker this works with. No code, text or artwork of theirs is
included. The protocol was worked out for interoperability.

It's offered as is, under the [MIT licence](LICENSE), with no warranty. It sends commands to a
cooking appliance you own, which could affect the appliance or its warranty. Don't leave a hob
unattended because software is watching it.
