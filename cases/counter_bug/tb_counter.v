// Testbench for the 4-bit synchronous counter.
//
// Tests:
//   1. Reset behaviour: count must be 0 one cycle after rst goes high.
//   2. Count-up: count must increment correctly for 8 cycles.
//   3. Wrap-around: not checked here (kept minimal for the demo).

`timescale 1ns/1ps

module tb_counter;

    // ----------------------------------------------------------------
    // DUT signals
    // ----------------------------------------------------------------
    reg        clk;
    reg        rst;
    wire [3:0] count;

    // ----------------------------------------------------------------
    // DUT instantiation
    // ----------------------------------------------------------------
    counter dut (
        .clk   (clk),
        .rst   (rst),
        .count (count)
    );

    // ----------------------------------------------------------------
    // Clock: 10 ns period
    // ----------------------------------------------------------------
    initial clk = 0;
    always #5 clk = ~clk;

    // ----------------------------------------------------------------
    // Stimulus and checks
    // ----------------------------------------------------------------
    integer errors;

    initial begin
        errors = 0;
        rst    = 1;

        // Hold reset for 3 rising edges
        repeat (3) @(posedge clk);
        #1; // sample just after the clock edge

        assert (count === 4'b0000) else begin
            $error("expected count=0 after reset, got count=%0d", count);
            errors = errors + 1;
        end

        // Release reset and count for 8 cycles
        rst = 0;
        repeat (8) begin
            @(posedge clk);
            #1;
        end

        // After 8 increments from 0, count must be 8
        assert (count === 4'd8) else begin
            $error("expected count=8 after 8 increments, got count=%0d", count);
            errors = errors + 1;
        end

        // ----------------------------------------------------------------
        // Summary
        // ----------------------------------------------------------------
        if (errors == 0)
            $display("PASSED: all checks passed");
        else
            $display("FAILED: %0d error(s) found", errors);

        $finish;
    end

endmodule
