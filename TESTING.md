# Testing the experimental alpha

Thank you for helping test Pinscape Pico JSON Generator. This project currently has one thoroughly used reference cabinet configuration, but broad hardware compatibility and first-time usability are not yet proven.

## Safety boundary

- Keep a backup of every known-good configuration.
- The generator saves a new copy and should never overwrite the imported source.
- Review generated JSON in MJR's official Pinscape Pico Config Tool.
- Do not energize solenoids, contactors, motors, or other high-power outputs until their GPIO, driver hardware, Night Mode behavior, time limit, cooling time, and hold power have been independently checked.
- Calibration, firmware installation, live input testing, and Pico programming remain functions of the official tool.

## Suggested first test

1. Start the generator without instructions from the project author.
2. Create a new configuration.
3. Add one keyboard button and assign its key with **Set key**.
4. Add a second button with a shifted action.
5. Add an output, but do not connect or energize hardware yet.
6. Save a generated copy.
7. Open the copy in the official Pinscape Pico Config Tool and record every warning or error.
8. Reopen the generated copy in this generator and verify that the assignments still display correctly.

## Additional areas needing testing

- Importing commented JSON-style configurations and strict JSON files.
- Shift-button reassignment and preservation of shifted actions.
- Duplicate GPIO prevention across buttons, outputs, I²C, ADC, and interrupt pins.
- Digital and PWM output generation and Night Mode behavior.
- Pico ADC and ADS1115 plungers.
- Every listed nudge and plunger sensor.
- Automatic I²C bus creation and alternate bus pins.
- Generic gamepad, Open Pinball Device, and Pinball FX/XInput mappings.
- Windows display scaling and smaller screens.
- The standalone Windows executable on computers without Python.

## Known limitations

- No direct Pico programming, firmware updates, calibration, or live hardware testing.
- Some advanced imported actions are preserved but cannot yet be fully edited visually.
- Optional hardware combinations have not all been tested on physical devices.
- Pinball FX/XInput generation is based on official configuration documentation but still needs broader cabinet testing.
- The Windows executable is unsigned and can trigger a SmartScreen warning.

## Reporting a useful issue

Include:

- Windows version and display scaling percentage.
- Pico model and Pinscape firmware build.
- Whether you started from a new configuration or imported one.
- Exact steps leading to the problem.
- The generator's Import messages and the official Config Tool's error text.
- A sanitized configuration sample when possible.

Remove names, paths, identifiers, or other private information before attaching configuration files or screenshots publicly.
