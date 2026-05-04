# Spec: Synchronous FIFO

## Description

A synchronous, single-clock FIFO with parameterisable depth and width.
Default: depth=8, width=8.

## Ports

| Port    | Direction | Width   | Description                        |
|---------|-----------|---------|------------------------------------|n| `clk`   | input     | 1       | Clock (rising-edge)                |
| `rst`   | input     | 1       | Synchronous reset, active high     |
| `wr_en` | input     | 1       | Write enable                       |
| `rd_en` | input     | 1       | Read enable                        |
| `din`   | input     | WIDTH   | Write data                         |
| `dout`  | output    | WIDTH   | Read data (registered)             |
| `full`  | output    | 1       | High when FIFO is full             |
| `empty` | output    | 1       | High when FIFO is empty            |

## Behaviour

- On reset: `wr_ptr=0`, `rd_ptr=0`, `count=0`. `empty` must be high, `full` must be low.
- `full` is asserted when `count == DEPTH`.
- `empty` is asserted when `count == 0`.
- A write increments `wr_ptr` and `count`. Writes are ignored when `full` is high.
- A read increments `rd_ptr` and decrements `count`. Reads are ignored when `empty` is high.
- Both `wr_ptr` and `rd_ptr` must wrap modulo `DEPTH` (not bitwise AND).
- Simultaneous read and write when neither full nor empty: count stays the same.

## Notes

The pointer wrap must use `% DEPTH` (or equivalent) to remain correct if
`DEPTH` is ever changed to a non-power-of-two value.
