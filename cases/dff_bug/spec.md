# Spec: D Flip-Flop with Synchronous Reset

## Description

A single-bit D flip-flop with synchronous active-high reset, triggered on the rising edge of `clk`.

## Ports

| Port  | Direction | Width | Description                          |
|-------|-----------|-------|--------------------------------------|
| `clk` | input     | 1     | Clock (rising-edge triggered)        |
| `rst` | input     | 1     | Synchronous reset, active high       |
| `d`   | input     | 1     | Data input                           |
| `q`   | output    | 1     | Registered output                    |

## Behaviour

- All state changes happen **only** on the rising edge of `clk`.
- If `rst` is high on a rising edge, `q` is set to `0` on that edge.
- Otherwise, `q` captures the value of `d` on the rising edge.
- There must be exactly **one** `always` block sensitive to `posedge clk`.

## Notes

The design must not respond to `negedge clk` at any point.
Two separate `always` blocks for the same register create a race condition
and violate the single-driver rule.
