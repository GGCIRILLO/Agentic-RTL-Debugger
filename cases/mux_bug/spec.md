# Spec: 4-to-1 Multiplexer

## Description

A combinational 4-to-1 multiplexer with 4-bit data inputs and a 2-bit select.

## Ports

| Port  | Direction | Width | Description              |
|-------|-----------|-------|--------------------------|
| `sel` | input     | 2     | Select signal            |
| `a`   | input     | 4     | Input channel 0          |
| `b`   | input     | 4     | Input channel 1          |
| `c`   | input     | 4     | Input channel 2          |
| `d`   | input     | 4     | Input channel 3          |
| `y`   | output    | 4     | Selected output          |

## Behaviour

- `sel=2'b00` → `y = a`
- `sel=2'b01` → `y = b`
- `sel=2'b10` → `y = c`
- `sel=2'b11` → `y = d`
- All selections are purely combinational (no clock).

## Notes

Every value of `sel` must select exactly the corresponding input channel.
No input channel may be hardcoded in the output logic.
