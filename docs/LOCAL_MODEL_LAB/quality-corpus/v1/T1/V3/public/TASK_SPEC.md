# T1 RTL Generation: four-register AXI4-Lite subset

Complete `rtl/axi_regs.sv` using the provided module port skeleton. Implement a 32-bit slave with four word-aligned, read/write registers at byte addresses 0x00, 0x04, 0x08 and 0x0c. Reset values, in address order, are: `0x89ABCDEF, 0x76543210, 0xDEADBEEF, 0x01020304`. Reset is synchronous, active-low.

AW and W are independent channels. Accept them in either order and retain at most one pending address and one pending data beat until both have arrived. Use the captured AW address for the write. Apply each WSTRB byte lane independently. A completed write returns OKAY. An unaligned or unmapped access returns SLVERR and reads return zero. Do not accept another write while its B response is pending. A read accepts one request while no R response is pending. Hold BVALID/BRESP and RVALID/RDATA/RRESP stable until the corresponding READY handshake. No bursts, IDs, or extra AXI features are required.

Do not edit the fixed testbench or runner. Run the unchanged baseline first, use its actual diagnostics, then make the smallest source-only repair. The fixed testbench checks independent AW/W ordering, simultaneous handshakes, partial strobes, reset values, unmapped/unaligned accesses, and response backpressure. The fixed synthesis check rejects inferred latches and elaboration errors.
