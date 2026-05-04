// 4-to-1 multiplexer

`timescale 1ns/1ps

module mux4to1 (
    input  wire [1:0] sel,
    input  wire [3:0] a, b, c, d,
    output reg  [3:0] y
);

    always @(*) begin
        case (sel)
            2'b00: y = a;
            2'b01: y = b;
            2'b10: y = c;
            2'b11: y = 4'b1111;
            default: y = 4'b0;
        endcase
    end

endmodule
