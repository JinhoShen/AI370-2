#!/usr/bin/env python3
"""Build deterministic hidden/public fixtures for the FPGA quality corpus."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "docs/LOCAL_MODEL_LAB/quality-corpus/v1"

PORTS = """module axi_regs (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic [7:0]  s_axi_awaddr,
  input  logic        s_axi_awvalid,
  output logic        s_axi_awready,
  input  logic [31:0] s_axi_wdata,
  input  logic [3:0]  s_axi_wstrb,
  input  logic        s_axi_wvalid,
  output logic        s_axi_wready,
  output logic [1:0]  s_axi_bresp,
  output logic        s_axi_bvalid,
  input  logic        s_axi_bready,
  input  logic [7:0]  s_axi_araddr,
  input  logic        s_axi_arvalid,
  output logic        s_axi_arready,
  output logic [31:0] s_axi_rdata,
  output logic [1:0]  s_axi_rresp,
  output logic        s_axi_rvalid,
  input  logic        s_axi_rready
);\n"""

T1_SPECS = {
    "V1": ("10203040", "A5A55A5A", "0BADF00D", "55AA33CC"),
    "V2": ("C001D00D", "5A5AA5A5", "13579BDF", "2468ACE0"),
    "V3": ("89ABCDEF", "76543210", "DEADBEEF", "01020304"),
}
T2_SPECS = T1_SPECS

T1_SPEC = """# T1 RTL Generation: four-register AXI4-Lite subset

Complete `rtl/axi_regs.sv` using the provided module port skeleton. Implement a 32-bit slave with four word-aligned, read/write registers at byte addresses 0x00, 0x04, 0x08 and 0x0c. Reset values, in address order, are: `{resets}`. Reset is synchronous, active-low.

AW and W are independent channels. Accept them in either order and retain at most one pending address and one pending data beat until both have arrived. Use the captured AW address for the write. Apply each WSTRB byte lane independently. A completed write returns OKAY. An unaligned or unmapped access returns SLVERR and reads return zero. Do not accept another write while its B response is pending. A read accepts one request while no R response is pending. Hold BVALID/BRESP and RVALID/RDATA/RRESP stable until the corresponding READY handshake. No bursts, IDs, or extra AXI features are required.

Do not edit the fixed testbench or runner. Run the unchanged baseline first, use its actual diagnostics, then make the smallest source-only repair. The fixed testbench checks independent AW/W ordering, simultaneous handshakes, partial strobes, reset values, unmapped/unaligned accesses, and response backpressure. The fixed synthesis check rejects inferred latches and elaboration errors.
"""

T1_TB = r'''`timescale 1ns/1ps
module tb_axi_regs;
  localparam logic [31:0] R0 = 32'h{r0};
  localparam logic [31:0] R1 = 32'h{r1};
  localparam logic [31:0] R2 = 32'h{r2};
  localparam logic [31:0] R3 = 32'h{r3};
  logic aclk=0, aresetn=0;
  logic [7:0] awaddr=0, araddr=0;
  logic awvalid=0, wvalid=0, bready=0, arvalid=0, rready=0;
  logic [31:0] wdata=0;
  logic [3:0] wstrb=0;
  wire awready, wready, bvalid, arready, rvalid;
  wire [1:0] bresp, rresp;
  wire [31:0] rdata;
  integer checks=0;
  always #5 aclk=~aclk;
  axi_regs dut(.aclk, .aresetn, .s_axi_awaddr(awaddr), .s_axi_awvalid(awvalid),
    .s_axi_awready(awready), .s_axi_wdata(wdata), .s_axi_wstrb(wstrb),
    .s_axi_wvalid(wvalid), .s_axi_wready(wready), .s_axi_bresp(bresp),
    .s_axi_bvalid(bvalid), .s_axi_bready(bready), .s_axi_araddr(araddr),
    .s_axi_arvalid(arvalid), .s_axi_arready(arready), .s_axi_rdata(rdata),
    .s_axi_rresp(rresp), .s_axi_rvalid(rvalid), .s_axi_rready(rready));

  task automatic check_read(input logic [7:0] addr, input logic [31:0] exp_data,
                            input logic [1:0] exp_resp);
    begin
      @(negedge aclk); araddr=addr; arvalid=1; rready=0;
      do @(posedge aclk); while (!arready);
      @(negedge aclk); arvalid=0;
      wait(rvalid===1'b1);
      repeat (2) begin
        @(posedge aclk);
        if (!rvalid || rdata!==exp_data || rresp!==exp_resp)
          $fatal(1,"R response changed or mismatch addr=%h data=%h resp=%b",addr,rdata,rresp);
        checks=checks+1;
      end
      @(negedge aclk); rready=1;
      @(posedge aclk);
      @(negedge aclk); rready=0;
    end
  endtask

  task automatic finish_write(input logic [1:0] exp_resp);
    begin
      wait(bvalid===1'b1);
      repeat (2) begin
        @(posedge aclk);
        if (!bvalid || bresp!==exp_resp)
          $fatal(1,"B response changed or mismatch resp=%b",bresp);
        checks=checks+1;
      end
      @(negedge aclk); bready=1;
      @(posedge aclk);
      @(negedge aclk); bready=0;
    end
  endtask

  task automatic write_aw_first(input logic [7:0] addr, input logic [31:0] data,
                                 input logic [3:0] strb, input logic [1:0] resp);
    begin
      @(negedge aclk); awaddr=addr; awvalid=1;
      do @(posedge aclk); while (!awready);
      @(negedge aclk); awvalid=0;
      repeat (2) @(posedge aclk);
      @(negedge aclk); wdata=data; wstrb=strb; wvalid=1;
      do @(posedge aclk); while (!wready);
      @(negedge aclk); wvalid=0;
      finish_write(resp);
    end
  endtask

  task automatic write_w_first(input logic [7:0] addr, input logic [31:0] data,
                                input logic [3:0] strb, input logic [1:0] resp);
    begin
      @(negedge aclk); wdata=data; wstrb=strb; wvalid=1;
      do @(posedge aclk); while (!wready);
      @(negedge aclk); wvalid=0;
      repeat (2) @(posedge aclk);
      @(negedge aclk); awaddr=addr; awvalid=1;
      do @(posedge aclk); while (!awready);
      @(negedge aclk); awvalid=0;
      finish_write(resp);
    end
  endtask

  task automatic write_together(input logic [7:0] addr, input logic [31:0] data,
                                 input logic [3:0] strb, input logic [1:0] resp);
    begin
      @(negedge aclk); awaddr=addr; awvalid=1; wdata=data; wstrb=strb; wvalid=1;
      do @(posedge aclk); while (!(awready && wready));
      @(negedge aclk); awvalid=0; wvalid=0;
      finish_write(resp);
    end
  endtask

  initial begin
    repeat (3) @(posedge aclk);
    @(negedge aclk); aresetn=1;
    check_read(8'h00,R0,2'b00); check_read(8'h04,R1,2'b00);
    check_read(8'h08,R2,2'b00); check_read(8'h0c,R3,2'b00);
    write_aw_first(8'h00,32'h12345678,4'hf,2'b00);
    check_read(8'h00,32'h12345678,2'b00);
    write_w_first(8'h04,32'hA1B2C3D4,4'hf,2'b00);
    check_read(8'h04,32'hA1B2C3D4,2'b00);
    write_together(8'h08,32'hFFEEDDCC,4'hf,2'b00);
    check_read(8'h08,32'hFFEEDDCC,2'b00);
    write_together(8'h00,32'hAA00CC00,4'b0101,2'b00);
    check_read(8'h00,32'h12005600,2'b00);
    write_aw_first(8'h10,32'h12345678,4'hf,2'b10);
    write_w_first(8'h03,32'h12345678,4'hf,2'b10);
    check_read(8'h10,32'h00000000,2'b10);
    check_read(8'h03,32'h00000000,2'b10);
    if (checks < 32) $fatal(1,"scenario coverage incomplete checks=%0d",checks);
    $display("QUALITY_T1_PASS checks=%0d",checks);
    $finish;
  end
  initial begin #200000; $fatal(1,"T1 simulation watchdog"); end
endmodule
'''


def reference_dut(resets: tuple[str, ...]) -> str:
    init = "\n".join(f"      regs[{i}] <= 32'h{value};" for i, value in enumerate(resets))
    return PORTS + f'''  logic [31:0] regs [0:3];
  logic aw_pending, w_pending;
  logic [7:0] aw_hold;
  logic [31:0] wd_hold;
  logic [3:0] ws_hold;
  logic aw_hs, w_hs;
  logic [7:0] selected_aw;
  logic [31:0] selected_wd;
  logic [3:0] selected_ws;
  logic selected_aw_valid, selected_w_valid;
  logic [1:0] write_resp;
  integer b;
  assign s_axi_awready = aresetn && !aw_pending && !s_axi_bvalid;
  assign s_axi_wready = aresetn && !w_pending && !s_axi_bvalid;
  assign s_axi_arready = aresetn && !s_axi_rvalid;
  always_comb begin
    selected_aw = aw_pending ? aw_hold : s_axi_awaddr;
    selected_wd = w_pending ? wd_hold : s_axi_wdata;
    selected_ws = w_pending ? ws_hold : s_axi_wstrb;
    selected_aw_valid = aw_pending || (s_axi_awvalid && s_axi_awready);
    selected_w_valid = w_pending || (s_axi_wvalid && s_axi_wready);
    aw_hs = s_axi_awvalid && s_axi_awready;
    w_hs = s_axi_wvalid && s_axi_wready;
    write_resp = (selected_aw[1:0] == 0 && selected_aw[7:4] == 0) ? 2'b00 : 2'b10;
  end
  always_ff @(posedge aclk) begin
    if (!aresetn) begin
{init}
      aw_pending <= 0; w_pending <= 0; aw_hold <= 0; wd_hold <= 0; ws_hold <= 0;
      s_axi_bvalid <= 0; s_axi_bresp <= 0; s_axi_rvalid <= 0; s_axi_rresp <= 0; s_axi_rdata <= 0;
    end else begin
      if (s_axi_bvalid && s_axi_bready) s_axi_bvalid <= 0;
      if (aw_hs) begin aw_hold <= s_axi_awaddr; aw_pending <= 1; end
      if (w_hs) begin wd_hold <= s_axi_wdata; ws_hold <= s_axi_wstrb; w_pending <= 1; end
      if (selected_aw_valid && selected_w_valid && !s_axi_bvalid) begin
        aw_pending <= 0; w_pending <= 0; s_axi_bvalid <= 1; s_axi_bresp <= write_resp;
        if (write_resp == 0) begin
          case (selected_aw[3:2])
            0: for (b=0;b<4;b=b+1) if (selected_ws[b]) regs[0][8*b +: 8] <= selected_wd[8*b +: 8];
            1: for (b=0;b<4;b=b+1) if (selected_ws[b]) regs[1][8*b +: 8] <= selected_wd[8*b +: 8];
            2: for (b=0;b<4;b=b+1) if (selected_ws[b]) regs[2][8*b +: 8] <= selected_wd[8*b +: 8];
            3: for (b=0;b<4;b=b+1) if (selected_ws[b]) regs[3][8*b +: 8] <= selected_wd[8*b +: 8];
          endcase
        end
      end
      if (s_axi_rvalid && s_axi_rready) s_axi_rvalid <= 0;
      if (s_axi_arvalid && s_axi_arready) begin
        s_axi_rvalid <= 1; s_axi_rresp <= 2'b00; s_axi_rdata <= 0;
        if (s_axi_araddr[1:0] != 0 || s_axi_araddr[7:4] != 0) s_axi_rresp <= 2'b10;
        else case (s_axi_araddr[3:2])
          0: s_axi_rdata <= regs[0]; 1: s_axi_rdata <= regs[1];
          2: s_axi_rdata <= regs[2]; 3: s_axi_rdata <= regs[3];
        endcase
      end
    end
  end
endmodule
'''


def write_manifest(folder: Path) -> dict:
    files = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            files[path.relative_to(folder).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = {"schema_version": 1, "task": folder.parent.name, "variant": folder.name, "files": files}
    (folder / "SHA256SUMS.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return payload


def build_t1() -> list[dict]:
    records = []
    for variant, resets in T1_SPECS.items():
        folder = CORPUS / "T1" / variant
        manifest_path = folder / "SHA256SUMS.json"
        if folder.exists():
            if not manifest_path.is_file():
                raise RuntimeError(f"Refusing to overwrite incomplete corpus variant: {folder}")
            saved = json.loads(manifest_path.read_text())
            actual = {}
            for existing in sorted(folder.rglob("*")):
                if existing.is_file() and existing != manifest_path:
                    actual[existing.relative_to(folder).as_posix()] = hashlib.sha256(existing.read_bytes()).hexdigest()
            if actual != saved.get("files"):
                raise RuntimeError(f"Frozen corpus integrity check failed: {folder}")
            records.append(saved)
            continue
        public = folder / "public/rtl"
        private = folder / "private"
        public.mkdir(parents=True)
        private.mkdir(parents=True)
        reset_str = ", ".join(f"0x{x}" for x in resets)
        (folder / "public/TASK_SPEC.md").write_text(T1_SPEC.format(resets=reset_str))
        (public / "axi_regs.sv").write_text(PORTS + "  // Complete this module using TASK_SPEC.md.\nendmodule\n")
        (private / "tb_axi_regs.sv").write_text(T1_TB.format(r0=resets[0], r1=resets[1], r2=resets[2], r3=resets[3]))
        (private / "reference_axi_regs.sv").write_text(reference_dut(resets))
        records.append(write_manifest(folder))
    return records


def build_t2() -> list[dict]:
    records = []
    for variant, resets in T2_SPECS.items():
        folder = CORPUS / "T2" / variant
        manifest_path = folder / "SHA256SUMS.json"
        if folder.exists():
            if not manifest_path.is_file():
                raise RuntimeError(f"Refusing to overwrite incomplete corpus variant: {folder}")
            saved = json.loads(manifest_path.read_text())
            actual = {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(folder.rglob("*")) if p.is_file() and p != manifest_path}
            if actual != saved.get("files"):
                raise RuntimeError(f"Frozen corpus integrity check failed: {folder}")
            records.append(saved)
            continue
        public = folder / "public/rtl"
        private = folder / "private"
        public.mkdir(parents=True)
        private.mkdir(parents=True)
        correct = reference_dut(resets)
        if variant == "V1":
            seeded = correct.replace(
                "assign s_axi_awready = aresetn && !aw_pending && !s_axi_bvalid;",
                "assign s_axi_awready = aresetn && !aw_pending && !s_axi_bvalid && s_axi_wvalid;",
            )
        elif variant == "V2":
            seeded = correct.replace(
                "assign s_axi_wready = aresetn && !w_pending && !s_axi_bvalid;",
                "assign s_axi_wready = aresetn && !w_pending && !s_axi_bvalid && s_axi_awvalid;",
            )
        else:
            seeded = correct.replace("selected_aw = aw_pending ? aw_hold : s_axi_awaddr;", "selected_aw = s_axi_awaddr;")
            seeded = seeded.replace("selected_wd = w_pending ? wd_hold : s_axi_wdata;", "selected_wd = s_axi_wdata;")
        if seeded == correct:
            raise RuntimeError(f"could not generate the expected T2 {variant} defect")
        reset_str = ", ".join(f"0x{x}" for x in resets)
        spec = """# T2 RTL Debug: independent AXI4-Lite write channels

The supplied four-register AXI4-Lite slave compiles but loses writes when AW and W do not arrive in the same cycle. Diagnose the fixed baseline XSim failure and repair only `rtl/axi_regs.sv`. The required register map, reset values, WSTRB behavior, response codes, and backpressure behavior are specified below. Keep the existing module interface.

Registers at 0x00, 0x04, 0x08 and 0x0c reset respectively to `{resets}`. Reset is synchronous active-low. AW and W are independent; accept them in either order and retain at most one pending channel beat until the other arrives. Store at the captured AW address, apply WSTRB byte lanes independently, and return OKAY. Unaligned/unmapped transactions return SLVERR (read data zero). Hold B and R response payloads stable until handshake. Do not change the testbench, task specification or runner. Run the unchanged baseline first; then diagnose and repair the source. The fixed XSim and synthesis checks are authoritative.
""".format(resets=reset_str)
        testbench = T1_TB.format(r0=resets[0], r1=resets[1], r2=resets[2], r3=resets[3])
        # Perturb the master payload after a single-channel handshake. A correct
        # slave must use the captured beat, not the now-changing input bus.
        testbench = testbench.replace("@(negedge aclk); awvalid=0;\n      repeat (2) @(posedge aclk);\n      @(negedge aclk); wdata=data;", "@(negedge aclk); awvalid=0; awaddr=8'hfc;\n      repeat (2) @(posedge aclk);\n      @(negedge aclk); wdata=data;")
        testbench = testbench.replace("@(negedge aclk); wvalid=0;\n      repeat (2) @(posedge aclk);\n      @(negedge aclk); awaddr=addr;", "@(negedge aclk); wvalid=0; wdata=32'hDEADBEEF; wstrb=0;\n      repeat (2) @(posedge aclk);\n      @(negedge aclk); awaddr=addr;")
        (folder / "public/TASK_SPEC.md").write_text(spec)
        (public / "axi_regs.sv").write_text(seeded)
        (private / "tb_axi_regs.sv").write_text(testbench)
        (private / "reference_axi_regs.sv").write_text(correct)
        records.append(write_manifest(folder))
    return records


def build_t3() -> list[dict]:
    records = []
    for variant, resets in T1_SPECS.items():
        folder = CORPUS / "T3" / variant
        manifest_path = folder / "SHA256SUMS.json"
        if folder.exists():
            if not manifest_path.is_file():
                raise RuntimeError(f"Refusing to overwrite incomplete corpus variant: {folder}")
            saved = json.loads(manifest_path.read_text())
            actual = {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(folder.rglob("*")) if p.is_file() and p != manifest_path}
            if actual != saved.get("files"):
                raise RuntimeError(f"Frozen corpus integrity check failed: {folder}")
            records.append(saved)
            continue
        public = folder / "public"
        private = folder / "private/mutants"
        public.mkdir(parents=True)
        private.mkdir(parents=True)
        resets_text = ", ".join(f"0x{x}" for x in resets)
        spec = f"""# T3 Testbench Generation: self-checking AXI4-Lite regression

Create `sim/tb_axi_regs.sv`, a self-checking SystemVerilog testbench for the supplied correct `axi_regs` design. Only the testbench is editable. The public module interface and four register addresses are in `rtl/axi_regs.sv`; reset values in order are {resets_text}.

Exercise and check all of the following: reset values; AW-before-W; W-before-AW; simultaneous AW/W; all four WSTRB byte lanes including a partial write; unmapped and unaligned accesses; B response backpressure with stable BVALID/BRESP; R response backpressure with stable RVALID/RDATA/RRESP; and multiple consecutive transactions. Use self-checking assertions or `$fatal` on any mismatch and a finite watchdog. Do not alter the DUT, task specification, runner or hidden test data.

The fixed evaluator runs your testbench on the correct DUT and on five hidden mutated DUTs. PASS requires the correct DUT to print `QUALITY_T3_PASS`, emit each required `QUALITY_T3_SCENARIO_<name>_PASS` marker, and every mutant to fail without the terminal marker. Required names: reset, aw_before_w, w_before_aw, simultaneous, wstrb, unmapped, b_backpressure, r_backpressure, consecutive. The evaluator itself, rather than a language model, checks mutation sensitivity.
"""
        (public / "TASK_SPEC.md").write_text(spec)
        (public / "rtl").mkdir()
        (public / "sim").mkdir()
        (public / "rtl/axi_regs.sv").write_text(reference_dut(resets))
        (public / "sim/tb_axi_regs.sv").write_text("""`timescale 1ns/1ps
module tb_axi_regs;
  // Write a self-checking testbench following TASK_SPEC.md.
  initial begin
    $display(\"T3 testbench not implemented\");
    $finish;
  end
endmodule
""")
        golden = T1_TB.format(r0=resets[0], r1=resets[1], r2=resets[2], r3=resets[3])
        golden = golden.replace("QUALITY_T1_PASS", "QUALITY_T3_PASS").replace("T1 simulation watchdog", "T3 simulation watchdog")
        marker_block = "\n".join(f'    $display("QUALITY_T3_SCENARIO_{name}_PASS");' for name in (
            "reset", "aw_before_w", "w_before_aw", "simultaneous", "wstrb", "unmapped",
            "b_backpressure", "r_backpressure", "consecutive",
        ))
        golden = golden.replace('    if (checks < 32) $fatal(1,"scenario coverage incomplete checks=%0d",checks);',
                                '    if (checks < 32) $fatal(1,"scenario coverage incomplete checks=%0d",checks);\n' + marker_block)
        (folder / "private/reference_tb_axi_regs.sv").write_text(golden)
        correct = reference_dut(resets)
        mutants = {
            "ignore-wstrb": correct.replace("if (selected_ws[b])", "if (1'b1)"),
            "same-cycle-aw-w": correct.replace(
                "assign s_axi_awready = aresetn && !aw_pending && !s_axi_bvalid;",
                "assign s_axi_awready = aresetn && !aw_pending && !s_axi_bvalid && s_axi_wvalid;"),
            "unstable-read-response": correct.replace(
                "if (s_axi_rvalid && s_axi_rready) s_axi_rvalid <= 0;",
                "if (s_axi_rvalid && !s_axi_rready) s_axi_rdata <= ~s_axi_rdata;\n      if (s_axi_rvalid && s_axi_rready) s_axi_rvalid <= 0;"),
            "wrong-reset-value": correct.replace(f"regs[0] <= 32'h{resets[0]};", "regs[0] <= 32'h00000000;", 1),
            "unstable-write-response": correct.replace(
                "if (s_axi_bvalid && s_axi_bready) s_axi_bvalid <= 0;",
                "if (s_axi_bvalid && !s_axi_bready) s_axi_bresp <= ~s_axi_bresp;\n      if (s_axi_bvalid && s_axi_bready) s_axi_bvalid <= 0;"),
        }
        for name, source_text in mutants.items():
            if source_text == correct:
                raise RuntimeError(f"T3 mutation was not applied: {name}")
            (private / f"{name}.sv").write_text(source_text)
        records.append(write_manifest(folder))
    return records


def build_t4() -> list[dict]:
    """Build multi-file XSim elaboration repair exercises with immutable TBs."""
    records = []
    cases = {
        "V1": (".operation(op)", ".op(op)", "port"),
        "V2": ("alu_core u_alu", "alu u_alu", "module"),
        "V3": (".valid_o(valid)", ".valid(valid)", "port/width"),
    }
    for variant, (broken, fixed, defect) in cases.items():
        folder = CORPUS / "T4" / variant
        manifest_path = folder / "SHA256SUMS.json"
        if folder.exists():
            if not manifest_path.is_file():
                raise RuntimeError(f"Refusing to overwrite incomplete corpus variant: {folder}")
            saved = json.loads(manifest_path.read_text())
            actual = {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(folder.rglob("*")) if p.is_file() and p != manifest_path}
            if actual != saved.get("files"):
                raise RuntimeError(f"Frozen corpus integrity check failed: {folder}")
            records.append(saved)
            continue
        public, private = folder / "public", folder / "private"
        (public / "rtl").mkdir(parents=True)
        private.mkdir(parents=True)
        package = """package alu_pkg;
  localparam integer DATA_W = 8;
  typedef enum logic [1:0] {ADD=2'b00, XOR_OP=2'b01, AND_OP=2'b10, SUB=2'b11} opcode_t;
endpackage
"""
        alu = """module alu(input logic [7:0] a,b, input logic [1:0] op,
  output logic [7:0] y, output logic valid);
  import alu_pkg::*;
  always_comb begin
    valid = 1'b1;
    case (opcode_t'(op))
      ADD: y = a + b; XOR_OP: y = a ^ b; AND_OP: y = a & b; SUB: y = a - b;
      default: begin y = '0; valid = 1'b0; end
    endcase
  end
endmodule
"""
        top = """module calc_top(input logic [7:0] a,b, input logic [1:0] op,
  output logic [7:0] y, output logic valid);
  logic [7:0] result;
  alu u_alu(.a(a), .b(b), .op(op), .y(result), .valid(valid));
  assign y = result;
endmodule
"""
        seeded = top.replace(fixed, broken, 1)
        (public / "rtl/alu_pkg.sv").write_text(package)
        (public / "rtl/alu.sv").write_text(alu)
        (public / "rtl/calc_top.sv").write_text(seeded)
        spec = f"""# T4 Vivado XSim: multi-file compile and elaboration repair

The isolated SystemVerilog project has a {defect} integration defect in its public RTL. Read the original XSim diagnostics, identify the source of the compile/elaboration failure, and make the smallest repair. The public interface and behavior are fixed: `calc_top` computes 8-bit ADD, XOR, AND, or SUB selected by `op` and asserts `valid`. Only files under `rtl/` may be edited. Do not edit this task, hidden testbench, runner, or Tcl.

The evaluator compiles package, leaf module, and top in fixed order using Vivado 2026.1, elaborates `tb_calc_top`, and runs the self-checking regression. Baseline diagnostics must be observed before any repair. PASS requires all tool exit codes to be zero and `QUALITY_T4_PASS` in the simulation log.
"""
        (public / "TASK_SPEC.md").write_text(spec)
        tb = """`timescale 1ns/1ps
module tb_calc_top;
  logic [7:0] a,b,y; logic [1:0] op; logic valid;
  calc_top dut(.a(a),.b(b),.op(op),.y(y),.valid(valid));
  task automatic check(input logic [7:0] aa,bb,input logic [1:0] oo,input logic [7:0] expected);
    begin a=aa;b=bb;op=oo;#1;if(!valid || y!==expected) $fatal(1,"mismatch op=%0d got=%h expected=%h",oo,y,expected); end
  endtask
  initial begin
    check(8'h15,8'h22,0,8'h37); check(8'hf0,8'h0f,1,8'hff);
    check(8'hcc,8'h0f,2,8'h0c); check(8'h03,8'h05,3,8'hfe);
    check(8'hff,8'h01,0,8'h00);
    $display("QUALITY_T4_PASS checks=5"); $finish;
  end
  initial begin #1000;$fatal(1,"T4 watchdog");end
endmodule
"""
        (private / "tb_calc_top.sv").write_text(tb)
        records.append(write_manifest(folder))
    return records


def build_t5() -> list[dict]:
    records = []
    variants = {
        "V1": ("case (sel)\n      3'd0: y = a + b;\n      3'd1: y = a ^ b;\n      3'd2: y = a & b;\n      3'd3: y = a - b;\n    endcase", "case (sel)\n      3'd0: y = a + b;\n      3'd1: y = a ^ b;\n      3'd2: y = a & b;\n      3'd3: y = a - b;\n      default: y = 8'h00;\n    endcase"),
        "V2": ("if (sel == 0) y = a + b;\n    else if (sel == 1) y = a ^ b;\n    else if (sel == 2) y = a & b;\n    else if (sel == 3) y = a - b;", "case (sel)\n      0:y=a+b; 1:y=a^b; 2:y=a&b; 3:y=a-b; default:y=8'h00;\n    endcase"),
        "V3": ("casez (sel)\n      3'b0??: y = a + b;\n      3'b100: y = a ^ b;\n      3'b101: y = a & b;\n      3'b110: y = a - b;\n    endcase", "case (sel)\n      0:y=a+b; 1:y=a^b; 2:y=a&b; 3:y=a-b; default:y=8'h00;\n    endcase"),
    }
    for variant, (broken, repaired) in variants.items():
        folder = CORPUS / "T5" / variant
        manifest_path = folder / "SHA256SUMS.json"
        if folder.exists():
            if not manifest_path.is_file(): raise RuntimeError(f"Refusing to overwrite incomplete corpus variant: {folder}")
            saved=json.loads(manifest_path.read_text())
            actual={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob("*")) if p.is_file() and p!=manifest_path}
            if actual!=saved.get("files"): raise RuntimeError(f"Frozen corpus integrity check failed: {folder}")
            records.append(saved); continue
        public, private = folder / "public", folder / "private"
        (public / "rtl").mkdir(parents=True); private.mkdir(parents=True)
        pre="""module mux_math(input logic [2:0] sel, input logic [7:0] a,b, output logic [7:0] y);
  always_comb begin
    """
        post="\n  end\nendmodule\n"
        correct=pre+repaired+post
        seeded=pre+broken+post
        (public / "rtl/mux_math.sv").write_text(seeded)
        (folder / "private/reference_mux_math.sv").write_text(correct)
        (public / "TASK_SPEC.md").write_text("""# T5 Vivado synthesis: remove inferred latch while preserving behavior

Repair `rtl/mux_math.sv`. For `sel` 0, 1, 2, 3, compute respectively 8-bit wrapping add, XOR, AND, and subtract; for selectors 4–7, output zero. `y` must be fully combinational and have no inferred latch. Only the DUT file is editable.

The fixed evaluator first runs a self-checking XSim regression (including all eight selector values), then Vivado 2026.1 synthesis for the frozen FPGA part. PASS requires the regression marker, successful synthesis, a utilization report, and no latch diagnostics. Timing closure is not required.
""")
        (private / "tb_mux_math.sv").write_text("""`timescale 1ns/1ps
module tb_mux_math;
  logic [2:0] sel; logic [7:0] a,b,y; integer i; logic [7:0] expected;
  mux_math dut(.sel(sel),.a(a),.b(b),.y(y));
  initial begin
    a=8'hd3;b=8'h37;
    for(i=0;i<8;i=i+1) begin sel=i; #1; case(i)
      0:expected=8'h0a; 1:expected=8'he4; 2:expected=8'h13; 3:expected=8'h9c;
      default:expected=0;
    endcase if(y!==expected) $fatal(1,"selector %0d got %h expected %h",i,y,expected); end
    $display("QUALITY_T5_PASS checks=8");$finish;
  end
endmodule
""")
        records.append(write_manifest(folder))
    return records


def build_t6() -> list[dict]:
    records=[]
    seeds={"V1":"return input;","V2":"return input ^ 0x00ff00ffu;","V3":"return ~(input >> 1);"}
    vectors={"V1":[0x12345678,0,0xffffffff,0xa5a5f00d],"V2":[0x89abcdef,0x01020304,0x80000000,0x55aa55aa],"V3":[0x0f0f0f0f,0xdeadbeef,0x13579bdf,0x2468ace0]}
    for variant,seed in seeds.items():
        folder=CORPUS/"T6"/variant; manifest_path=folder/"SHA256SUMS.json"
        if folder.exists():
            if not manifest_path.is_file(): raise RuntimeError(f"Refusing to overwrite incomplete corpus variant: {folder}")
            saved=json.loads(manifest_path.read_text()); actual={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob("*")) if p.is_file() and p!=manifest_path}
            if actual!=saved.get("files"): raise RuntimeError(f"Frozen corpus integrity check failed: {folder}")
            records.append(saved); continue
        public,private=folder/"public",folder/"private"; (public/"src").mkdir(parents=True); private.mkdir(parents=True)
        correct="""#include <cstdint>
std::uint32_t invert32(std::uint32_t input) { return ~input; }
"""
        (public/"src/invert32.cpp").write_text(correct.replace("return ~input;",seed))
        (folder/"private/reference_invert32.cpp").write_text(correct)
        vals=vectors[variant]; expected=[(~x)&0xffffffff for x in vals]
        tb="#include <cstdint>\n#include <cstdio>\nstd::uint32_t invert32(std::uint32_t input);\nint main(){\n"
        for x,y in zip(vals,expected): tb+=f"  if(invert32(0x{x:08x}u)!=0x{y:08x}u){{std::fprintf(stderr,\"mismatch {x:08x}\\n\");return 1;}}\n"
        tb+=f'  std::puts("QUALITY_T6_CSIM_PASS checks={len(vals)}");return 0;\n}}\n'
        (private/"testbench.cpp").write_text(tb)
        cfg="""[hls]
syn.file=src/invert32.cpp
syn.top=invert32
clock=5ns
"""
        (public/"hls_config.cfg").write_text(cfg)
        spec="""# T6 Vitis HLS: bitwise inversion kernel

Implement `std::uint32_t invert32(std::uint32_t input)` in `src/invert32.cpp` so it returns the 32-bit one's complement of the input. Only this source file is editable. Do not change the fixed HLS config or private C testbench.

The fixed Vitis HLS 2026.1 evaluator runs C simulation against four frozen vectors and C synthesis for `xc7s100fgga676-2`. PASS requires the `QUALITY_T6_CSIM_PASS` marker, successful C synthesis and a generated `invert32_csynth.rpt`. The checker does not use an LLM judge.
"""
        (public/"TASK_SPEC.md").write_text(spec)
        records.append(write_manifest(folder))
    return records


def build_t7() -> list[dict]:
    records=[]
    for variant in ("V1","V2","V3"):
        source=CORPUS/"T4"/variant; target=CORPUS/"T7"/variant; manifest_path=target/"SHA256SUMS.json"
        if target.exists():
            if not manifest_path.is_file(): raise RuntimeError(f"Refusing to overwrite incomplete corpus variant: {target}")
            saved=json.loads(manifest_path.read_text()); actual={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.rglob("*")) if p.is_file() and p!=manifest_path}
            if actual!=saved.get("files"): raise RuntimeError(f"Frozen corpus integrity check failed: {target}")
            records.append(saved); continue
        shutil.copytree(source,target,ignore=shutil.ignore_patterns("SHA256SUMS.json"))
        spec=target/"public/TASK_SPEC.md"
        spec.write_text(spec.read_text().replace("T4 Vivado XSim", "T7 AMD Ross assisted Vivado XSim").replace("QUALITY_T4_PASS", "QUALITY_T7_PASS")+
            "\nBefore any source edit or XSim validation, call the installed AMD Ross `vivado-simulate-rtl` Skill and its `references/xsim.md` guide using `ross_skill_read`, then call `ross_doc_search` for Vivado 2026.1 multi-file RTL compilation/elaboration guidance. Use both returned results in your diagnosis. Both tool calls must succeed and appear in the trace before a patch or simulation. If Ross tools are unavailable, report blocked; do not substitute another source.\n")
        tb=target/"private/tb_calc_top.sv"; tb.write_text(tb.read_text().replace("QUALITY_T4_PASS", "QUALITY_T7_PASS"))
        records.append(write_manifest(target))
    return records


def build_t8() -> list[dict]:
    records=[]
    for variant,resets in T1_SPECS.items():
        source=CORPUS/"T1"/variant; target=CORPUS/"T8"/variant; manifest_path=target/"SHA256SUMS.json"
        if target.exists():
            if not manifest_path.is_file(): raise RuntimeError(f"Refusing to overwrite incomplete corpus variant: {target}")
            saved=json.loads(manifest_path.read_text()); actual={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.rglob("*")) if p.is_file() and p!=manifest_path}
            if actual!=saved.get("files"): raise RuntimeError(f"Frozen corpus integrity check failed: {target}")
            records.append(saved); continue
        public=target/"public"; private=target/"private"; (public/"rtl").mkdir(parents=True); private.mkdir(parents=True)
        resets_text=", ".join(f"0x{x}" for x in resets)
        spec=f"""# T8 Autonomous Agent: complete RTL delivery cycle

Implement the four-register AXI4-Lite slave in `rtl/axi_regs.sv` from the interface and behavioral requirements in this file. The register reset values in order are {resets_text}. Support independent AW/W handshakes, one pending write, WSTRB byte updates, aligned addresses 0x00–0x0c, SLVERR for unsupported addresses, read response stability under backpressure, and reset. Only the DUT file is editable.

Work autonomously: inspect the starter RTL, run the unchanged baseline once, diagnose the fixed tool output, patch the design, rerun the fixed validator, and then give a concise delivery summary. The summary must contain separate lines in this exact form: `STATUS=PASS`, `XSim=PASS marker=<exact marker>`, `SYNTHESIS=PASS report=<exact utilization report path>`, and `RTL_SHA256=<final source SHA-256>`. Report only facts shown by the fixed validator output. The evaluator verifies all four statements against its actual trace, hashes, simulation log, and synthesis report.
"""
        (public/"TASK_SPEC.md").write_text(spec)
        (public/"rtl/axi_regs.sv").write_text("module axi_regs;\n  // Implement the behavior specified in TASK_SPEC.md.\nendmodule\n")
        hidden_tb=T1_TB.format(r0=resets[0],r1=resets[1],r2=resets[2],r3=resets[3]).replace("QUALITY_T1_PASS","QUALITY_T8_PASS").replace("T1 simulation watchdog","T8 simulation watchdog")
        (private/"tb_axi_regs.sv").write_text(hidden_tb)
        (private/"reference_axi_regs.sv").write_text(reference_dut(resets))
        records.append(write_manifest(target))
    return records


if __name__ == "__main__":
    print(json.dumps({"t1": build_t1(), "t2": build_t2(), "t3": build_t3(), "t4": build_t4(), "t5": build_t5(), "t6": build_t6(), "t7": build_t7(), "t8": build_t8()}, indent=2, ensure_ascii=False))
