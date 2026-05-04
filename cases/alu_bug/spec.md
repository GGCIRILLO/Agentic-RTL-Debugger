# Spec: 8-bit ALU

## Description

An 8-bit combinational ALU supporting 8 operations selected by a 3-bit opcode.

## Ports

| Port     | Direction | Width | Description                   |
|----------|-----------|-------|-------------------------------|
| `a`      | input     | 8     | First operand                 |
| `b`      | input     | 8     | Second operand                |
| `op`     | input     | 3     | Operation select              |
| `result` | output    | 8     | Operation result              |
| `zero`   | output    | 1     | High when result is zero      |

## Opcodes

| `op`    | Operation | Expression              |
|---------|-----------|-------------------------|
| `3'd0`  | ADD       | `a + b`                 |
| `3'd1`  | SUB       | `a - b` (wrapping)      |
| `3'd2`  | AND       | `a & b`                 |
| `3'd3`  | OR        | `a \| b`               |
| `3'd4`  | XOR       | `a ^ b`                 |
| `3'd5`  | SLT       | `1` if `$signed(a) < $signed(b)`, else `0` |
| `3'd6`  | SLL       | `a << b[2:0]`           |
| `3'd7`  | SRL       | `a >> b[2:0]`           |

## Notes

- SLT must use **signed** comparison (`$signed(a) < $signed(b)`).
- SLL shifts **left**; SRL shifts **right**.
- All operations are purely combinational.
- `zero` is derived from `result` combinationally.
