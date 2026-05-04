# Expected Fix – `alu_bug`

## Root Cause

Three bugs in the opcode decode logic:

1. SUB and AND cases are **swapped**: SUB computes `a & b` and AND computes `a - b`.
2. SLT uses **unsigned** comparison `(a < b)` instead of **signed** `($signed(a) < $signed(b))`.
3. SLL uses **right shift** `>>` instead of **left shift** `<<`.

## Correct Patch

```diff
-            SUB: result = a & b;
-            AND: result = a - b;
+            SUB: result = a - b;
+            AND: result = a & b;
```

```diff
-            SLT: result = (a < b) ? 8'd1 : 8'd0;
+            SLT: result = ($signed(a) < $signed(b)) ? 8'd1 : 8'd0;
```

```diff
-            SLL: result = a >> b[2:0];
+            SLL: result = a << b[2:0];
```

## Why

- Swapped opcodes cause two operations to produce wrong results simultaneously.
- Unsigned SLT fails when one operand is negative (MSB set): `8'hFF > 8'h01`
  in unsigned but `8'hFF (-1) < 8'h01 (1)` in signed.
- Wrong shift direction in SLL produces a right-shifted result instead of left.
