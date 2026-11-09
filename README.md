@IMSAIGuy made two USB interface programs, for the TinySA and the NanoVNA. They have graphical instrument panels controlled with a mouse.
Here are YouTube his videos (c) imsaiguy:
TinySA     https://youtu.be/yPIbrWnYdHI
NanoVNA    https://youtu.be/Vf9LRCsLcrs

- Compiled binaries for Windows x64, MacOSX and Linux can be found under Releases.

## Connecting a NanoVNA-F V3

Two settings on the instrument itself decide whether the panel can see it at all:

- **CONFIG -> Connection -> USB** (not UART). On UART the USB socket stays silent, Windows never creates
  a COM port, and the panel's port list comes up empty.
- **CONFIG -> Serial Speed** -> **115200**. The panel opens the port at a fixed 115200 baud and has no
  speed selector. The hardware supports more (up to **3,000,000** baud), but the panel will not talk to
  it at that rate unless you change the baud argument in `nanovna_panel/vna_device.py`.

Also note the panel opens the port at whatever `CONFIG -> Connection` exposes: if the port list looks
empty even though Device Manager shows `USB Serial Device (COMx)`, you are probably on a build older
than v1.2 running in Windows dark mode, where the port names were drawn white on white.

