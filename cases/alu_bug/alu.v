// Simple 8-bit ALU
// Operations: ADD, SUB, AND, OR, XOR, SLT (set less than), SLL, SRL

`timescale 1ns/1ps

module alu (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire [2:0] op,
    output reg  [7:0] result,
    output wire       zero
);

    // Opcodes
    localparam ADD = 3'd0;
    localparam SUB = 3'd1;
    localparam AND = 3'd2;
    localparam OR  = 3'd3;
    localparam XOR = 3'd4;
    localparam SLT = 3'd5;
    localparam SLL = 3'd6;
    localparam SRL = 3'd7;

    assign zero = (result == 8'd0);

    always @(*) begin
        case (op)
            ADD: result = a + b;
            SUB: result = a & b;
            AND: result = a - b;  
            OR:  result = a | b;
            XOR: result = a ^ b;
            SLT: result = (a < b) ? 8'd1 : 8'd0;  
            SLL: result = a >> b[2:0];  
            SRL: result = a >> b[2:0];
            default: result = 8'd0;
        endcase
    end

endmodule
