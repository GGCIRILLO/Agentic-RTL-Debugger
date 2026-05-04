# Expected outcome: counter_bug

## Simulation result

The testbench must print `FAILED` and exit with one or more errors when
run against the buggy `counter.v`.

The expected failure message is:

```
FAILED: expected count=0 after reset, got count=<non-zero value>
```

## Root cause

The `always` block checks `rst` and assigns `0`, but then unconditionally
increments `count` on every rising edge. Because both assignments are
non-blocking, the last assignment executed wins. The increment is executed
last, so it overrides the reset, and the counter never correctly resets
while `rst` is asserted.

## Minimal correct fix

Swap the conditional order so that the reset check comes first:

```verilog
always @(posedge clk) begin
    if (rst)
        count <= 4'b0;
    else
        count <= count + 1;
end
```

## Confidence

High. The bug is deterministic and always reproducible.
