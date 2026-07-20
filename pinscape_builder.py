from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from pinscape_parser import PinscapeParseError, loads


class Builder(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Pinscape Pico JSON Generator — Experimental Alpha")
        self.geometry("1280x800")
        self.minsize(1024, 650)
        self.config_data: dict = {}
        self.original_data: dict = {}
        self.parked_shifted: dict[int, list[dict]] = {}
        self.current_path: Path | None = None

        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", foreground="#555555")

        header = ttk.Frame(self, padding=14)
        header.pack(fill="x")
        ttk.Label(header, text="Pinscape Pico JSON Generator", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Save generated copy…", command=self.save_generated).pack(side="right", padx=(8, 0))
        ttk.Button(header, text="Open configuration…", command=self.open_file).pack(side="right")
        ttk.Button(header, text="New configuration…", command=self.new_configuration).pack(side="right", padx=(0, 8))

        info = ttk.Frame(self, padding=(14, 0, 14, 10))
        info.pack(fill="x")
        self.path_label = ttk.Label(info, text="No configuration loaded", style="Sub.TLabel")
        self.path_label.pack(side="left")
        ttk.Label(info, text="The imported source is never overwritten", style="Sub.TLabel").pack(side="right")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self.summary, self.pin_map = self._overview_tab()
        self.inputs, input_bar = self._tree_tab(
            "Button Inputs",
            ("number", "gpio", "shift", "normal", "shifted", "options", "usage"),
            (55, 75, 65, 210, 210, 180, 280), toolbar=True)
        ttk.Button(input_bar, text="Add button", command=lambda: self.edit_button_row(None)).pack(side="left")
        ttk.Button(input_bar, text="Edit selected", command=self.edit_selected_input).pack(side="left", padx=(18, 5))
        ttk.Button(input_bar, text="Make selected the Shift button", command=self.make_selected_shift).pack(side="left", padx=(0, 5))
        ttk.Button(input_bar, text="Remove selected", command=self.remove_selected_input).pack(side="left")
        self.shift_status = ttk.Label(input_bar, text="Shift button: not assigned")
        self.shift_status.pack(side="right")
        self.inputs.bind("<Double-1>", lambda _event: self.edit_selected_input())
        self.outputs, output_bar = self._tree_tab(
            "Output Ports",
            ("port", "name", "gpio", "mode", "night", "max_on", "cooling", "hold"),
            (55, 225, 70, 85, 150, 100, 100, 100), toolbar=True)
        ttk.Button(output_bar, text="Add output", command=lambda: self.edit_output(None)).pack(side="left")
        ttk.Button(output_bar, text="Edit selected", command=self.edit_selected_output).pack(side="left", padx=(18, 5))
        ttk.Button(output_bar, text="Remove selected", command=self.remove_selected_output).pack(side="left")
        self.outputs.bind("<Double-1>", lambda _event: self.edit_selected_output())
        self.devices, addon_bar = self._tree_tab("Add-ons", ("category", "device", "settings"), (180, 220, 620), toolbar=True)
        ttk.Button(addon_bar, text="USB interfaces", command=self.configure_usb).pack(side="left")
        ttk.Button(addon_bar, text="Configure I²C bus", command=self.configure_i2c).pack(side="left")
        ttk.Button(addon_bar, text="Configure nudge sensor", command=self.configure_nudge).pack(side="left", padx=5)
        ttk.Button(addon_bar, text="Configure plunger / shooter", command=self.configure_plunger).pack(side="left")
        ttk.Button(addon_bar, text="Pinball FX / XInput", command=self.configure_fx).pack(side="left", padx=5)
        self.messages = self._text_tab("Import messages")
        # Developer diagnostics remain available internally, but aren't shown
        # as normal cabinet-builder pages.
        self.raw = tk.Text(self)
        self.generated = tk.Text(self)
        self.input_rows: list[dict] = []

        self.status = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w", padding=5).pack(fill="x")
        self._show_welcome()

    def _show_welcome(self) -> None:
        welcome = (
            "EXPERIMENTAL ALPHA — TESTER PREVIEW\n\n"
            "This generator has been tested with one working cabinet configuration. "
            "Other hardware combinations still need community testing.\n\n"
            "Getting started\n"
            "1. Choose New configuration or Open configuration.\n"
            "2. Add only the buttons, outputs, and hardware you actually use.\n"
            "3. Resolve every item shown under Import messages.\n"
            "4. Save a generated copy. Your imported source is never overwritten.\n"
            "5. Review and test the copy in MJR's official Pinscape Pico Config Tool.\n\n"
            "Do not treat generated output as hardware-verified. Output safety values, "
            "sensor wiring, calibration, and firmware programming remain your responsibility."
        )
        self._set_text(self.summary, welcome)
        self._draw_pin_map()

    def _text_tab(self, title: str) -> tk.Text:
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text=title)
        text = tk.Text(frame, wrap="word", font=("Consolas", 10), padx=10, pady=10)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        text.configure(state="disabled")
        return text

    def _overview_tab(self):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text="Overview")
        text = tk.Text(frame, wrap="word", font=("Segoe UI", 10), padx=12, pady=12, width=42)
        text.grid(row=0, column=0, sticky="nsew")
        text.configure(state="disabled")
        canvas = tk.Canvas(frame, background="white", highlightthickness=0, width=650)
        canvas.grid(row=0, column=1, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=2)
        return text, canvas

    def _tree_tab(self, title: str, columns: tuple[str, ...], widths: tuple[int, ...], toolbar: bool = False):
        frame = ttk.Frame(self.tabs)
        self.tabs.add(frame, text=title)
        bar = ttk.Frame(frame, padding=6)
        if toolbar:
            bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for column, width in zip(columns, widths):
            tree.heading(column, text=column.replace("_", " ").title())
            tree.column(column, width=width, minwidth=60, anchor="w")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        row = 1 if toolbar else 0
        tree.grid(row=row, column=0, sticky="nsew")
        yscroll.grid(row=row, column=1, sticky="ns")
        xscroll.grid(row=row + 1, column=0, sticky="ew")
        frame.rowconfigure(row, weight=1)
        frame.columnconfigure(0, weight=1)
        return (tree, bar) if toolbar else tree

    def open_file(self) -> None:
        filename = filedialog.askopenfilename(
            title="Open Pinscape Pico configuration",
            filetypes=(("Pinscape configurations", "*.txt *.json *.js *.cfg"), ("All files", "*.*")),
        )
        if filename:
            self.load(Path(filename))

    def new_configuration(self) -> None:
        dialog = NewConfigDialog(self)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        name, unit = dialog.result
        cfg = {
            "id": {"unitNum": unit, "unitName": name, "ledWizUnitNum": 0},
            "keyboard": {"enable": True},
            "buttons": [],
            "outputs": [],
        }
        self.config_data = cfg
        self.original_data = {}
        self.parked_shifted = {}
        self.current_path = None
        self.path_label.configure(text="New unsaved configuration — Simple starter")
        self._populate()
        self.tabs.select(self.summary.master)
        self.status.set("New safe configuration created — add only the hardware you use")

    def load(self, path: Path) -> None:
        try:
            source = path.read_text(encoding="utf-8-sig")
            parsed = loads(source)
            if not isinstance(parsed, dict):
                raise PinscapeParseError("Top-level configuration must be an object", 1, 1)
        except (OSError, UnicodeError, PinscapeParseError) as exc:
            self._set_text(self.messages, f"IMPORT FAILED\n\n{exc}\n\nNo changes were made.")
            self.tabs.select(self.messages.master)
            self.status.set("Import failed — source file was not changed")
            messagebox.showerror("Could not import configuration", str(exc))
            return

        self.config_data = parsed
        self.original_data = json.loads(json.dumps(parsed))
        self.parked_shifted = {}
        self.current_path = path
        self.path_label.configure(text=str(path))
        self._populate()
        conflicts = self.validate_config()
        if conflicts:
            self.status.set(f"Imported {len(parsed)} sections with {len(conflicts)} conflict(s) — see Import messages")
            self.tabs.select(self.messages.master)
        else:
            self.status.set(f"Imported {len(parsed)} top-level sections — no changes made")

    def _populate(self) -> None:
        for tree in (self.inputs, self.outputs, self.devices):
            tree.delete(*tree.get_children())

        cfg = self.config_data
        unit = cfg.get("id", {})
        buttons = cfg.get("buttons", [])
        outputs = cfg.get("outputs", [])
        physical_buttons = self._group_buttons(buttons)
        enabled_usb = [name for name in ("keyboard", "gamepad", "xInput", "openPinballDevice") if cfg.get(name, {}).get("enable")]
        overview = [
            f"Unit: {unit.get('unitName', '(unnamed)')} (#{unit.get('unitNum', '?')})",
            f"USB interfaces: {', '.join(enabled_usb) or 'none found'}",
            f"Physical button inputs: {len(physical_buttons)}",
            f"Button action mappings: {len(buttons)} (normal, shifted, macros, and other actions)",
            f"Output devices: {len(outputs)}",
            "",
            "The official Pinscape Pico Config Tool remains responsible for programming, calibration, and live hardware testing.",
        ]
        self._set_text(self.summary, "\n".join(overview))
        self._draw_pin_map()

        self.input_rows = self._group_buttons(buttons)
        shift_gpios = []
        for number, row in enumerate(self.input_rows, 1):
            if row["is_shift"]:
                shift_gpios.append(str(row["gp"]))
            normal = row.get("normal") or row.get("always") or row.get("shift_source")
            shifted = row.get("shifted")
            options = self._row_options(row)
            usage = self._usage(normal, shifted)
            self.inputs.insert("", "end", values=(
                number,
                f"GP{row['gp']}",
                "SHIFT" if row["is_shift"] else "",
                self._action(normal.get("action", {})) if normal else "None",
                self._action(shifted.get("action", {})) if shifted else "None",
                options,
                usage,
            ))
        self.shift_status.configure(text="Shift button: " + (", ".join("GP" + gp for gp in shift_gpios) if shift_gpios else "not assigned"))

        for number, output in enumerate(outputs, 1):
            device = output.get("device", {})
            self.outputs.insert("", "end", values=(
                number,
                output.get("name", "(unnamed)"),
                f"GP{device.get('gp', '?')}" if device.get("type") == "gpio" else self._source(device),
                "PWM" if device.get("pwm") else "Digital",
                "Disabled" if output.get("noisy") else "Still active",
                self._display_ms(output.get("timeLimit")),
                self._display_ms(output.get("coolingTime")),
                (str(output["powerLimit"]) + "%") if "powerLimit" in output else "—",
            ))

        featured = ("id", "keyboard", "gamepad", "xInput", "openPinballDevice", "i2c0", "i2c1", "plunger", "pico_adc", "ads1115", "nudge", "lis3dh", "mxc6655xa", "mc3416")
        for bus in ("i2c0", "i2c1"):
            if bus in cfg:
                self.devices.insert("", "end", values=("Shared bus", bus.upper(), self._settings(cfg[bus])))
        nudge_type = self._configured_type(cfg, ("lis3dh", "mxc6655xa", "mc3416"), cfg.get("nudge", {}).get("source"))
        self.devices.insert("", "end", values=("Nudge", nudge_type or "Not configured", self._settings(cfg.get(nudge_type, {})) if nudge_type else ""))
        plunger_type = cfg.get("plunger", {}).get("source") or self._configured_type(cfg, ("pico_adc", "ads1115", "vcnl4010", "vl6180x", "aedr8300", "tcd1103", "tsl1410r", "tsl1412s"))
        self.devices.insert("", "end", values=("Plunger / shooter", plunger_type or "Not configured", self._settings(cfg.get(plunger_type, {})) if plunger_type else ""))
        fx = cfg.get("xInput", {})
        fx_text = "Right stick X = reversed plunger" if fx.get("xRight") == "negate(plunger.z)" else self._settings(fx)
        self.devices.insert("", "end", values=("Game compatibility", "Pinball FX / XInput" if fx.get("enable") else "XInput disabled", fx_text if fx.get("enable") else ""))

        known = set(featured) | {
            "buttons", "outputs", "serialPorts", "logging", "vcnl4010", "vl6180x",
            "aedr8300", "tcd1103", "tsl1410r", "tsl1412s",
        }
        unknown = sorted(set(cfg) - known)
        conflicts = self.validate_config()
        message = ["IMPORT SUCCEEDED", ""]
        if conflicts:
            message.extend((
                f"CONFIGURATION CONFLICTS FOUND: {len(conflicts)}",
                "The file was imported unchanged. Conflicts must be resolved before a generated copy can be saved.",
                "",
                *[f"  • {item}" for item in conflicts],
            ))
        else:
            message.append("No pin conflicts were found and no changes were made.")
        if unknown:
            message.extend(("", "Sections not yet displayed by this prototype:", *[f"  • {name} (preserved in parsed data)" for name in unknown]))
        self._set_text(self.messages, "\n".join(message))
        self._set_text(self.raw, json.dumps(cfg, indent=2, ensure_ascii=False))
        self._refresh_generated()
        if conflicts:
            if self.current_path:
                self.status.set(f"Imported with {len(conflicts)} configuration conflict(s) — see Import messages")
            else:
                self.status.set(f"New configuration has {len(conflicts)} item(s) to finish — see Import messages")

    def _refresh_generated(self) -> None:
        self._set_text(self.generated, self.generate_text())

    def _draw_pin_map(self) -> None:
        canvas = self.pin_map
        canvas.delete("all")
        center_x = 390
        canvas.create_text(center_x, 18, text="Pico GPIO assignments", font=("Segoe UI", 13, "bold"))
        canvas.create_text(center_x, 42, text="Green input  •  Orange output  •  Blue I²C  •  Purple analog  •  Teal interrupt  •  Red conflict", font=("Segoe UI", 8), fill="#555555")
        image_path = Path(__file__).with_name("assets") / "PicoDiagram.png"
        try:
            self.pico_image = tk.PhotoImage(file=str(image_path))
            canvas.create_image(center_x, 355, image=self.pico_image)
        except tk.TclError:
            canvas.create_rectangle(center_x-70, 88, center_x+70, 622, fill="#2b7d54", outline="#17583a", width=2)
            canvas.create_text(center_x, 355, text="RASPBERRY PI\nPICO", fill="white", font=("Segoe UI", 14, "bold"), justify="center")
        assignments: dict[int, list[tuple[str, str]]] = {}
        def add(gp, label, colour):
            if isinstance(gp, int): assignments.setdefault(gp, []).append((label, colour))
        for row in self._group_buttons(self.config_data.get("buttons", [])):
            button = row.get("normal") or row.get("always") or row.get("shift_source") or {}
            name = button.get("name", "Button")
            add(row.get("gp"), ("SHIFT: " if row.get("is_shift") else "Button: ") + name, "#59b83b")
        for number, output in enumerate(self.config_data.get("outputs", []), 1):
            dev = output.get("device", {})
            if dev.get("type") == "gpio": add(dev.get("gp"), f"Output #{number}: {output.get('name', 'unnamed')}", "#ed8b23")
        for bus in ("i2c0", "i2c1"):
            data = self.config_data.get(bus, {})
            if data.get("enable", True):
                add(data.get("sda"), f"{bus.upper()} SDA", "#2589cc"); add(data.get("scl"), f"{bus.upper()} SCL", "#2589cc")
        adc = self.config_data.get("pico_adc", {})
        add(adc.get("gpio"), "Pico ADC / Plunger", "#9a57c7")
        for device in ("lis3dh", "mxc6655xa", "mc3416", "vcnl4010", "vl6180x"):
            data = self.config_data.get(device, {})
            add(data.get("interrupt"), f"{device.upper()} interrupt", "#00a0a0")
        add(self.config_data.get("ads1115", {}).get("ready"), "ADS1115 READY", "#00a0a0")

        # Physical header row numbers are important: GPIO rows are separated
        # by GND and power pins, so simple even GPIO spacing doesn't line up.
        left = {0:0, 1:1, 2:3, 3:4, 4:5, 5:6, 6:8, 7:9, 8:10, 9:11,
                10:13, 11:14, 12:15, 13:16, 14:18, 15:19}
        right = {28:6, 27:8, 26:9, 22:11, 21:13, 20:14, 19:15, 18:16,
                 17:18, 16:19}
        def draw_side(gpios, x_pin, x_text, anchor, top, spacing):
            for gp, physical_row in gpios.items():
                y = top + physical_row * spacing
                entries = assignments.get(gp, [])
                colour = "#d64b3c" if len(entries) > 1 else (entries[0][1] if entries else "#999999")
                label = " | ".join(v[0] for v in entries) if entries else "Available"
                canvas.create_oval(x_pin-5, y-5, x_pin+5, y+5, fill=colour, outline="")
                canvas.create_text(x_text, y, text=f"GP{gp}  {label}" if anchor == "w" else f"{label}  GP{gp}", anchor=anchor, fill=colour if entries else "#777777", font=("Segoe UI", 8, "bold" if entries else "normal"))
        draw_side(left, center_x-140, center_x-153, "e", 102, 26.25)
        draw_side(right, center_x+140, center_x+153, "w", 102, 26.25)

    @staticmethod
    def _settings(data: dict) -> str:
        return ", ".join(f"{key}={value}" for key, value in data.items())

    @staticmethod
    def _configured_type(cfg, names, preferred=None):
        if preferred in names:
            return preferred
        return next((name for name in names if name in cfg), None)

    def generate_text(self) -> str:
        banner = (
            "// Generated by Pinscape Pico JSON Generator\n"
            "// Import this COPY into the official Pinscape Pico Config Tool for validation and testing.\n"
        )
        return banner + json.dumps(self.config_data, indent=2, ensure_ascii=False) + "\n"

    def save_generated(self) -> None:
        if not self.config_data:
            messagebox.showinfo("Nothing to save", "Open or create a configuration first.")
            return
        conflicts = self.validate_config()
        if conflicts:
            messagebox.showerror(
                "Resolve configuration conflicts",
                "The generated configuration cannot be saved yet:\n\n" + "\n".join(f"• {item}" for item in conflicts),
            )
            self.tabs.select(self.messages.master)
            return
        initial = "pinscape-generated.txt"
        if self.current_path:
            initial = self.current_path.stem + " - generated.txt"
        filename = filedialog.asksaveasfilename(
            title="Save generated configuration copy",
            defaultextension=".txt",
            initialfile=initial,
            filetypes=(("Text configuration", "*.txt"), ("All files", "*.*")),
        )
        if not filename:
            return
        target = Path(filename)
        if self.current_path and target.resolve() == self.current_path.resolve():
            messagebox.showerror("Source protected", "Choose a different filename. The imported source will not be overwritten.")
            return
        target.write_text(self.generate_text(), encoding="utf-8")
        self.status.set(f"Generated copy saved to {target}")

    def _shift_bits(self) -> int:
        for button in self.config_data.get("buttons", []):
            if button.get("type") == "shift" and isinstance(button.get("shiftBits"), int):
                return button["shiftBits"]
        return 1

    def gpio_uses(self, exclude_button_gp=None, exclude_output_index=None) -> dict[int, list[str]]:
        uses: dict[int, list[str]] = {}
        def add(gp, label):
            if isinstance(gp, int):
                uses.setdefault(gp, []).append(label)

        for button in self.config_data.get("buttons", []):
            gp = button.get("source", {}).get("gp")
            if gp != exclude_button_gp:
                add(gp, "button input")
        for index, output in enumerate(self.config_data.get("outputs", [])):
            if index != exclude_output_index:
                add(output.get("device", {}).get("gp"), f"output #{index + 1}")
        for bus in ("i2c0", "i2c1"):
            if bus in self.config_data:
                add(self.config_data[bus].get("sda"), f"{bus.upper()} SDA")
                add(self.config_data[bus].get("scl"), f"{bus.upper()} SCL")
        add(self.config_data.get("pico_adc", {}).get("gpio"), "Pico ADC / plunger")
        for device in ("lis3dh", "mxc6655xa", "mc3416", "vcnl4010", "vl6180x"):
            add(self.config_data.get(device, {}).get("interrupt"), f"{device.upper()} interrupt")
        add(self.config_data.get("ads1115", {}).get("ready"), "ADS1115 READY")
        aedr = self.config_data.get("aedr8300", {})
        add(aedr.get("channelA"), "AEDR-8300 channel A"); add(aedr.get("channelB"), "AEDR-8300 channel B")
        tcd = self.config_data.get("tcd1103", {})
        for key in ("fm", "icg", "sh", "os"): add(tcd.get(key), f"TCD1103 {key.upper()}")
        for device in ("tsl1410r", "tsl1412s"):
            data=self.config_data.get(device,{})
            for key in ("si","clk","so"): add(data.get(key), f"{device.upper()} {key.upper()}")
        return uses

    def validate_config(self) -> list[str]:
        """Find physical pin conflicts without changing imported data."""
        assignments: dict[int, list[str]] = {}
        def add(gp, label):
            if isinstance(gp, int) and gp >= 0:
                labels = assignments.setdefault(gp, [])
                if label not in labels:
                    labels.append(label)

        # Multiple normal/shifted mappings on one GPIO are one physical button.
        button_gpios = {}
        for button in self.config_data.get("buttons", []):
            source = button.get("source", {})
            if source.get("type") == "gpio" and isinstance(source.get("gp"), int):
                button_gpios.setdefault(source["gp"], []).append(button.get("name", "unnamed"))
        for gp, names in button_gpios.items():
            add(gp, "button input (" + ", ".join(names[:2]) + ("…" if len(names) > 2 else "") + ")")

        for index, output in enumerate(self.config_data.get("outputs", []), 1):
            device = output.get("device", {})
            if device.get("type") == "gpio":
                add(device.get("gp"), f"output #{index} ({output.get('name', 'unnamed')})")
        for bus in ("i2c0", "i2c1"):
            data = self.config_data.get(bus, {})
            add(data.get("sda"), f"{bus.upper()} SDA")
            add(data.get("scl"), f"{bus.upper()} SCL")
        add(self.config_data.get("pico_adc", {}).get("gpio"), "Pico ADC / plunger")
        for device in ("lis3dh", "mxc6655xa", "mc3416", "vcnl4010", "vl6180x"):
            add(self.config_data.get(device, {}).get("interrupt"), f"{device.upper()} interrupt")
        add(self.config_data.get("ads1115", {}).get("ready"), "ADS1115 READY")
        aedr=self.config_data.get("aedr8300",{})
        add(aedr.get("channelA"),"AEDR-8300 channel A"); add(aedr.get("channelB"),"AEDR-8300 channel B")
        tcd=self.config_data.get("tcd1103",{})
        for key in ("fm","icg","sh","os"): add(tcd.get(key),f"TCD1103 {key.upper()}")
        for device in ("tsl1410r","tsl1412s"):
            data=self.config_data.get(device,{})
            for key in ("si","clk","so"): add(data.get(key),f"{device.upper()} {key.upper()}")

        conflicts = []
        shift_gpios = sorted({
            button.get("source", {}).get("gp")
            for button in self.config_data.get("buttons", [])
            if button.get("type") == "shift" and isinstance(button.get("source", {}).get("gp"), int)
        })
        if len(shift_gpios) > 1:
            conflicts.append("Multiple Shift buttons are assigned: " + ", ".join(f"GP{gp}" for gp in shift_gpios))
        for device in ("lis3dh","mxc6655xa","mc3416","ads1115","vcnl4010","vl6180x"):
            if device in self.config_data:
                bus=self.config_data[device].get("i2c")
                if bus not in (0,1) or f"i2c{bus}" not in self.config_data:
                    conflicts.append(f"{device.upper()} requires configured I2C bus {bus}")
        for device in ("lis3dh", "mxc6655xa", "mc3416"):
            data = self.config_data.get(device, {})
            if "interrupt" in data and (not isinstance(data["interrupt"], int) or data["interrupt"] < 0):
                conflicts.append(f"{device.upper()} interrupt must be an exposed GPIO or omitted when unwired; do not use -1")
        adc_checks=(("pico_adc","gpio"),("tcd1103","os"),("tsl1410r","so"),("tsl1412s","so"))
        for device,key in adc_checks:
            if device in self.config_data and self.config_data[device].get(key) not in (26,27,28):
                conflicts.append(f"{device.upper()} {key.upper()} must use ADC-capable GP26, GP27, or GP28")
        for bus in ("i2c0","i2c1"):
            if bus in self.config_data:
                unit=int(bus[-1]); sda=self.config_data[bus].get("sda"); scl=self.config_data[bus].get("scl")
                valid={0:({0,4,8,12,16,20},{1,5,9,13,17,21}),1:({2,6,10,14,18,26},{3,7,11,15,19,27})}
                if sda not in valid[unit][0] or scl not in valid[unit][1]:
                    conflicts.append(f"{bus.upper()} has invalid SDA/SCL pins GP{sda}/GP{scl}")
        for gp, labels in sorted(assignments.items()):
            if len(labels) > 1:
                conflicts.append(f"GP{gp} is assigned to " + " and ".join(labels))
        return conflicts

    def set_single_shift(self, selected_gp: int) -> None:
        """Make selected_gp the only Shift source while preserving old Shift actions."""
        bits = self._shift_bits()
        buttons = self.config_data.get("buttons", [])
        old_shift_gpios = {
            b.get("source", {}).get("gp") for b in buttons
            if b.get("type") == "shift" and isinstance(b.get("source", {}).get("gp"), int)
        }

        # A shifted action on the Shift source could fire while the Shift button
        # itself is being pressed. Park it in the builder until this GPIO is
        # changed back to a normal button.
        parked = [
            b for b in buttons
            if b.get("source", {}).get("gp") == selected_gp
            and b.get("type") != "shift"
            and b.get("shiftMask") is not None
            and b.get("shiftBits", 0) != 0
        ]
        if parked:
            self.parked_shifted[selected_gp] = json.loads(json.dumps(parked))
            buttons[:] = [b for b in buttons if b not in parked]

        chosen = None
        # Prefer the normal/base mapping on the selected GPIO.
        for button in buttons:
            if button.get("source", {}).get("gp") == selected_gp:
                if button.get("shiftMask") is None or button.get("shiftBits", 0) == 0:
                    chosen = button
                    break
        if chosen is None:
            chosen = next((b for b in buttons if b.get("source", {}).get("gp") == selected_gp), None)
        if chosen is None:
            return

        for button in buttons:
            was_shift = button.get("type") == "shift"
            if was_shift:
                button.pop("type", None)
                button.pop("shiftBits", None)
            if button is chosen:
                button["type"] = "shift"
                button["shiftBits"] = bits
                button.pop("shiftMask", None)
            elif was_shift:
                # The former Shift button keeps its regular action as an unshifted mapping.
                button["shiftMask"] = bits
                button["shiftBits"] = 0

        # Restore the former Shift button's parked alternate action now that it
        # is once again an ordinary physical button.
        for gp in old_shift_gpios - {selected_gp}:
            if gp in self.parked_shifted:
                buttons.extend(self.parked_shifted.pop(gp))

    def available_gpio(self, exclude_button_gp=None, exclude_output_index=None) -> list[int]:
        # Standard Pico header GPIO. GP23-25 and GP29 are internal/not normally exposed.
        exposed = list(range(23)) + [26, 27, 28]
        used = self.gpio_uses(exclude_button_gp, exclude_output_index)
        return [gp for gp in exposed if gp not in used]

    def _group_buttons(self, buttons: list[dict]) -> list[dict]:
        rows: list[dict] = []
        by_gp: dict[int, dict] = {}
        for index, button in enumerate(buttons):
            source = button.get("source", {})
            if source.get("type") != "gpio" or not isinstance(source.get("gp"), int):
                # Preserve non-GPIO and unknown input sources as individual rows.
                gp = -(index + 1)
            else:
                gp = source["gp"]
            row = by_gp.get(gp)
            if row is None:
                row = {"gp": gp, "indices": [], "is_shift": False}
                by_gp[gp] = row
                rows.append(row)
            row["indices"].append(index)
            kind = self._condition_kind(button)
            if kind == "shift-source":
                row["is_shift"] = True
                row["shift_source"] = button
                # A shift input can still have a regular key action.
                row.setdefault("normal", button)
            elif kind in ("normal", "shifted", "always"):
                if kind in row:
                    row.setdefault("extras", []).append(button)
                else:
                    row[kind] = button
        return rows

    @staticmethod
    def _display_ms(value) -> str:
        return f"{value} ms" if value is not None else "—"

    def _row_options(self, row: dict) -> str:
        button = row.get("normal") or row.get("always") or row.get("shift_source") or row.get("shifted") or {}
        source = button.get("source", {})
        parts = []
        if "debounceTimeOn" in source:
            parts.append(f"ON {source['debounceTimeOn']} µs")
        if "debounceTimeOff" in source:
            parts.append(f"OFF {source['debounceTimeOff']} µs")
        if "tPulse" in button:
            parts.append(f"Pulse {button['tPulse']}")
        if row.get("extras"):
            parts.append(f"+{len(row['extras'])} advanced")
        return ", ".join(parts) or "Default"

    @staticmethod
    def _usage_for_action(button: dict | None) -> str:
        if not button:
            return "—"
        action = button.get("action", {})
        if action.get("type") == "nightmode":
            return "Night Mode"
        if action.get("type") != "key":
            return action.get("type", "—")
        key = action.get("key", "").lower()
        usages = {
            "1": "Start Game", "2": "Extra Ball", "5": "Coin In",
            "enter": "Select / Launch Ball", "escape": "Exit / Menu",
            "left shift": "Left Flipper", "right shift": "Right Flipper",
            "left ctrl": "Left MagnaSave", "right ctrl": "Right MagnaSave",
            "space": "Forward Nudge", "f13": "Volume Down", "f18": "Volume Up",
            "f14": "Table Volume Up", "f15": "Table Volume Down",
            "left alt": "Shift / Alternate functions",
        }
        return usages.get(key, f"Key {action.get('key', '?')}")

    def _usage(self, normal: dict | None, shifted: dict | None) -> str:
        values = [self._usage_for_action(normal)]
        if shifted:
            values.append(self._usage_for_action(shifted))
        return " / ".join(values)

    def configure_i2c(self):
        if not self.config_data:
            messagebox.showinfo("Open a configuration", "Open a configuration first.")
            return
        dialog = I2CDialog(self, self.config_data)
        self.wait_window(dialog)
        if dialog.result:
            bus, data = dialog.result
            self.config_data.pop("i2c0", None)
            self.config_data.pop("i2c1", None)
            if bus:
                self.config_data[bus] = data
            self._populate()
            self.tabs.select(self.devices.master)

    def configure_usb(self):
        if not self.config_data:
            messagebox.showinfo("Open a configuration", "Open or create a configuration first.")
            return
        dialog = USBDialog(self, self.config_data)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        keyboard, gamepad, open_pin = dialog.result
        if keyboard: self.config_data["keyboard"] = {"enable": True}
        else: self.config_data.pop("keyboard", None)
        if gamepad:
            old = self.config_data.get("gamepad", {})
            self.config_data["gamepad"] = {
                "enable": True,
                "x": old.get("x", "nudge.x"), "y": old.get("y", "nudge.y"),
                "z": old.get("z", "plunger.z"),
            }
        else: self.config_data.pop("gamepad", None)
        if open_pin: self.config_data["openPinballDevice"] = {"enable": True}
        else: self.config_data.pop("openPinballDevice", None)
        self._populate()
        self.tabs.select(self.devices.master)
        self.status.set("USB interfaces updated")

    def configure_nudge(self):
        if not self.config_data:
            messagebox.showinfo("Open a configuration", "Open a configuration first.")
            return
        dialog = NudgeDialog(self, self.config_data)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        kind, device, nudge = dialog.result
        for key in ("lis3dh", "mxc6655xa", "mc3416"):
            self.config_data.pop(key, None)
        if kind:
            self.config_data[kind] = device
            self.config_data["nudge"] = nudge
            self._ensure_i2c_bus(device.get("i2c"))
        else:
            self.config_data.pop("nudge", None)
        self._populate()
        self.tabs.select(self.devices.master)

    def configure_plunger(self):
        if not self.config_data:
            messagebox.showinfo("Open a configuration", "Open a configuration first.")
            return
        dialog = PlungerDialog(self, self.config_data)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        kind, device, plunger = dialog.result
        types = ("pico_adc", "ads1115", "vcnl4010", "vl6180x", "aedr8300", "tcd1103", "tsl1410r", "tsl1412s")
        for key in types:
            self.config_data.pop(key, None)
        if kind:
            self.config_data[kind] = device
            self.config_data["plunger"] = plunger
            if kind in ("ads1115", "vcnl4010", "vl6180x"):
                self._ensure_i2c_bus(device.get("i2c"))
        else:
            self.config_data.pop("plunger", None)
        self._populate()
        self.tabs.select(self.devices.master)

    def _ensure_i2c_bus(self, number) -> None:
        """Add a safe default bus when a newly selected device requires it."""
        if number not in (0, 1):
            return
        key = f"i2c{number}"
        if key not in self.config_data:
            sda, scl = ((0, 1) if number == 0 else (18, 19))
            self.config_data[key] = {"enable": True, "sda": sda, "scl": scl, "speed": 400000}

    def configure_fx(self):
        if not self.config_data:
            messagebox.showinfo("Open a configuration", "Open a configuration first.")
            return
        dialog = FXDialog(self, self.config_data)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        mode = dialog.result
        xinput = self.config_data.setdefault("xInput", {})
        if mode != "Disabled":
            xinput["enable"] = True
            xinput["xRight"] = "negate(plunger.z)"
            if mode == "Pinball FX plunger + nudge":
                xinput["xLeft"] = "nudge.x"
                xinput["yLeft"] = "nudge.y"
            else:
                if xinput.get("xLeft") == "nudge.x": xinput.pop("xLeft", None)
                if xinput.get("yLeft") == "nudge.y": xinput.pop("yLeft", None)
        else:
            if xinput.get("xRight") in ("plunger.z", "negate(plunger.z)"):
                xinput.pop("xRight", None)
            if xinput.get("xLeft") == "nudge.x": xinput.pop("xLeft", None)
            if xinput.get("yLeft") == "nudge.y": xinput.pop("yLeft", None)
            if not any(k in xinput for k in ("xLeft", "yLeft", "xRight", "yRight", "leftTrigger", "rightTrigger")):
                self.config_data.pop("xInput", None)
        self._populate()
        self.tabs.select(self.devices.master)
        self.status.set("Pinball FX XInput plunger setting updated")

    def _condition_kind(self, button: dict) -> str:
        if button.get("type") == "shift":
            return "shift-source"
        if "shiftMask" not in button:
            return "always"
        return "shifted" if button.get("shiftBits", 0) else "normal"

    def edit_selected_input(self) -> None:
        selected = self.inputs.selection()
        if not selected:
            messagebox.showinfo("Select an input", "Select an input mapping first.")
            return
        self.edit_button_row(self.inputs.index(selected[0]))

    def edit_button_row(self, row_index: int | None) -> None:
        if not self.config_data:
            messagebox.showinfo("Open a configuration", "Open a configuration before adding buttons.")
            return
        row = self.input_rows[row_index] if row_index is not None else None
        if row and row.get("extras"):
            messagebox.showwarning(
                "Advanced mappings present",
                "This GPIO has additional mappings that the simple row editor cannot represent yet. "
                "They will be preserved, but review Generated Configuration after editing.",
            )
        dialog = ButtonRowDialog(self, row, self._shift_bits())
        self.wait_window(dialog)
        if dialog.result is None:
            return
        buttons = self.config_data.setdefault("buttons", [])
        becoming_shift = any(b.get("type") == "shift" for b in dialog.result)
        if row is not None and becoming_shift and row.get("shifted"):
            self.parked_shifted[row["gp"]] = [json.loads(json.dumps(row["shifted"]))]
        if row is None:
            buttons.extend(dialog.result)
        else:
            old_indices = set(row["indices"])
            preserved = [b for i, b in enumerate(buttons) if i not in old_indices]
            preserved.extend(row.get("extras", []))
            insert_at = min(old_indices)
            self.config_data["buttons"] = preserved[:insert_at] + dialog.result + preserved[insert_at:]
        if row is not None and not becoming_shift and row["gp"] in self.parked_shifted:
            has_shifted = any(
                b.get("source", {}).get("gp") == row["gp"]
                and b.get("shiftMask") is not None and b.get("shiftBits", 0) != 0
                for b in self.config_data["buttons"]
            )
            if not has_shifted:
                self.config_data["buttons"].extend(self.parked_shifted.pop(row["gp"]))
        new_shift = next((b for b in dialog.result if b.get("type") == "shift"), None)
        if new_shift:
            self.set_single_shift(new_shift.get("source", {}).get("gp"))
        self._populate()
        self.tabs.select(self.inputs.master)
        self.status.set("Button row updated in generated configuration")

    def make_selected_shift(self) -> None:
        selected = self.inputs.selection()
        if not selected:
            messagebox.showinfo("Select a button", "Select the physical button to use as Shift.")
            return
        selected_row = self.input_rows[self.inputs.index(selected[0])]
        self.set_single_shift(selected_row["gp"])
        self._populate()
        self.tabs.select(self.inputs.master)

    def edit_input(self, index: int | None, initial_kind: str | None) -> None:
        if not self.config_data:
            messagebox.showinfo("Open a configuration", "Open a configuration before adding inputs.")
            return
        buttons = self.config_data.setdefault("buttons", [])
        original = buttons[index] if index is not None else {}
        dialog = InputDialog(self, original, initial_kind or self._condition_kind(original), self._shift_bits())
        self.wait_window(dialog)
        if dialog.result is None:
            return
        if index is None:
            buttons.append(dialog.result)
        else:
            buttons[index] = dialog.result
        self._populate()
        self.tabs.select(self.inputs.master)
        self.status.set("Input mapping updated in generated copy")

    def remove_selected_input(self) -> None:
        selected = self.inputs.selection()
        if not selected:
            return
        row = self.input_rows[self.inputs.index(selected[0])]
        name = (row.get("normal") or row.get("always") or row.get("shift_source") or {}).get("name", f"GP{row['gp']}")
        if messagebox.askyesno("Remove button", f"Remove all normal and shifted mappings for {name!r}?"):
            indices = set(row["indices"])
            self.config_data["buttons"] = [b for i, b in enumerate(self.config_data["buttons"]) if i not in indices]
            self._populate()

    def edit_selected_output(self) -> None:
        selected = self.outputs.selection()
        if not selected:
            messagebox.showinfo("Select an output", "Select an output mapping first.")
            return
        self.edit_output(self.outputs.index(selected[0]))

    def edit_output(self, index: int | None) -> None:
        if not self.config_data:
            messagebox.showinfo("Open a configuration", "Open a configuration before adding outputs.")
            return
        outputs = self.config_data.setdefault("outputs", [])
        original = outputs[index] if index is not None else {}
        dialog = OutputDialog(self, original, index)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        if index is None:
            outputs.append(dialog.result)
        else:
            outputs[index] = dialog.result
        self._populate()
        self.tabs.select(self.outputs.master)
        self.status.set("Output mapping updated in generated copy")

    def remove_selected_output(self) -> None:
        selected = self.outputs.selection()
        if not selected:
            return
        index = self.outputs.index(selected[0])
        name = self.config_data["outputs"][index].get("name", "this output")
        if messagebox.askyesno("Remove output", f"Remove {name!r} from the generated configuration?"):
            del self.config_data["outputs"][index]
            self._populate()

    @staticmethod
    def _source(source: dict) -> str:
        kind = source.get("type", "")
        if kind == "gpio":
            return f"GPIO {source.get('gp', '?')}" + (" (PWM)" if source.get("pwm") else "")
        return kind or json.dumps(source)

    @staticmethod
    def _hex(value) -> str:
        return hex(value) if isinstance(value, int) else str(value)

    def _action(self, action: dict) -> str:
        kind = action.get("type", "unknown")
        if kind == "key":
            return f"Key: {action.get('key', '?')}"
        if kind == "macro":
            steps = [self._action(step.get("action", {})) for step in action.get("steps", [])]
            return "Macro: " + " → ".join(steps)
        return kind

    @staticmethod
    def _timing(button: dict, source: dict) -> str:
        values = []
        for key in ("debounceTimeOn", "debounceTimeOff"):
            if key in source:
                values.append(f"{key}={source[key]}")
        if "tPulse" in button:
            values.append(f"tPulse={button['tPulse']}")
        if button.get("type"):
            values.append(f"type={button['type']}")
        return ", ".join(values)

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")


class FormDialog(tk.Toplevel):
    def __init__(self, parent, title: str):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.body = ttk.Frame(self, padding=14)
        self.body.pack(fill="both", expand=True)
        self.result = None
        self.row = 0

    def field(self, label: str, variable, values=None, width=34):
        ttk.Label(self.body, text=label).grid(row=self.row, column=0, sticky="w", padx=(0, 12), pady=4)
        if values is None:
            widget = ttk.Entry(self.body, textvariable=variable, width=width)
        else:
            widget = ttk.Combobox(self.body, textvariable=variable, values=values, state="readonly", width=width - 2)
        widget.grid(row=self.row, column=1, sticky="ew", pady=4)
        self.row += 1
        return widget

    def buttons(self, save_command):
        bar = ttk.Frame(self.body)
        bar.grid(row=self.row, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Apply", command=save_command).pack(side="right", padx=(0, 8))
        self.bind("<Escape>", lambda _e: self.destroy())

    @staticmethod
    def number(value: str, label: str, optional=False) -> int | None:
        value = value.strip()
        if optional and not value:
            return None
        try:
            return int(value, 0)
        except ValueError as exc:
            raise ValueError(f"{label} must be a whole number") from exc


class NewConfigDialog(FormDialog):
    def __init__(self, parent):
        super().__init__(parent, "New Pinscape configuration")
        self.name = tk.StringVar(value="Main Pico")
        self.unit = tk.StringVar(value="1")
        self.field("Unit name", self.name)
        self.field("Unit number", self.unit)
        ttk.Label(
            self.body,
            text="Starts safely with Keyboard enabled. Buttons, outputs, I²C,\nsensors, gamepads, Open Pinball, and XInput remain off.",
            foreground="#555555",
        ).grid(row=self.row, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.row += 1
        self.buttons(self.save)

    def save(self):
        try:
            unit = self.number(self.unit.get(), "Unit number")
        except ValueError as exc:
            messagebox.showerror("Invalid unit", str(exc), parent=self)
            return
        name = self.name.get().strip()
        if not name:
            messagebox.showerror("Invalid unit", "Unit name cannot be blank", parent=self)
            return
        self.result = (name, unit)
        self.destroy()


class USBDialog(FormDialog):
    def __init__(self, parent, cfg):
        super().__init__(parent, "USB interfaces")
        self.keyboard = tk.BooleanVar(value=cfg.get("keyboard", {}).get("enable", False))
        self.gamepad = tk.BooleanVar(value=cfg.get("gamepad", {}).get("enable", False))
        self.open_pin = tk.BooleanVar(value=cfg.get("openPinballDevice", {}).get("enable", False))
        ttk.Label(self.body, text="Enable only the interfaces your games use.", foreground="#555555").grid(row=self.row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.row += 1
        for text, variable in (
            ("Keyboard", self.keyboard),
            ("Generic USB gamepad (nudge X/Y and plunger Z)", self.gamepad),
            ("Open Pinball Device", self.open_pin),
        ):
            ttk.Checkbutton(self.body, text=text, variable=variable).grid(row=self.row, column=0, columnspan=2, sticky="w", pady=4)
            self.row += 1
        ttk.Label(self.body, text="Pinball FX Xbox emulation is configured separately.", foreground="#555555").grid(row=self.row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.row += 1
        self.buttons(self.save)

    def save(self):
        self.result = (self.keyboard.get(), self.gamepad.get(), self.open_pin.get())
        self.destroy()


class I2CDialog(FormDialog):
    def __init__(self, parent, cfg):
        super().__init__(parent, "I²C bus")
        existing = "i2c1" if "i2c1" in cfg else ("i2c0" if "i2c0" in cfg else "None")
        data = cfg.get(existing, {})
        self.bus = tk.StringVar(value=existing)
        self.sda = tk.StringVar(value=str(data.get("sda", 18 if existing == "i2c1" else 0)))
        self.scl = tk.StringVar(value=str(data.get("scl", 19 if existing == "i2c1" else 1)))
        self.speed = tk.StringVar(value=str(data.get("speed", 400000)))
        self.field("Bus", self.bus, ("None", "i2c0", "i2c1"))
        self.field("SDA GPIO", self.sda)
        self.field("SCL GPIO", self.scl)
        self.field("Speed", self.speed)
        self._last_bus = existing
        self.bus.trace_add("write", self._bus_changed)
        self.buttons(self.save)

    def _bus_changed(self, *_):
        bus = self.bus.get()
        if bus == self._last_bus: return
        if bus == "i2c0": self.sda.set("0"); self.scl.set("1")
        elif bus == "i2c1": self.sda.set("18"); self.scl.set("19")
        self._last_bus = bus

    def save(self):
        if self.bus.get() == "None":
            self.result = (None, {})
            self.destroy()
            return
        try:
            sda = self.number(self.sda.get(), "SDA GPIO")
            scl = self.number(self.scl.get(), "SCL GPIO")
            speed = self.number(self.speed.get(), "Speed")
        except ValueError as exc:
            messagebox.showerror("Invalid I²C bus", str(exc), parent=self); return
        valid = {
            "i2c0": ({0, 4, 8, 12, 16, 20}, {1, 5, 9, 13, 17, 21}),
            "i2c1": ({2, 6, 10, 14, 18, 26}, {3, 7, 11, 15, 19, 27}),
        }
        if sda not in valid[self.bus.get()][0] or scl not in valid[self.bus.get()][1]:
            messagebox.showerror("Invalid I²C pins", f"GP{sda}/GP{scl} is not a valid {self.bus.get().upper()} SDA/SCL pair.", parent=self); return
        self.result = (self.bus.get(), {"enable": True, "sda": sda, "scl": scl, "speed": speed})
        self.destroy()


class FXDialog(FormDialog):
    def __init__(self, parent, cfg):
        super().__init__(parent, "Pinball FX / XInput plunger")
        current = cfg.get("xInput", {})
        enabled = current.get("enable") and current.get("xRight") == "negate(plunger.z)"
        full = enabled and current.get("xLeft") == "nudge.x" and current.get("yLeft") == "nudge.y"
        selected = "Pinball FX plunger + nudge" if full else ("Pinball FX plunger only" if enabled else "Disabled")
        self.mode = tk.StringVar(value=selected)
        self.field("XInput setup", self.mode, ("Disabled", "Pinball FX plunger only", "Pinball FX plunger + nudge"))
        ttk.Label(self.body, text="Pinball FX uses reversed right-stick X for the plunger and\nleft-stick X/Y for nudge. Keyboard buttons can remain enabled.", foreground="#555555").grid(row=self.row, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.row += 1
        self.buttons(self.save)

    def save(self):
        self.result = self.mode.get()
        self.destroy()


class NudgeDialog(FormDialog):
    TYPES = ("None", "LIS3DH", "MXC6655XA", "MC3416")
    def __init__(self, parent, cfg):
        super().__init__(parent, "Nudge sensor")
        current = next((x for x in ("lis3dh", "mxc6655xa", "mc3416") if x in cfg), None)
        data = cfg.get(current, {}) if current else {}
        self.kind = tk.StringVar(value=current.upper() if current else "None")
        self.bus = tk.StringVar(value=str(data.get("i2c", 1)))
        self.addr = tk.StringVar(value=hex(data.get("addr", 0x19 if current == "lis3dh" else 0x4C)))
        intr = data.get("interrupt")
        self.interrupt = tk.StringVar(value="" if intr is None or intr == -1 else str(intr))
        self.grange = tk.StringVar(value=str(data.get("gRange", 2)))
        nudge = cfg.get("nudge", {})
        self.x = tk.StringVar(value=nudge.get("x", "+X")); self.y = tk.StringVar(value=nudge.get("y", "+Y")); self.z = tk.StringVar(value=nudge.get("z", "+Z"))
        self.field("Sensor", self.kind, self.TYPES)
        self.field("I²C bus number", self.bus, ("0", "1"))
        self.addr_widget = self.field("I²C address", self.addr)
        self.field("Interrupt GPIO (blank if unwired)", self.interrupt)
        self.field("Range (g)", self.grange, ("2", "4", "8"))
        axes = ("+X", "-X", "+Y", "-Y", "+Z", "-Z")
        self.field("Logical X", self.x, axes); self.field("Logical Y", self.y, axes); self.field("Logical Z", self.z, axes)
        ttk.Label(self.body, text="Blank interrupt uses polling. A wired interrupt is preferred;\nGP26 matches the standard cabinet configuration used for this builder.", foreground="#555555").grid(row=self.row, column=0, columnspan=2, sticky="w", pady=(8, 0)); self.row += 1
        self._last_kind = self.kind.get()
        self.kind.trace_add("write", self._kind_changed)
        self._kind_changed()
        self.buttons(self.save)

    def _kind_changed(self, *_):
        kind = self.kind.get()
        if kind != self._last_kind:
            if kind == "LIS3DH": self.addr.set("0x19")
            elif kind == "MC3416": self.addr.set("0x4c")
            elif kind == "MXC6655XA": self.addr.set("")
            self._last_kind = kind
        self.addr_widget.configure(state="disabled" if kind in ("None", "MXC6655XA") else "normal")

    def save(self):
        if self.kind.get() == "None": self.result = (None, {}, {}); self.destroy(); return
        try:
            bus=self.number(self.bus.get(),"I²C bus"); intr=self.number(self.interrupt.get(),"Interrupt",optional=True); gr=self.number(self.grange.get(),"Range")
            addr=self.number(self.addr.get(),"Address") if self.kind.get() in ("LIS3DH", "MC3416") else None
        except ValueError as exc: messagebox.showerror("Invalid nudge sensor", str(exc), parent=self); return
        kind=self.kind.get().lower(); device={"i2c":bus,"gRange":gr}
        if intr is not None and intr >= 0: device["interrupt"] = intr
        if kind in ("lis3dh","mc3416"): device["addr"]=addr
        self.result=(kind,device,{"source":kind,"x":self.x.get(),"y":self.y.get(),"z":self.z.get()}); self.destroy()


class PlungerDialog(FormDialog):
    LABELS = {
        "Pico ADC": ("GPIO", None, None, None),
        "ADS1115": ("I²C bus", "Address", "READY GPIO (blank if unwired)", "Channel 0-3"),
        "VCNL4010": ("I²C bus", "IR current mA", "Interrupt GPIO (blank if unwired)", "Power law"),
        "VL6180X": ("I²C bus", "Interrupt GPIO (blank if unwired)", None, None),
        "AEDR-8300": ("Channel A GPIO", "Channel B GPIO", "Auto-zero time ms", None),
        "TCD1103": ("FM GPIO", "ICG GPIO", "SH GPIO", "OS ADC GPIO"),
        "TSL1410R": ("SI GPIO", "CLK GPIO", "SO ADC GPIO", None),
        "TSL1412S": ("SI GPIO", "CLK GPIO", "SO ADC GPIO", None),
    }
    KEY = {"Pico ADC":"pico_adc","ADS1115":"ads1115","VCNL4010":"vcnl4010","VL6180X":"vl6180x","AEDR-8300":"aedr8300","TCD1103":"tcd1103","TSL1410R":"tsl1410r","TSL1412S":"tsl1412s"}
    DEFAULTS = {
        "Pico ADC": (28,), "ADS1115": (1, "0x48", "", 0),
        "VCNL4010": (1, 200, "", 2), "VL6180X": (1, ""),
        "AEDR-8300": (20, 21, 5000), "TCD1103": (19, 20, 21, 27),
        "TSL1410R": (18, 19, 26), "TSL1412S": (18, 19, 26),
    }
    def __init__(self,parent,cfg):
        super().__init__(parent,"Plunger / shooter sensor")
        current=cfg.get("plunger",{}).get("source"); reverse={v:k for k,v in self.KEY.items()}; label=reverse.get(current,"None")
        self.kind=tk.StringVar(value=label); self.vals=[tk.StringVar() for _ in range(4)]; self.labels=[]; self.entries=[]
        self.field("Sensor",self.kind,("None",*self.LABELS.keys()))
        for i in range(4):
            lab=ttk.Label(self.body,text=f"Parameter {i+1}"); lab.grid(row=self.row,column=0,sticky="w",padx=(0,12),pady=4)
            ent=ttk.Entry(self.body,textvariable=self.vals[i],width=34); ent.grid(row=self.row,column=1,sticky="ew",pady=4)
            self.labels.append(lab); self.entries.append(ent); self.row+=1
        self.kind.trace_add("write",lambda *_:self.refresh())
        self._load(cfg,current); self.refresh(); self.buttons(self.save)

    def _load(self,cfg,current):
        d=cfg.get(current,{}) if current else {}; p=cfg.get("plunger",{})
        vals={
            "pico_adc":[d.get("gpio",28)], "ads1115":[d.get("i2c",1),hex(d.get("addr",0x48)),d.get("ready",""),d.get("channel",0)],
            "vcnl4010":[d.get("i2c",1),d.get("iredCurrent",200),d.get("interrupt",""),p.get("powerLaw",2)],
            "vl6180x":[d.get("i2c",1),d.get("interrupt","")], "aedr8300":[d.get("channelA",20),d.get("channelB",21),p.get("autoZeroTime",5000)],
            "tcd1103":[d.get("fm",19),d.get("icg",20),d.get("sh",21),d.get("os",27)],
            "tsl1410r":[d.get("si",18),d.get("clk",19),d.get("so",26)], "tsl1412s":[d.get("si",18),d.get("clk",19),d.get("so",26)]}
        for var,val in zip(self.vals,vals.get(current,[])): var.set(str(val))

    def refresh(self):
        labels=self.LABELS.get(self.kind.get(),(None,)*4)
        defaults=self.DEFAULTS.get(self.kind.get(),())
        for lab,ent,textval in zip(self.labels,self.entries,labels):
            lab.configure(text=textval or "Unused"); ent.configure(state="normal" if textval else "disabled")
        for var, value in zip(self.vals, defaults):
            if not var.get().strip(): var.set(str(value))

    def save(self):
        if self.kind.get()=="None": self.result=(None,{},{}); self.destroy(); return
        kind=self.KEY[self.kind.get()]; labels=self.LABELS[self.kind.get()]
        optional_gpio = {
            "ads1115": {2}, "vcnl4010": {2}, "vl6180x": {1},
        }
        try: nums=[self.number(v.get(),labels[i],optional=i in optional_gpio.get(kind,set())) for i,v in enumerate(self.vals) if labels[i]]
        except ValueError as exc: messagebox.showerror("Invalid plunger sensor",str(exc),parent=self); return
        p={"source":kind}; d={}
        if kind=="pico_adc": d={"gpio":nums[0]}
        elif kind=="ads1115":
            d={"i2c":nums[0],"addr":nums[1],"channel":nums[3]}
            if nums[2] is not None and nums[2] >= 0: d["ready"]=nums[2]
        elif kind=="vcnl4010":
            d={"i2c":nums[0],"iredCurrent":nums[1]}; p["powerLaw"]=nums[3]
            if nums[2] is not None and nums[2] >= 0: d["interrupt"]=nums[2]
        elif kind=="vl6180x":
            d={"i2c":nums[0]}
            if nums[1] is not None and nums[1] >= 0: d["interrupt"]=nums[1]
        elif kind=="aedr8300": d={"channelA":nums[0],"channelB":nums[1]}; p.update({"autoZero":True,"autoZeroTime":nums[2]})
        elif kind=="tcd1103": d={"fm":nums[0],"icg":nums[1],"sh":nums[2],"os":nums[3],"invertedLogic":True}
        else: d={"si":nums[0],"clk":nums[1],"so":nums[2]}
        self.result=(kind,d,p); self.destroy()


class ButtonRowDialog(FormDialog):
    """Original-Pinscape-style editor: one physical input, two actions."""

    ACTIONS = ("None", "Keyboard key", "Night Mode", "Keep advanced action")

    def __init__(self, parent, row: dict | None, shift_bits: int):
        super().__init__(parent, "Physical button")
        self.row_data = row or {}
        self.shift_bits = shift_bits
        normal = self.row_data.get("normal") or self.row_data.get("always") or self.row_data.get("shift_source") or {}
        shifted = self.row_data.get("shifted") or {}
        source = normal.get("source", shifted.get("source", {}))
        gp = self.row_data.get("gp", source.get("gp", ""))

        self.name = tk.StringVar(value=normal.get("name", shifted.get("name", "")))
        self.gpio = tk.StringVar(value=str(gp if isinstance(gp, int) and gp >= 0 else ""))
        self.is_shift = tk.BooleanVar(value=bool(self.row_data.get("is_shift")))
        self.normal_kind, self.normal_key = self._action_vars(normal.get("action", {}))
        self.shifted_kind, self.shifted_key = self._action_vars(shifted.get("action", {}))
        if row is None:
            self.normal_kind.set("Keyboard key")
        self.pull = tk.StringVar(value=source.get("pull", "up"))
        self.debounce_on = tk.StringVar(value=str(source.get("debounceTimeOn", 1500 if row is None else "")))
        self.debounce_off = tk.StringVar(value=str(source.get("debounceTimeOff", 1000 if row is None else "")))
        self.pulse = tk.StringVar(value=str(normal.get("tPulse", shifted.get("tPulse", ""))))

        self.field("Button name / VP usage", self.name, width=40)
        current_gp = gp if isinstance(gp, int) and gp >= 0 else None
        choices = parent.available_gpio(exclude_button_gp=current_gp)
        if current_gp is not None and current_gp not in choices:
            choices.append(current_gp)
        self.field("Pico GPIO", self.gpio, values=tuple(str(i) for i in sorted(choices)), width=40)
        ttk.Label(self.body, text="Only exposed GPIOs not already reserved by another device are listed.", foreground="#555555").grid(row=self.row, column=0, columnspan=2, sticky="w", pady=(0, 5)); self.row += 1
        ttk.Checkbutton(self.body, text="Use this physical button as the Shift button", variable=self.is_shift).grid(
            row=self.row, column=0, columnspan=2, sticky="w", pady=(8, 6)); self.row += 1

        ttk.Separator(self.body).grid(row=self.row, column=0, columnspan=2, sticky="ew", pady=6); self.row += 1
        ttk.Label(self.body, text="Normal action", font=("Segoe UI", 10, "bold")).grid(row=self.row, column=0, columnspan=2, sticky="w"); self.row += 1
        self.normal_kind_widget = self.field("Action type", self.normal_kind, self.ACTIONS, width=40)
        self.normal_key_widget = self.field("Selected key", self.normal_key, width=40)
        self.normal_key_widget.configure(state="readonly")
        self.normal_key_button = ttk.Button(self.body, text="Set key", command=lambda: self.capture_key(self.normal_key))
        self.normal_key_button.grid(row=self.row - 1, column=2, padx=(7, 0))

        ttk.Label(self.body, text="Shifted action", font=("Segoe UI", 10, "bold")).grid(row=self.row, column=0, columnspan=2, sticky="w", pady=(10, 0)); self.row += 1
        self.shifted_kind_widget = self.field("Action type", self.shifted_kind, self.ACTIONS, width=40)
        self.shifted_key_widget = self.field("Selected key", self.shifted_key, width=40)
        self.shifted_key_widget.configure(state="readonly")
        self.shifted_key_button = ttk.Button(self.body, text="Set key", command=lambda: self.capture_key(self.shifted_key))
        self.shifted_key_button.grid(row=self.row - 1, column=2, padx=(7, 0))

        ttk.Separator(self.body).grid(row=self.row, column=0, columnspan=2, sticky="ew", pady=6); self.row += 1
        self.field("Input pull", self.pull, ("up", "down", "none"), width=40)
        self.field("Debounce ON (µs)", self.debounce_on, width=40)
        self.field("Debounce OFF (µs)", self.debounce_off, width=40)
        self.field("Pulse time", self.pulse, width=40)
        ttk.Label(
            self.body,
            text="The creator writes the normal and shifted JSON mappings automatically.",
            foreground="#555",
        ).grid(row=self.row, column=0, columnspan=2, sticky="w", pady=(8, 0)); self.row += 1
        self.buttons(self.save)
        self.normal_kind.trace_add("write", lambda *_: self.update_action_controls())
        self.shifted_kind.trace_add("write", lambda *_: self.update_action_controls())
        self.is_shift.trace_add("write", lambda *_: self.update_action_controls())
        self.update_action_controls()

    def update_action_controls(self):
        normal_keyboard = self.normal_kind.get() == "Keyboard key"
        self.normal_key_widget.configure(state="readonly" if normal_keyboard else "disabled")
        self.normal_key_button.configure(state="normal" if normal_keyboard else "disabled")

        shift_row = self.is_shift.get()
        self.shifted_kind_widget.configure(state="disabled" if shift_row else "readonly")
        shifted_keyboard = not shift_row and self.shifted_kind.get() == "Keyboard key"
        self.shifted_key_widget.configure(state="readonly" if shifted_keyboard else "disabled")
        self.shifted_key_button.configure(state="normal" if shifted_keyboard else "disabled")

    def capture_key(self, variable):
        dialog = KeyCaptureDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            variable.set(dialog.result)

    def _action_vars(self, action: dict):
        kind = action.get("type")
        label = "Keyboard key" if kind == "key" else "Night Mode" if kind == "nightmode" else "None" if not kind or kind == "none" else "Keep advanced action"
        return tk.StringVar(value=label), tk.StringVar(value=action.get("key", ""))

    def _make_action(self, kind: str, key: str, old: dict) -> dict | None:
        if kind == "None":
            return None
        if kind == "Keyboard key":
            if not key.strip():
                raise ValueError("Enter a keyboard key for each Keyboard key action")
            return {"type": "key", "key": key.strip()}
        if kind == "Night Mode":
            return {"type": "nightmode"}
        return old or {"type": "none"}

    def save(self):
        try:
            gp = self.number(self.gpio.get(), "GPIO")
            if gp not in (list(range(23)) + [26, 27, 28]):
                raise ValueError("Choose an exposed Pico header GPIO (GP0–GP22 or GP26–GP28)")
            current_gp = self.row_data.get("gp")
            conflicts = self.master.gpio_uses(exclude_button_gp=current_gp).get(gp, [])
            if conflicts:
                raise ValueError(f"GP{gp} is already assigned to {', '.join(conflicts)}")
            debounce_on = self.number(self.debounce_on.get(), "Debounce ON", True)
            debounce_off = self.number(self.debounce_off.get(), "Debounce OFF", True)
            pulse = self.number(self.pulse.get(), "Pulse time", True)
            old_normal = (self.row_data.get("normal") or self.row_data.get("always") or self.row_data.get("shift_source") or {}).get("action", {})
            old_shifted = (self.row_data.get("shifted") or {}).get("action", {})
            normal_action = self._make_action(self.normal_kind.get(), self.normal_key.get(), old_normal)
            shifted_action = None if self.is_shift.get() else self._make_action(self.shifted_kind.get(), self.shifted_key.get(), old_shifted)
            if normal_action is None and shifted_action is None:
                raise ValueError("Assign at least one normal or shifted action")
        except ValueError as exc:
            messagebox.showerror("Invalid button", str(exc), parent=self)
            return

        source = {"type": "gpio", "gp": gp}
        if self.pull.get() != "none":
            source["pull"] = self.pull.get()
        if debounce_on is not None:
            source["debounceTimeOn"] = debounce_on
        if debounce_off is not None:
            source["debounceTimeOff"] = debounce_off

        base_name = self.name.get().strip() or f"Button GP{gp}"
        result = []
        if normal_action is not None:
            normal = {"name": base_name, "source": dict(source), "action": normal_action}
            if self.is_shift.get():
                normal["type"] = "shift"
                normal["shiftBits"] = self.shift_bits
            else:
                normal["shiftMask"] = self.shift_bits
                normal["shiftBits"] = 0
            if pulse is not None:
                normal["tPulse"] = pulse
            result.append(normal)

        if shifted_action is not None:
            shifted = {
                "name": base_name + " (Shifted)",
                "source": dict(source),
                "shiftMask": self.shift_bits,
                "shiftBits": self.shift_bits,
                "action": shifted_action,
            }
            if pulse is not None:
                shifted["tPulse"] = pulse
            result.append(shifted)

        self.result = result
        self.destroy()


class InputDialog(FormDialog):
    ACTIONS = ("Keyboard key", "Night Mode", "None", "Keep advanced action")
    CONDITIONS = ("Normal (Shift not held)", "Shifted (Shift held)", "Always", "This is the Shift button")

    def __init__(self, parent, original: dict, kind: str, shift_bits: int):
        super().__init__(parent, "Input mapping")
        self.original = json.loads(json.dumps(original))
        self.shift_bits = shift_bits
        source = original.get("source", {})
        action = original.get("action", {})
        labels = {"normal": self.CONDITIONS[0], "shifted": self.CONDITIONS[1], "always": self.CONDITIONS[2], "shift-source": self.CONDITIONS[3]}
        action_label = "Keyboard key" if action.get("type") == "key" else "Night Mode" if action.get("type") == "nightmode" else "None" if action.get("type") == "none" else "Keep advanced action"
        self.name = tk.StringVar(value=original.get("name", ""))
        self.gpio = tk.StringVar(value=str(source.get("gp", "")))
        self.condition = tk.StringVar(value=labels.get(kind, self.CONDITIONS[2]))
        self.action_kind = tk.StringVar(value=action_label)
        self.key = tk.StringVar(value=action.get("key", ""))
        self.pull = tk.StringVar(value=source.get("pull", "up"))
        self.debounce_on = tk.StringVar(value=str(source.get("debounceTimeOn", "")))
        self.debounce_off = tk.StringVar(value=str(source.get("debounceTimeOff", "")))
        self.pulse = tk.StringVar(value=str(original.get("tPulse", "")))
        self.field("Name", self.name)
        self.field("GPIO", self.gpio)
        self.field("Shift behavior", self.condition, self.CONDITIONS)
        self.field("Action", self.action_kind, self.ACTIONS)
        self.field("Keyboard key", self.key)
        self.field("Input pull", self.pull, ("up", "down", "none"))
        self.field("Debounce ON (µs)", self.debounce_on)
        self.field("Debounce OFF (µs)", self.debounce_off)
        self.field("Pulse time", self.pulse)
        ttk.Label(self.body, text="Normal and shifted mappings may use the same GPIO.", foreground="#555").grid(row=self.row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.row += 1
        self.buttons(self.save)

    def save(self):
        try:
            gp = self.number(self.gpio.get(), "GPIO")
            debounce_on = self.number(self.debounce_on.get(), "Debounce ON", True)
            debounce_off = self.number(self.debounce_off.get(), "Debounce OFF", True)
            pulse = self.number(self.pulse.get(), "Pulse time", True)
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc), parent=self)
            return
        source = {"type": "gpio", "gp": gp}
        if self.pull.get() != "none":
            source["pull"] = self.pull.get()
        if debounce_on is not None:
            source["debounceTimeOn"] = debounce_on
        if debounce_off is not None:
            source["debounceTimeOff"] = debounce_off
        result = {"name": self.name.get().strip() or f"GPIO {gp}", "source": source}
        condition = self.condition.get()
        if condition == self.CONDITIONS[3]:
            result["type"] = "shift"
            result["shiftBits"] = self.original.get("shiftBits", self.shift_bits)
        elif condition in self.CONDITIONS[:2]:
            result["shiftMask"] = self.shift_bits
            result["shiftBits"] = self.shift_bits if condition == self.CONDITIONS[1] else 0
        action_kind = self.action_kind.get()
        if action_kind == "Keyboard key":
            if not self.key.get().strip():
                messagebox.showerror("Missing key", "Enter a keyboard key name.", parent=self)
                return
            result["action"] = {"type": "key", "key": self.key.get().strip()}
        elif action_kind == "Night Mode":
            result["action"] = {"type": "nightmode"}
        elif action_kind == "None":
            result["action"] = {"type": "none"}
        else:
            result["action"] = self.original.get("action", {"type": "none"})
            for key in ("type", "shiftBits"):
                if key in self.original and key not in result:
                    result[key] = self.original[key]
        if pulse is not None:
            result["tPulse"] = pulse
        self.result = result
        self.destroy()


class OutputDialog(FormDialog):
    def __init__(self, parent, original: dict, output_index: int | None = None):
        super().__init__(parent, "Output mapping")
        self.output_index = output_index
        device = original.get("device", {})
        self.name = tk.StringVar(value=original.get("name", ""))
        self.gpio = tk.StringVar(value=str(device.get("gp", "")))
        self.pwm = tk.BooleanVar(value=bool(device.get("pwm", False)))
        self.noisy = tk.BooleanVar(value=bool(original.get("noisy", False)))
        self.time_limit = tk.StringVar(value=str(original.get("timeLimit", "")))
        self.cooling = tk.StringVar(value=str(original.get("coolingTime", "")))
        self.power = tk.StringVar(value=str(original.get("powerLimit", "")))
        self.field("Name", self.name)
        current_gp = device.get("gp") if isinstance(device.get("gp"), int) else None
        choices = parent.available_gpio(exclude_output_index=output_index)
        if current_gp is not None and current_gp not in choices:
            choices.append(current_gp)
        self.field("GPIO", self.gpio, tuple(str(i) for i in sorted(choices)))
        ttk.Checkbutton(self.body, text="PWM output", variable=self.pwm).grid(row=self.row, column=0, columnspan=2, sticky="w", pady=4); self.row += 1
        ttk.Checkbutton(self.body, text="Noisy device (disabled in Night Mode)", variable=self.noisy).grid(row=self.row, column=0, columnspan=2, sticky="w", pady=4); self.row += 1
        self.field("Maximum ON time (ms)", self.time_limit)
        self.field("Cooling time (ms)", self.cooling)
        self.field("Hold power (%)", self.power)
        self.buttons(self.save)

    def save(self):
        try:
            gp = self.number(self.gpio.get(), "GPIO")
            if gp not in (list(range(23)) + [26, 27, 28]):
                raise ValueError("Choose an exposed Pico header GPIO (GP0–GP22 or GP26–GP28)")
            conflicts = self.master.gpio_uses(exclude_output_index=self.output_index).get(gp, [])
            if conflicts:
                raise ValueError(f"GP{gp} is already assigned to {', '.join(conflicts)}")
            time_limit = self.number(self.time_limit.get(), "Maximum ON time", True)
            cooling = self.number(self.cooling.get(), "Cooling time", True)
            power = self.number(self.power.get(), "Hold power", True)
        except ValueError as exc:
            messagebox.showerror("Invalid output", str(exc), parent=self)
            return
        result = {"name": self.name.get().strip() or f"Output GPIO {gp}", "device": {"type": "gpio", "gp": gp, "pwm": self.pwm.get()}}
        if self.noisy.get(): result["noisy"] = True
        if time_limit is not None: result["timeLimit"] = time_limit
        if cooling is not None: result["coolingTime"] = cooling
        if power is not None: result["powerLimit"] = power
        self.result = result
        self.destroy()


class KeyCaptureDialog(tk.Toplevel):
    KEY_NAMES = {
        "Control_L": "left ctrl", "Control_R": "right ctrl",
        "Shift_L": "left shift", "Shift_R": "right shift",
        "Alt_L": "left alt", "Alt_R": "right alt",
        "Return": "enter", "Escape": "escape", "BackSpace": "backspace",
        "Tab": "tab", "space": "space", "Delete": "delete",
        "Insert": "insert", "Home": "home", "End": "end",
        "Prior": "page up", "Next": "page down",
        "Left": "left", "Right": "right", "Up": "up", "Down": "down",
    }

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Press a key")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.result = None
        ttk.Label(self, text="Press the keyboard key to assign", font=("Segoe UI", 12, "bold"), padding=(24, 22, 24, 8)).pack()
        ttk.Label(self, text="Modifier keys such as Left Ctrl, Left Shift, and Left Alt are supported.", padding=(24, 0, 24, 18)).pack()
        ttk.Button(self, text="Cancel", command=self.destroy).pack(pady=(0, 18))
        self.bind("<KeyPress>", self.on_key)
        self.after(100, self.focus_force)

    def on_key(self, event):
        if event.keysym in ("Escape",):
            self.result = "escape"
        elif event.keysym in self.KEY_NAMES:
            self.result = self.KEY_NAMES[event.keysym]
        elif event.keysym.startswith("F") and event.keysym[1:].isdigit():
            self.result = event.keysym.upper()
        elif event.char and event.char.isprintable() and not event.char.isspace():
            self.result = event.char.lower()
        else:
            self.result = event.keysym.lower()
        self.destroy()


if __name__ == "__main__":
    Builder().mainloop()
