// 4-bit synchronous counter

`timescale 1ns/1ps

module counter (
    input  wire       clk,
    input  wire       rst,
    output reg  [3:0] count
);

    always @(posedge clk) begin
        count <= count + 1;
        if (rst)
            count <= 4'b0;
    end

endmodule
