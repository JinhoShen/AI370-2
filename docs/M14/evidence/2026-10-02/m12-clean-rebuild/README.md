# M12 clean rebuild evidence

A clean out-of-tree Vivado 2026.1 build exercised the checked-in M12 source and build script without changing the preserved GUI project or programming SP701. The build exited 0 and generated a bitstream. The routed DRC report contains warnings/advisories but no blocking errors. Timing summary reports all user constraints met (WNS 0.616 ns, TNS 0.000 ns).

The generated bitstream is intentionally not tracked; only its SHA256, size comparison, tool transcript and reports are retained. Compared with the previously retained/programmed M12 bitstream, the rebuilt file has the same 3,687,023-byte size and differs in four bytes at offsets 199, 202, 204 and 205, which are inside the `.bit` timestamp header. This is not byte-for-byte reproducibility, and the rebuilt artifact was not programmed. The physical M12 JTAG-to-AXI evidence remains the prior separately recorded run.
