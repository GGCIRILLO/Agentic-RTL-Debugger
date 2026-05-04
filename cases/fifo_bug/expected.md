# Expected Fix – `fifo_bug`

## Root Cause

Three bugs, all in the flag and pointer logic:

1. `full` condition is inverted: `count == 0` should be `count == DEPTH`.
2. `empty` condition is inverted: `count == DEPTH` should be `count == 0`.
3. `wr_ptr` wraps with `& 3'b111` (bitwise AND with 7), which happens to be
   correct for depth=8 but is semantically wrong and breaks for other depths.
   Should use `% DEPTH` to match `rd_ptr`.

## Correct Patch

```diff
-    assign full  = (count == 4'd0);
-    assign empty = (count == DEPTH);
+    assign full  = (count == DEPTH);
+    assign empty = (count == 4'd0);
```

```diff
-                wr_ptr <= (wr_ptr + 1) & 3'b111;
+                wr_ptr <= (wr_ptr + 1) % DEPTH;
```

## Why

`full` must block writes when the buffer is at capacity, not when it is empty.
`empty` must block reads when there is no data, not when the buffer is full.
Using `% DEPTH` for both pointers makes the wrap behaviour consistent and
parameterisation-safe.
