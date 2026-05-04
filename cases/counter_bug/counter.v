// 4-bit synchronous counter — contains an intentional reset bug.
//
// Bug: the reset condition uses a non-blocking assignment but checks
// `rst` one cycle too late due to the wrong conditional ordering.
// The counter increments on the same cycle that rst is high instead
// of resetting to 0.

`timescale 1ns/1ps

module counter (
    input  wire       clk,
    input  wire       rst,
    output reg  [3:0] count
);

    always @(posedge clk) begin
        // BUG: increment happens before reset check.
        // Should be: if (rst) count <= 4'b0; else count <= count + 1;
        count <= count + 1;
        if (rst)
            count <= 4'b0;
    end

endmodule
