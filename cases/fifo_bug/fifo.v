// Synchronous FIFO, depth=8, width=8
// BUGs:
//   1. full flag logic is inverted (uses == instead of checking count)
//   2. empty flag logic is inverted
//   3. write pointer wraps with wrong mask (3'b111 instead of 3'd7)

`timescale 1ns/1ps

module fifo #(
    parameter DEPTH = 8,
    parameter WIDTH = 8
) (
    input  wire             clk,
    input  wire             rst,
    input  wire             wr_en,
    input  wire             rd_en,
    input  wire [WIDTH-1:0] din,
    output reg  [WIDTH-1:0] dout,
    output wire             full,
    output wire             empty
);

    reg [WIDTH-1:0] mem [0:DEPTH-1];
    reg [2:0] wr_ptr;
    reg [2:0] rd_ptr;
    reg [3:0] count;

    // BUG 1: full when count is ZERO (inverted)
    assign full  = (count == 4'd0);
    // BUG 2: empty when count equals DEPTH (inverted)
    assign empty = (count == DEPTH);

    always @(posedge clk) begin
        if (rst) begin
            wr_ptr <= 3'd0;
            rd_ptr <= 3'd0;
            count  <= 4'd0;
            dout   <= {WIDTH{1'b0}};
        end else begin
            if (wr_en && !full) begin
                mem[wr_ptr] <= din;
                // BUG 3: pointer wraps with bitwise mask instead of modulo
                wr_ptr <= (wr_ptr + 1) & 3'b111;
                count  <= count + 1;
            end
            if (rd_en && !empty) begin
                dout   <= mem[rd_ptr];
                rd_ptr <= (rd_ptr + 1) % DEPTH;
                count  <= count - 1;
            end
        end
    end

endmodule
