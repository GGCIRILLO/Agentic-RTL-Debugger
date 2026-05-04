// Testbench for 8-bit ALU
`timescale 1ns/1ps

module tb_alu;
    reg  [7:0] a, b;
    reg  [2:0] op;
    wire [7:0] result;
    wire       zero;

    alu uut (.a(a), .b(b), .op(op), .result(result), .zero(zero));

    integer errors;

    task check;
        input [7:0] in_a, in_b;
        input [2:0] in_op;
        input [7:0] expected;
        input [64*8-1:0] label;
        begin
            a = in_a; b = in_b; op = in_op;
            #5;
            if (result !== expected) begin
                $display("ERROR [%0s]: a=%h b=%h op=%0d expected=%h got=%h",
                         label, in_a, in_b, in_op, expected, result);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        errors = 0;

        // ADD
        check(8'h05, 8'h03, 3'd0, 8'h08, "ADD");
        check(8'hFF, 8'h01, 3'd0, 8'h00, "ADD_overflow");

        // SUB
        check(8'h0A, 8'h03, 3'd1, 8'h07, "SUB");
        check(8'h03, 8'h05, 3'd1, 8'hFE, "SUB_borrow");

        // AND
        check(8'hF0, 8'h0F, 3'd2, 8'h00, "AND");
        check(8'hAA, 8'hFF, 3'd2, 8'hAA, "AND2");

        // OR
        check(8'hF0, 8'h0F, 3'd3, 8'hFF, "OR");

        // XOR
        check(8'hAA, 8'h55, 3'd4, 8'hFF, "XOR");

        // SLT: signed comparison
        // -1 (8'hFF) < 1 (8'h01) in signed -> result=1
        check(8'hFF, 8'h01, 3'd5, 8'h01, "SLT_signed_neg_lt_pos");
        // 1 < -1 in signed -> result=0
        check(8'h01, 8'hFF, 3'd5, 8'h00, "SLT_signed_pos_gt_neg");

        // SLL: shift LEFT
        check(8'h01, 8'h03, 3'd6, 8'h08, "SLL");
        check(8'h80, 8'h01, 3'd6, 8'h00, "SLL_overflow");

        // SRL: shift right
        check(8'h80, 8'h01, 3'd7, 8'h40, "SRL");

        if (errors == 0)
            $display("PASSED: all ALU tests passed");
        else
            $display("FAILED: %0d error(s) found", errors);

        $finish;
    end
endmodule
