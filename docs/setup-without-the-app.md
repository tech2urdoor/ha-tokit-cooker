# Setting the cooker up without the app

> [!WARNING]
> **This doesn't work yet, and trying it will lock you out of the cooker until you set it up again.**
> It has been tried once on a real cooker. [tools/setup_wifi.py](../tools/setup_wifi.py) found the
> cooker on its own network, read a token and sent the Wi-Fi details, and the cooker joined the
> network. It then stopped answering to that token, so nothing could read or control it. The way
> back is to reset the Wi-Fi again and set the cooker up in the app.
>
> Running the script with `--check` is safe: it reads and changes nothing. Why the token stops
> working is being looked into, and this page will say when the rest works.

A cooker whose Wi-Fi has been reset opens a Wi-Fi network of its own and waits to be told which
network to join. The app normally does the telling. The script does it instead, and while it's there
it reads the cooker's token, which is the key Home Assistant needs. No account is made and nothing
goes over the internet.

## What you need

- A computer with Wi-Fi and Python 3.9 or newer
- A copy of this repository on it
- One package: `pip install cryptography`
- The name and password of a 2.4 GHz Wi-Fi network. The cooker can't join a 5 GHz one

## Steps

1. **Reset the cooker's Wi-Fi**, the way its manual describes. It leaves your network, if it was on
   one, and opens its own.
2. **Join that network from the computer.** It has no password. Its name starts with the cooker's
   model, `chunmi-ihcooker-cbhw_`. The computer will say it has no internet, which is right.
3. **Run the script** from the repository folder:

   ```bash
   python tools/setup_wifi.py
   ```

   It finds the cooker, shows its model, MAC address and firmware, and shows the token. Copy the
   token somewhere safe now.
4. **Type your Wi-Fi's name and password** when it asks. The password isn't shown as you type. The
   cooker takes them, closes its own network and joins yours.
5. **Join your own Wi-Fi again**, find the cooker in your router's list of devices by its MAC
   address, and give it a fixed address.
6. **Add the integration** in Home Assistant with that address and the token.

To look before you leap, `python tools/setup_wifi.py --check` finds the cooker and reads the token,
then stops without changing anything.

## Options

| Option | What it does |
|---|---|
| `--check` | Find the cooker and read its token, then stop |
| `--ssid NAME` | The Wi-Fi network to put it on, instead of being asked |
| `--token-file FILE` | Save the token in a file only you can read, instead of showing it |
| `--host ADDRESS` | The cooker's address on its own network, if the script can't find it. It's the router address your Wi-Fi settings show while you're joined to the cooker. On the cooker tried, that was `10.10.1.1` |

There is deliberately no option for the Wi-Fi password, so it never lands in your shell's history.

## What the script sends

Three things, all to the cooker and nowhere else:

1. A hello. A cooker in this state answers with its token. One already on a Wi-Fi network answers
   with the token blanked out, and the script stops there.
2. `miIO.info`, to check the model. It refuses to go on with anything but `chunmi.ihcooker.cbhw`.
3. `miIO.config_router` with the network name, the password and `uid` 0.

## Things to know

- **The token is shown once.** The script shows it before it sends the Wi-Fi details, because the
  cooker's network disappears straight after. If you lose it, reset the Wi-Fi and start again.
- **The cooker's own network is open.** The token crosses it unprotected, and the Wi-Fi password is
  protected only by that token, so someone within radio range at that moment could read both. It
  lasts the minute the setup takes, and it's how setup over an access point works for this whole
  family of devices.
- **The token changes, and when it does isn't worked out.** On the cooker tried, the token shown
  after the reset was the one it had before, and it stopped working once the cooker had joined the
  network. That is why this doesn't work yet.
- **The TOKIT app won't see a cooker set up this way**, because it was never tied to an account. To
  go back to the app, reset the Wi-Fi again and set it up there.
- **The cooker still calls its maker's cloud** once it's on a network with internet access. See
  [Keeping it local](../README.md#keeping-it-local).
- **If the cooker never appears on your network**, the name or password was wrong, or the network is
  5 GHz only. Reset its Wi-Fi and run the script again.
