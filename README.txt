PINSCAPE PICO JSON GENERATOR — EXPERIMENTAL ALPHA

This build began from one working cabinet configuration. Other hardware and
first-time workflows require community testing. See TESTING.md before sharing
or programming a generated configuration.

What this version does
----------------------
• Opens a Pinscape Pico configuration file.
• Creates one safe keyboard-only starter configuration without assuming that
  optional hardware is connected.
• Understands comments, unquoted property names, hexadecimal numbers, and
  trailing commas used by Pinscape's configuration format.
• Displays inputs, shifted/combo conditions, actions, timing, outputs, USB
  interfaces, accelerometer, ADC, plunger, and nudge sections.
• Reports import errors with a line and column number.
• Uses one row per physical button, modeled after the original KL25Z tool.
• New buttons start with the Pinscape firmware defaults of 1500 µs ON and
  1000 µs OFF debounce; imported timing values are preserved unchanged.
• Shows Normal and Shifted actions beside each other.
• Lets you designate a row as the Shift button without editing masks/bits.
• Lets you add, edit, and remove GPIO inputs and outputs in memory.
• Shows output PWM, Night Mode, time limit, cooling, and hold power in
  dedicated columns.
• Provides Add-ons selectors for I²C, nudge sensors, ADCs, and supported
  plunger/shooter sensor families.
• Omits optional interrupt properties when no interrupt wire is connected;
  it never writes a placeholder GPIO value of -1 for new sensor setups.
• Provides documented Pinball FX XInput mappings for plunger-only or
  plunger-plus-nudge configurations.
• Shows a color-coded static Pico GPIO assignment map on the Overview page.
  The Pico artwork is redistributed from the Pinscape Pico project under its
  included license; see PinscapePico-License.txt.
• Keeps raw parsed/generated diagnostics out of the normal cabinet-builder UI.
• Generates strict, valid JSON that Pinscape accepts as configuration syntax.
• Saves only to a new generated copy and refuses to overwrite the imported file.
• Never silently fixes, uploads, or overwrites the source configuration.

Running it on Windows
---------------------
1. Install Python 3 from python.org if it is not already installed.
2. Double-click "Start Pinscape Builder.bat".
3. Click "Open configuration…" and select a Pinscape configuration.

Creating the standalone tester EXE
----------------------------------
On the Windows computer where the builder already runs, double-click
"Build Windows EXE.bat". It installs PyInstaller and creates:

    dist\PinscapePicoJSONGenerator.exe

That EXE contains Python and the Pico artwork, so testers don't need to install
Python. Windows might display an unsigned-app warning because this prototype
doesn't have a commercial code-signing certificate.

This is source code, not a finished installer. The Python files can be edited
in Notepad++, VS Code, or another text editor. A self-contained Windows EXE can
be packaged later after the interface and behavior are settled.

Project direction
-----------------
The imported source remains protected. Current/planned stages:
1. Import and inspect the working configuration.
2. Graphically edit input/output assignments and shifted mappings (included).
3. Add optional devices such as LIS3DH/MMA8451-family accelerometers and the
   Adafruit ADS1115 ADC.
4. Generate configuration text for copying into the official Pinscape Config
   Tool, which remains responsible for validation, upload, calibration, and
   hardware testing.
