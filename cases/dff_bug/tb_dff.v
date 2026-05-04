// Testbench for D flip-flop
`timescale 1ns/1ps

module tb_dff;
    reg clk, rst, d;
    wire q;

    dff uut (.clk(clk), .rst(rst), .d(d), .q(q));

    // 10 ns clock period
    initial clk = 0;
    always #5 clk = ~clk;

    integer errors;
    initial begin
        errors = 0;
        rst = 1; d = 0;
        @(posedge clk); #1;

        // After reset, q must be 0
        assert (q === 1'b0) else begin
            $error("after reset expected q=0, got q=%b", q);
            errors = errors + 1;
        end

        // Deassert reset, drive d=1
        rst = 0; d = 1;
        
        // Check at negedge. q should NOT change yet.
        @(negedge clk); #1;
        assert (q === 1'b0) else begin
            $error("expected q to remain 0 on negedge, got q=%b", q);
            errors = errors + 1;
        end

        // Check at posedge. q should now be 1.
        @(posedge clk); #1;
        assert (q === 1'b1) else begin
            $error("expected q=1 after d=1 posedge, got q=%b", q);
            errors = errors + 1;
        end

        // Drive d=0
        d = 0;
        
        // Check at negedge. q should NOT change yet.
        @(negedge clk); #1;
        assert (q === 1'b1) else begin
            $error("expected q to remain 1 on negedge, got q=%b", q);
            errors = errors + 1;
        end

        // Check at posedge. q should now be 0.
        @(posedge clk); #1;
        assert (q === 1'b0) else begin
            $error("expected q=0 after d=0 posedge, got q=%b", q);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASSED: all DFF tests passed");
        else
            $display("FAILED: %0d error(s) found", errors);

        $finish;
    end
endmodule
