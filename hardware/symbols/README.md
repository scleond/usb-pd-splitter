# Custom symbols

Use this folder to store KiCad schematic symbols for USB-C connectors, resistor networks, and any passive components specific to the splitter.

The current scaffold keeps its placeholder library directly in this directory:

- `usb_c.lib` - legacy-format placeholder library for USB-C and passive symbols

If the library grows, split it into focused libraries such as `usb_c/` and
`passive/`. New libraries should use KiCad's `.kicad_sym` format. The existing
placeholder library is intentionally left unchanged until the schematic symbols
are defined and tested in KiCad.
