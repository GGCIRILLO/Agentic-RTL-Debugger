# Expected outcome: counter_bug

## Simulation result

The testbench must print `FAILED` and exit with one or more errors when
run against the buggy `counter.v`.

The expected failure message is:

```
FAILED: expected count=0 after reset, got count=<non-zero value>
```

## Root cause

The `always` block increments `count` unconditionally on every rising
edge and then overwrites it to `0` only if `rst` is high. Because both
assignments are non-blocking, Verilog schedules them in declaration
order: the increment wins on the same edge as reset, so the counter
never reaches `0` while `rst` is asserted.

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
