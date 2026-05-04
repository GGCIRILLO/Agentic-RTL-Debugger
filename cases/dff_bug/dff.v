// D flip-flop with synchronous active-high reset
// BUG: reset is applied on negedge instead of posedge

`timescale 1ns/1ps

module dff (
    input  wire clk,
    input  wire rst,
    input  wire d,
    output reg  q
);

    always @(posedge clk) begin
        if (rst)
            q <= 1'b0;
    end

    // BUG: this second block captures d on the wrong edge
    always @(negedge clk) begin
        if (!rst)
            q <= d;
    end

endmodule
