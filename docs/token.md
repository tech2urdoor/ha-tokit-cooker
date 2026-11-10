# Reading the token from a cooker set up in the app

Once the cooker is set up in the TOKIT app, its token can be read from an Android phone that has the
app. Nothing on the cooker changes: no reset and no pairing.

This worked with version 1.5.2 of the app, twice: on a cooker that had been in the app for a while,
and again straight after the cooker was set up afresh. A later version may behave differently.

It needs the app and an Android phone. No way of getting the token without the app has been found:
[setting the cooker up without it](setup-without-the-app.md) can't work.

## Why it works

While the app is on screen it keeps asking the cloud for your list of devices, and it writes each
answer to the phone's system log. The answer includes each device's local address and its token.

## Steps

You need a computer with [adb](https://developer.android.com/tools/adb), and USB debugging turned on
in the phone's developer options.

1. Connect the phone by USB and start capturing its log to a file:

   ```bash
   adb logcat -T 1 > phone-log.txt
   ```

2. Open the TOKIT app and wait about ten seconds on its main screen.
3. Stop the capture with Ctrl+C.
4. Search the file for the token. It's 32 characters, using only 0 to 9 and a to f, in a field named
   `token`, next to `localip`, `mac` and `model`:

   ```bash
   grep -o '"token":"[0-9a-f]\{32\}"' phone-log.txt | sort -u
   ```

   If you have more than one device in the app, check the `model` beside each token. The cooker's is
   `chunmi.ihcooker.cbhw`.
5. **Delete the file.** It holds the token, and whatever else every app on your phone logged in
   those seconds.

## Looking after the token

Anyone on your network who has the token can control the cooker, within the limit that it won't heat
without a press on its own button. Treat it like a password.

It stays the same until the cooker is put on a Wi-Fi network again, by the app or by anything else.
Resetting the cooker's Wi-Fi doesn't change it. Setting the Wi-Fi up afterwards does, every time, so
after that you read the token again and give Home Assistant the new one.
