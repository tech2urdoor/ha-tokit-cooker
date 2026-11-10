# Reading the token from a cooker already in the app

If the cooker is set up in the TOKIT app and you'd rather leave it that way, its token can be read
from an Android phone that has the app. Nothing on the cooker changes: no reset and no pairing.

This worked with version 1.5.2 of the app. A later version may behave differently. If you don't
have an Android phone, or this stops working, [set the cooker up without the app](setup-without-the-app.md)
instead.

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
without a press on its own button. Treat it like a password. It stays the same until the cooker is
reset and set up again.
