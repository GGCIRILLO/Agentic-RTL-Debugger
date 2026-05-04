# Expected Fix – `mux_bug`

## Root Cause

`case` branch for `sel=2'b11` assigns a hardcoded constant `4'b1111` instead of forwarding input `d`.

## Correct Patch

```diff
-            2'b11: y = 4'b1111;
+            2'b11: y = d;
```

## Why

Every select value must forward the corresponding input port unchanged.
Hardcoding the output violates the pass-through contract of a multiplexer.
