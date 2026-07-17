# USB-PD Splitter Design Notes

## Intended topology
- `PWR_IN`: USB-C power input
- `DATA_IN`: USB-C data input
- `OUT`: USB-C device output

## Intended signal flow
- `PWR_IN.VBUS` → `OUT.VBUS`
- `PWR_IN.GND` → `OUT.GND`
- `PWR_IN.CC1/CC2` → `OUT.CC1/CC2`
- `DATA_IN.D+` → `OUT.D+`
- `DATA_IN.D-` → `OUT.D-`
- `DATA_IN.GND` → `OUT.GND`
- `DATA_IN.CC1/CC2` present host-side signaling for the data connector
- `PWR_IN` non-CC pins DNP

## Updated design note
This design is a passive power/data injector for a USB-C device.

### What this means
- `PWR_IN` is the power input and passes `VBUS`, `GND`, and CC through to `OUT`
- `DATA_IN` is the USB host data input and passes `D+`, `D-`, `GND`, and CC signaling to `OUT`
- `OUT` is the powered device and negotiates power with the source through the power path

### Important constraint
- `DATA_IN` must present host-side CC signaling (Rp) if it is a host data connection.
- `PWR_IN` must carry `VBUS` to `OUT` or the device will have no power.

## Recommended revision
1. Route `PWR_IN.VBUS` and `PWR_IN.GND` to `OUT.VBUS` and `OUT.GND`.
2. Keep `PWR_IN.CC1/CC2` connected to `OUT.CC1/CC2` if the output device should negotiate with the power source.
3. On `DATA_IN`, use the correct CC pull resistors for the intended role:
   - If `DATA_IN` is a host-facing connector, use Rp to indicate a DFP/source.
   - If `DATA_IN` is a device-facing connector, use Rd and ensure `OUT` is actually the host side.
4. If you want a pure data-only input, consider how `DATA_IN.VBUS` will be handled for USB attachment detection and enumeration.

## Practical approach
- Make `PWR_IN` the power feed: VBUS + GND + CC only.
- Make `DATA_IN` the USB data feed: D+/D- + GND + CC as host-side signaling.
- Ensure `OUT` sees VBUS from the power source and D+/D- from the data source together.
