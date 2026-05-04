# Spec: 4-bit Synchronous Counter

## Description

A 4-bit synchronous counter with active-high synchronous reset.

## Ports

| Port    | Direction | Width | Description                          |
|---------|-----------|-------|--------------------------------------|
| `clk`   | input     | 1     | Clock signal (rising-edge triggered) |
| `rst`   | input     | 1     | Synchronous reset, active high       |
| `count` | output    | 4     | Current counter value                |

## Behaviour

- On every rising edge of `clk`:
  - If `rst` is high, `count` must be set to `0` on that same clock edge.
  - Otherwise, `count` increments by 1.
- The counter wraps around naturally from `4'hF` to `4'h0`.

## Expected reset behaviour (used by testbench)

After reset is deasserted on rising edge N, `count` must equal `0` at the
end of edge N and `1` at the end of edge N+1.
