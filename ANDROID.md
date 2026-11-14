# Running the NanoVNA panel on an Android tablet

There is **no Android binary to compile** for this project, for two hard reasons:

* PyInstaller — what `build_exe.bat` / the release builds use — only targets
  Windows, macOS and GNU/Linux. It has no Android target at all.
* PyQt6 publishes no Android wheels. Its `aarch64` wheels are `manylinux`
  (glibc) builds; Android is bionic, so they cannot be loaded by an Android app.

What *does* work is running the same Python code on the tablet itself under
**Termux**, because Termux's `x11-repo` ships `pyqt6` 6.12.0 built for Android.
No source changes, no APK.

## 1. Install on the tablet

Install Termux from **F-Droid** (the Play Store build is abandoned), then:

```bash
pkg update -y && pkg install -y x11-repo
pkg install -y pyqt6 python-numpy termux-x11-nightly python-pip git
pip install --no-deps pyqtgraph pyserial
```

`--no-deps` matters: numpy and PyQt6 are already provided by `pkg`, and letting
pip try to rebuild numpy on the tablet takes forever.

Also install the Termux:X11 app (`termux-x11-universal-debug.apk` from the
`nightly` tag of github.com/termux/termux-x11). Android 7 or newer.

## 2. Get the code and check the GUI

```bash
cd ~ && git clone https://github.com/cghercoias/TinySA-NanoVNA-for-Windows
cd TinySA-NanoVNA-for-Windows/instrument-panels/nanovna_panel
python vna_panel.py --sim
```

`--sim` uses the built-in simulator, so the panel comes up with no hardware
attached. Start the display first — in a second Termux session:

```bash
termux-wake-lock            # stops Android from freezing the session
termux-x11 :1 &
```

then in the first session:

```bash
DISPLAY=:1 python vna_panel.py --sim
```

Open the Termux:X11 app, rotate to landscape. Touch acts as a mouse pointer;
knobs are drag-operated.

## 3. The one real blocker: USB

An unrooted Android app cannot open `/dev/ttyACM0` / `/dev/ttyUSB*` — the app
sandbox and SELinux deny it, and most vendor kernels do not even ship
`cdc_acm` / `ch341` / `ftdi_sio`. So `list_ports()` finds nothing and the port
box stays empty. Two ways around it:

**a. Network bridge (no root, recommended).** Leave the NanoVNA plugged into a
Linux box (Pi 5, Orange Pi, Pi-hole host) and forward the serial port over TCP.
The panel in this branch accepts `socket://host:port` as a port, so the tablet
needs no USB at all.

**b. Root the tablet** and load a kernel/module that exposes the device node
(`cdc_acm` for a NanoVNA-F V3), then use `--port /dev/ttyACM0` as usual.

## 4. Bridge on the host that has the NanoVNA

A NanoVNA-F V3 is USB CDC, so it appears as `/dev/ttyACM0`:

```bash
dmesg | tail -5            # confirm ttyACM0 appeared
```

socat, no config file needed:

```bash
sudo apt install socat
sudo socat TCP-LISTEN:4012,reuseaddr,fork /dev/ttyACM0,b115200,raw,echo=0
```

ser2net 4.x equivalent (`/etc/ser2net.yaml`):

```yaml
connection: &nanovna
  accepter: tcp,4012
  enable: on
  options:
    kickolduser: true
  connector: serialdev,/dev/ttyACM0,115200n81,local
```

Either way the stream must stay **raw** — telnet/IAC negotiation bytes would
corrupt the shell protocol.

## 5. Point the tablet at the bridge

```bash
DISPLAY=:1 python vna_panel.py --port socket://192.168.1.150:4012
```

Quick link test from the tablet before starting the panel:

```bash
python -c "import serial;s=serial.serial_for_url('socket://192.168.1.150:4012');s.write(b'\r');print(s.read(64))"
```

It should print the `ch> ` prompt.

Remember the two instrument-side settings (see README): `CONFIG -> Connection
-> USB` (not UART) and `CONFIG -> Serial Speed -> 115200`. Over the bridge the
baud rate is set on the host side (`b115200` above), not on the tablet.

## 6. What changed in the code

`vna_device.py` (and `device.py` in the tinySA panel) gained one helper:

```python
def open_port(port, baud=115200, timeout=0.05, write_timeout=2):
    if "://" in port:
        return serial.serial_for_url(port, baudrate=baud, timeout=timeout,
                                     write_timeout=write_timeout)
    return serial.Serial(port, baud, timeout=timeout, write_timeout=write_timeout)
```

`SerialTransport` now calls it. Local ports behave exactly as before; any
pyserial URL also works: `socket://` for socat/ser2net raw, `rfc2217://` for
ser2net's telnet mode. This is not Android-specific — it also lets two panels
share one instrument, or run the panel on the Mac over Wi-Fi.

## 7. If you do want a real APK

That means a rewrite, not a build: Kivy + Buildozer (no pyqtgraph, so the plots
get redone in matplotlib or custom Kivy canvas drawing), or Qt for Android +
`pyqtdeploy` (cross-build Qt 6 for each ABI yourself, then a per-ABI APK). Weeks
of work against a Termux setup that already runs this code unchanged.
