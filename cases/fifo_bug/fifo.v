// Synchronous FIFO, depth=8, width=8

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

    assign full  = (count == 4'd0);
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
