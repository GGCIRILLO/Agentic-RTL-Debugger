// Testbench for synchronous FIFO
`timescale 1ns/1ps

module tb_fifo;
    parameter DEPTH = 8;
    parameter WIDTH = 8;

    reg             clk, rst;
    reg             wr_en, rd_en;
    reg  [WIDTH-1:0] din;
    wire [WIDTH-1:0] dout;
    wire             full, empty;

    fifo #(.DEPTH(DEPTH), .WIDTH(WIDTH)) uut (
        .clk(clk), .rst(rst),
        .wr_en(wr_en), .rd_en(rd_en),
        .din(din), .dout(dout),
        .full(full), .empty(empty)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    integer errors;
    integer i;

    task write_word;
        input [WIDTH-1:0] data;
        begin
            @(negedge clk);
            wr_en = 1; din = data; rd_en = 0;
            @(posedge clk); #1;
            wr_en = 0;
        end
    endtask

    task read_word;
        input [WIDTH-1:0] expected;
        begin
            @(negedge clk);
            rd_en = 1; wr_en = 0;
            @(posedge clk); #1;
            rd_en = 0;
            if (dout !== expected) begin
                $display("ERROR: expected dout=%h, got dout=%h", expected, dout);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        errors = 0;
        rst = 1; wr_en = 0; rd_en = 0; din = 0;
        @(posedge clk); #1;
        rst = 0;

        // After reset: FIFO must be empty, not full
        if (!empty) begin
            $display("ERROR: FIFO should be empty after reset, empty=%b full=%b", empty, full);
            errors = errors + 1;
        end
        if (full) begin
            $display("ERROR: FIFO should not be full after reset, full=%b", full);
            errors = errors + 1;
        end

        // Write 4 words
        for (i = 0; i < 4; i = i + 1)
            write_word(8'hA0 + i);

        // After 4 writes: not empty, not full
        if (empty) begin
            $display("ERROR: FIFO should not be empty after 4 writes");
            errors = errors + 1;
        end
        if (full) begin
            $display("ERROR: FIFO should not be full after 4 writes (depth=8)");
            errors = errors + 1;
        end

        // Read 4 words back and check order
        read_word(8'hA0);
        read_word(8'hA1);
        read_word(8'hA2);
        read_word(8'hA3);

        // Fill to full
        for (i = 0; i < DEPTH; i = i + 1)
            write_word(8'hB0 + i);

        if (!full) begin
            $display("ERROR: FIFO should be full after %0d writes", DEPTH);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASSED: all FIFO tests passed");
        else
            $display("FAILED: %0d error(s) found", errors);

        $finish;
    end
endmodule
