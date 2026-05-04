// Testbench for 4-to-1 mux
`timescale 1ns/1ps

module tb_mux;
    reg  [1:0] sel;
    reg  [3:0] a, b, c, d;
    wire [3:0] y;

    mux4to1 uut (.sel(sel), .a(a), .b(b), .c(c), .d(d), .y(y));

    task check;
        input [1:0] s;
        input [3:0] in_a, in_b, in_c, in_d, expected;
        begin
            sel = s; a = in_a; b = in_b; c = in_c; d = in_d;
            #5;
            if (y !== expected) begin
                $display("ERROR: sel=%b a=%h b=%h c=%h d=%h expected y=%h got y=%h",
                         s, in_a, in_b, in_c, in_d, expected, y);
                $finish;
            end
        end
    endtask

    integer errors;
    initial begin
        errors = 0;

        // sel=00 -> a
        check(2'b00, 4'hA, 4'hB, 4'hC, 4'hD, 4'hA);
        // sel=01 -> b
        check(2'b01, 4'hA, 4'hB, 4'hC, 4'hD, 4'hB);
        // sel=10 -> c
        check(2'b10, 4'hA, 4'hB, 4'hC, 4'hD, 4'hC);
        // sel=11 -> d  (this will FAIL with the bug)
        sel = 2'b11; a = 4'hA; b = 4'hB; c = 4'hC; d = 4'h5;
        #5;
        if (y !== 4'h5) begin
            $display("ERROR: sel=11 expected y=5 (d), got y=%h", y);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASSED: all mux tests passed");
        else
            $display("FAILED: %0d error(s) found", errors);

        $finish;
    end
endmodule
