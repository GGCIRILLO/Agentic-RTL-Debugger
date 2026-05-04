# Expected Fix – `dff_bug`

## Root Cause

The design uses two `always` blocks for the same register `q`: one sensitive to `posedge clk` (reset path) and one sensitive to `negedge clk` (data path). This creates a race condition and means `q` captures `d` half a clock cycle late.

## Correct Patch

Merge the two blocks into one `always @(posedge clk)` block:

```diff
-    always @(posedge clk) begin
-        if (rst)
-            q <= 1'b0;
-    end
-
-    always @(negedge clk) begin
-        if (!rst)
-            q <= d;
-    end
+    always @(posedge clk) begin
+        if (rst)
+            q <= 1'b0;
+        else
+            q <= d;
+    end
```

## Why

A D flip-flop by definition captures data on one clock edge only.
Splitting reset and data capture across two edges violates this contract
and causes undefined behaviour in synthesis.
