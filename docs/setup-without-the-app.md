# Setting the cooker up without the app

> [!WARNING]
> **It can't be done, and trying it locks you out of the cooker.** A cooker in setup mode takes
> Wi-Fi details from anything that sends them, the app or not. It then makes itself a new token and
> shows it to nothing on your network. You're left with a cooker on your Wi-Fi that you can't read
> or control, until you reset its Wi-Fi and set it up in the app.
>
> That goes for any tool that sends `miIO.config_router`, python-miio's Wi-Fi command included.

The TOKIT app is needed once, to put the cooker on your Wi-Fi. After that you
[read the token from the phone](token.md), and the app has no further part in it.

This page is what was tried, so that nobody has to find it out again. It was done on one Induction
Cooker Pro (TCL02M-3A, firmware 2.2.0_0002), whose Wi-Fi was reset four times in an evening.
Release 0.1.0 of this repository carried a script for it, `tools/setup_wifi.py`. The script has been
removed.

## What the cooker does after a Wi-Fi reset

- It restarts and opens a Wi-Fi network of its own, with no password. The network's name starts
  with `chunmi-ihcooker-cbhw_`. The cooker is that network's router, at `10.10.1.1`.
- It answers a hello with its token in full. A cooker on Wi-Fi blanks that field.
- **The token is the one it had before the reset.** A reset by itself doesn't change it.
- It answers `miIO.info` sent with that token, giving its model, MAC address and firmware.

Up to here it's everything setup over an access point needs.

## What it does when it's given Wi-Fi details

This is `miIO.config_router` with `ssid`, `passwd` and `uid` 0, sent with the token the cooker had
just shown:

- It sends no reply.
- It closes its own network at once. It doesn't restart.
- It joins the Wi-Fi named within seconds.
- **From that moment it ignores the token it had shown**, and a hello gets the blanked field.

| Try | Wi-Fi details sent | What happened |
|---|---|---|
| 1 | A real network | The cooker joined it. The token it had shown no longer worked |
| 2 | The same, with its address on that network watched from the moment it appeared | The cooker joined it. Its first answer already had the token blanked, and it answered to none of the tokens it had shown so far |
| 3 | A network that doesn't exist | The cooker closed its own network and didn't come back in five minutes. After another reset it showed a new token again |

The third try settles it. On a network that isn't there the cooker could reach nothing, and its
token changed all the same. **The cooker makes the new token itself, the moment it's given Wi-Fi
details.** Nothing can ask it for that token afterwards, because every request has to be encrypted
with the token you don't have.

## Why the app can do it

Setting the cooker up in the app changes the token too: the one the cooker showed in setup mode
wasn't the one it answered to afterwards. The difference is that the app is told the new one. Once
the cooker is on a network with internet access it calls its maker's cloud, and the new token turns
up in the list of devices the app fetches from that cloud for your account. That list is where
[reading the token from the phone](token.md) gets it.

None of this is special to the cooker. The maintainer of python-miio, the best-known library for
this family of devices, [put it](https://github.com/rytilahti/python-miio/issues/461) as "the token
gets changed during provisioning", and says there is no known way to ask a device for it afterwards.

There is a sound reason for it. In setup mode the cooker's network is open and it hands its token
to anyone in range who asks. A token that has been given out like that is thrown away as soon as
setup happens.

## Not tried

- Reading the token out of the cooker's Wi-Fi chip. That means opening a mains appliance.
- Catching what the cooker tells its maker's cloud.
- Other firmware versions. If yours behaves differently, please
  [open an issue](https://github.com/tech2urdoor/ha-tokit-cooker/issues).

## If you've already tried it

Reset the cooker's Wi-Fi again, set it up in the TOKIT app, and [read the new token](token.md). Then
add the integration again in Home Assistant with the new token: it updates the cooker that's already
there.
