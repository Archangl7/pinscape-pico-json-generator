# Pinscape Pico JSON Generator

A community-built Windows interface for creating and editing JSON configuration files for [Pinscape Pico](https://github.com/mjrgh/PinscapePico).

## Why this project exists

Pinball King started this project after working through the difficult process of creating a reliable Pinscape Pico configuration for a real virtual pinball cabinet. The JSON format is powerful, but configuring GPIO assignments, shifted buttons, output safety settings, nudge hardware, and a plunger by hand can be intimidating and syntax-sensitive.

Once that cabinet had a known-good working configuration, we worked backward from it to build a visual generator. The goal is to make simple Pinscape Pico setups approachable while still exposing the advanced functions that make the platform valuable. This project is being shared as a way for Pinball King to give back to the virtual pinball community.

## What it does

The generator can:

- Create a safe keyboard-only starter configuration.
- Import existing Pinscape Pico JSON-style configurations without overwriting them.
- Assign cabinet buttons, keyboard keys, a Shift button, and shifted actions.
- Configure GPIO and PWM outputs with Night Mode and output safety settings.
- Configure I²C buses, nudge sensors, plunger sensors, USB interfaces, and Pinball FX/XInput mappings.
- Display GPIO assignments on a Pico board diagram.
- Detect duplicate GPIO assignments and missing required bus configuration.
- Save a strict JSON copy for review, hardware testing, calibration, and programming with the official Pinscape Pico Config Tool.

## Project status: experimental alpha

This is an experimental tester preview, not a proven public release. Development started from one personally tested cabinet configuration. We do not yet know whether every supported sensor, output type, imported configuration, or first-time workflow is generated correctly.

The first public phase is intended to answer a basic question: can other builders use the program without private guidance and produce configurations that the official Pinscape Pico Config Tool accepts and reports correctly?

Always review a generated configuration in the official Pinscape Pico Config Tool before programming hardware. Do not connect or activate high-power outputs based only on this generator's display.

The generator never overwrites an imported source configuration and does not directly program the Pico.

See [TESTING.md](TESTING.md) for the current test plan, known limitations, and useful information to include in a bug report.

## Download or run

Windows testers should use `PinscapePicoJSONGenerator.exe` from the latest GitHub Actions build or release when available.

To run from source:

1. Install Python 3.
2. Download or clone this repository.
3. Run `Start Pinscape Builder.bat`.

To build the standalone Windows executable locally, run `Build Windows EXE.bat`. The result is written to `dist\PinscapePicoJSONGenerator.exe`.

## Attribution

Created by **Pinball King** as a community give-back project for virtual pinball builders.

Pinscape Pico, its firmware, official Config Tool, configuration format, and documentation are created by [Michael J. Roberts (MJR)](https://github.com/mjrgh). Visit the [Pinscape Pico repository](https://github.com/mjrgh/PinscapePico) and [MJR's Pinscape resources](https://mjrnet.org/pinscape/) for the official project and documentation.

This generator is an independent community project. It is not an official Pinscape release and is not endorsed by or affiliated with Michael J. Roberts or the Pinscape project.

The Overview board diagram was sourced from `GUIConfigTool/resources/PicoDiagram.bmp` in the [Pinscape Pico repository](https://github.com/mjrgh/PinscapePico) and converted to PNG for display by this application. It is redistributed under the notices supplied with Pinscape Pico; see [PinscapePico-License.txt](PinscapePico-License.txt). That license also contains the applicable Raspberry Pi artwork and documentation notices.

Raspberry Pi and Pico are trademarks of Raspberry Pi Ltd. This project is not affiliated with or endorsed by Raspberry Pi Ltd. See [Raspberry Pi licensing information](https://www.raspberrypi.com/licensing/).

## License

The original code in this repository is released under the [BSD 3-Clause License](LICENSE). Components originating from Pinscape Pico remain subject to the notices in [PinscapePico-License.txt](PinscapePico-License.txt).

## Feedback

Please use GitHub Issues for reproducible import problems, incorrect generated JSON, GPIO validation errors, and interface suggestions. Remove private cabinet information from configuration samples before posting them publicly.
