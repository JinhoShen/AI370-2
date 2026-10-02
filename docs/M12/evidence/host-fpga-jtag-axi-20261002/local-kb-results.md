# Ross Local Knowledge Base query results — M12 Host↔FPGA

Executed 2026-10-02 14:29 Asia/Taipei through the configured local `amd-embedded-doc-search` MCP endpoint. Query output is retained as returned; it informed the JTAG-to-AXI path choice and Tcl transaction procedure.

## Query 1

Vivado 2026.1 JTAG to AXI Master hardware AXI4-Lite transactions run_hw_axi SP701 Spartan-7


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #PG174 [Product Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: Adaptive SoC, Artix 7, FPGA, Kintex 7, Kintex UltraScale, Kintex UltraScale+, Spartan 7, Virtex 7, Virtex UltraScale+, Zynq 7000, Zynq UltraScale+, Zynq UltraScale+ MPSoC
title: JTAG to AXI Master v1.2 Product Guide (PG174)
tool: All
url: https://docs.amd.com/v/u/en-US/pg174-jtag-axi
version: All

12345678 -type write
Create a read AXI transaction with eight 32-bit data: create_hw_axi_txn rd_txn_lite [get_hw_axis hw_axi_1] -address 00000000 -type read JTAG to AXI Master v1 2 18 Send Feedback PG174 February 4, 2021 www xilinx com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #UG835 [Reference Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: Vivado Design Suite Tcl Command Reference Guide (UG835)
tool: Vivado Design Suite
url: https://docs.amd.com/r/en-US/Vivado-Design-Suite-Tcl-Command-Reference-Guide-UG835/get_hw_axi_txns
version: 2023.1, 2023.2, 2024.1, 2025.1, 2025.2, 2026.1

Title: Vivado Design Suite Tcl Command Reference Guide (UG835)  ###  Page Content: Get a list of hardware AXI transactions. Syntax get_hw_axi_txns [of_objects <args>] [regexp] [nocase] [filter <arg>] [quiet] [verbose] [<patterns>] Returns Hw_axi_txns Usage Name Description [-of_objects] Get 'hw_axi_txn' objects of these types: 'hw_axi'. [-regexp] Patterns are full regular expressions [-nocase] Perform case-insensitive matching. (valid only when -regexp specified) [-filter] Filter list with expression [-quiet] Ignore command errors [-verbose] Suspend message limits during command execution [<patterns>] Match the 'hw_axi_txn' objects against patterns. Default: * Categories Hardware, Object Description Returns the read or write transactions for the specified JTAG to AXI Master core, hw_axi object. The JTAG to AXI Master is a customizable IP core that works as an AXI Master to drive AXI transactions and drive AXI signals that are internal to the hardware device. This IP can be used in Vivado IP integrator or can be instantiated in HDL in a Vivado project. The JTAG-AXI core supports all memory-mapped AXI interfaces, except AXI4-Stream, and supports the AXI-Lite protocol. The AXI interface can be selected as a property of the core. The width of AXI data bus is customizable. This IP can drive any AXI4-Lite or Memory Mapped Slave directly, and can also be connected as the AXI Master to the interconnect. Run-time interaction with this core requires the use of the Vivado logic analyzer feature. Detailed documentation on the IP core can be found in the LogiCORE IP JTAG to AXI Master Product Guide (PG174). A tutorial showing its use can be found in the Vivado Design Suite Tutorial: Programming and Debugging (UG936). The JTAG to AXI Master core must be instantiated in the RTL code, from the Xilinx IP catalog. AXI transactions are defined as complete READ or WRITE transactions between the AXI master and various slaves. This command returns a list of hw_axi_txn objects on the hw_device, or returns an error if it fails. Arguments -of_objects <arg> - (Optional) Return the AXI Master cores of the specified hardware devices. The devices must be specified as objects using the get_hw_devices or the current_hw_device commands. Note: The -of_objects option requires objects to be specified using the get_* commands, such as get_cells or get_pins, rather than specifying objects by name. In addition, -of_objects cannot be used with a search <pattern>. -regexp - (Optional) Specifies that the search <patterns> are written as regular expressions. Both search <patterns> and -filter expressions must be written as regular expressions when this argument is used. Xilinx regular expression Tcl commands are always anchored to the start of the search string. You can add ".*" to the beginning or end of a search string to widen the search to include a substring. See http://perldoc.perl.org/perlre.html for help with regular expression syntax. Note: The Tcl built-in command regexp is not anchored, and works as a standard Tcl command. For more information refer to http://www.tcl.tk/man/tcl8.5/TclCmd/regexp.htm. -nocase - (Optional) Perform case-insensitive matching when a pattern has been specified. This argument applies to the use of -regexp only. -filter <args> - (Optional) Filter the results list with the specified expression. The -filter argument filters

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #UG908 [User Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: Vivado Design Suite User Guide: Programming and Debugging (UG908)
tool: Vivado Design Suite
url: https://docs.amd.com/r/en-US/ug908-vivado-programming-debugging/Description-of-hw_axi-and-hw_axi_txn-Tcl-Commands
version: 2023.1, 2023.2, 2024.1, 2025.1, 2026.1, 2025.2

Title: Vivado Design Suite User Guide: Programming and Debugging (UG908)  ###  Page Content: The following table contains descriptions of all Tcl commands used to interact with JTAG-to-AXI Master cores. Table 1. Description of hw_axi and hw_axi_txn Tcl Commands Tcl Command Description create_hw_axi_txn Creates hardware AXI transaction object. delete_hw_axi_txn Deletes hardware AXI transaction objects. get_hw_axi_txns Gets a list of hardware AXI transaction objects. get_hw_axis Gets a list of hardware AXI objects. refresh_hw_axi Refreshes hardware AXI object status. report_hw_axi_txn Reports formatted hardware AXI transaction data. reset_hw_axi Resets hardware AXI core state. run_hw_axi Runs hardware AXI read/write transactions and update transaction status in the corresponding hw_axi object.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #UG908 [User Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: Vivado Design Suite User Guide: Programming and Debugging (UG908)
tool: Vivado Design Suite
url: https://docs.amd.com/r/en-US/ug908-vivado-programming-debugging/Interacting-with-the-JTAG-to-AXI-Master-Debug-Core-in-Hardware
version: 2023.1, 2023.2, 2024.1, 2025.1, 2026.1, 2025.2

Title: Vivado Design Suite User Guide: Programming and Debugging (UG908)  ###  Page Content: The JTAG-to-AXI Master debug core can only be communicated with using Tcl commands. You can create and run AXI read and write transactions using the create_hw_axi_txn and run_hw_axi commands, respectively.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #PG174 [Product Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: Adaptive SoC, Artix 7, FPGA, Kintex 7, Kintex UltraScale, Kintex UltraScale+, Spartan 7, Virtex 7, Virtex UltraScale+, Zynq 7000, Zynq UltraScale+, Zynq UltraScale+ MPSoC
title: JTAG to AXI Master v1.2 Product Guide (PG174)
tool: All
url: https://docs.amd.com/v/u/en-US/pg174-jtag-axi
version: All

INTRODUCTION
Chapter 4: Design Flow Steps Interacting with the JTAG to AXI Master Core in Hardware The JTAG to AXI Master core can only be communicated with using Tcl console commands You can create and run AXI read and write transactions using these Tcl console commands A complete list of these Tcl console commands and methodology to interact with the core can be found at Hardware System Communication Using the JTAG-to-AXI Master Debug Core section of the chapter titled Debugging Logic Designs in Hardware in the Vivado Design Suite User Guide: Programming and Debugging (UG908) [Ref 6] JTAG to AXI Master v1 2 17 Send Feedback PG174 February 4, 2021 www xilinx com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #PG174 [Product Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: Adaptive SoC, Artix 7, FPGA, Kintex 7, Kintex UltraScale, Kintex UltraScale+, Spartan 7, Virtex 7, Virtex UltraScale+, Zynq 7000, Zynq UltraScale+, Zynq UltraScale+ MPSoC
title: JTAG to AXI Master v1.2 Product Guide (PG174)
tool: All
url: https://docs.amd.com/v/u/en-US/pg174-jtag-axi
version: All

1 = last data beat
JTAG to AXI Master v1 2 8 Send Feedback PG174 February 4, 2021 www xilinx com




## Query 2

PG174 JTAG to AXI create_hw_axi_txn write read run_hw_axi Tcl example -type write -address -data


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #PG174 [Product Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: Adaptive SoC, Artix 7, FPGA, Kintex 7, Kintex UltraScale, Kintex UltraScale+, Spartan 7, Virtex 7, Virtex UltraScale+, Zynq 7000, Zynq UltraScale+, Zynq UltraScale+ MPSoC
title: JTAG to AXI Master v1.2 Product Guide (PG174)
tool: All
url: https://docs.amd.com/v/u/en-US/pg174-jtag-axi
version: All

12345678 -type write
Create a read AXI transaction with eight 32-bit data: create_hw_axi_txn rd_txn_lite [get_hw_axis hw_axi_1] -address 00000000 -type read JTAG to AXI Master v1 2 18 Send Feedback PG174 February 4, 2021 www xilinx com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #UG835 [Reference Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: Vivado Design Suite Tcl Command Reference Guide (UG835)
tool: Vivado Design Suite
url: https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/create_hw_axi_txn
version: 2026.1

Title: Vivado Design Suite Tcl Command Reference Guide (UG835)  ###  Page Content: Create hardware AXI transaction object. Syntax create_hw_axi_txn [address <arg>] [data <arg>] [size <arg>] type <arg> [len <arg>] [burst <arg>] [cache <arg>] [id <arg>] [force] [quiet] [verbose] <name> <hw_axi> Returns New hardware AXI transaction object. Usage Name Description [-address] AXI read or write address. Default: Address zero [-data] Transaction data. Default: All zeroes [-size] Deprecated. Data word size in bits. This is now automatically set based on the IP core properties. -type READ or WRITE transaction. [-len] Length of the transaction in data words. Default: 1 [-burst] Burst type: INCR,FIXED or WRAP. Default: INCR [-cache] AXI cache type. Default: 3 [-id] Address ID. Default: 0 [-force] Overwrite an existing transaction with the specified name if it exists, otherwise create a new transaction. Default: 0 [-quiet] Ignore command errors [-verbose] Suspend message limits during command execution <name> Name of new object. <hw_axi> Associated hardware AXI core object. Categories Hardware Description Define a read or write transaction for the JTAG to AXI Master core, hw_axi object, specified by the get_hw_axis command. The JTAG to AXI Master is a customizable IP core that works as an AXI Master to drive AXI transactions and drive AXI signals that are internal to the hardware device. The JTAG-AXI core supports all memory-mapped AXI interfaces, except AXI4-Stream, and supports the AXI-Lite protocol. Detailed documentation on the IP core can be found in the LogiCORE IP JTAG to AXI Master Product Guide (PG174). AXI transactions are read/write burst transactions from the JTAG to AXI Master core onto AXI signals connected to the core. The AXI transaction lets you configure aspects of the read or write transaction such as the data to send and the address to send it to. These defined transactions are stored as properties of the specified hw_axi object, waiting to be run and reported using the run_hw_axi and report_hw_axi_txn commands. The command returns the name of the hw_axi_txn object created, or returns an error if it fails. Arguments -address <arg> - (Optional) Specify the address of the register on the hw_axi object to read from, or write into. Default address 0000. -data <arg> - (Optional) The data value specified in hexadecimal format to write into the address location of the hw_axi for WRITE transactions. The default data value is all zeros. -type [ READ | WRITE ] - (Required) Specify the AXI transaction to READ from the specified address, or WRITE into it. -len <arg> - (Optional) The length of the READ or WRITE transaction, specified as the number of data words to read or write, based on the -size option. The default is 1. -burst <arg> - (Optional) The type of AXI bursts to perform. Bursts can be specified as INCR, FIXED, or WRAP. The default data burst is incremental (INCR). -cache <arg> - (Optional) The AXI command cache to implement, specified in decimal form. The default value is 3. For more information on read/write cache settings refer to the LogiCORE IP Product Guide: JTAG to AXI Master (PG174). -id <arg> - (Optional) The ID

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #UG835 [Reference Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: Vivado Design Suite Tcl Command Reference Guide (UG835)
tool: Vivado Design Suite
url: https://docs.amd.com/r/en-US/Vivado-Design-Suite-Tcl-Command-Reference-Guide-UG835/report_hw_axi_txn
version: 2023.1, 2023.2, 2024.1, 2025.1, 2025.2, 2026.1

Title: Vivado Design Suite Tcl Command Reference Guide (UG835)  ###  Page Content: read_txn] This example creates AXI read and write transactions, runs the hw_axi, and reports on the results: create_hw_axi_txn wr_txn [lindex [get_hw_axis] 0] -address 80000000 \ -data {11112222 33334444 55556666 77778888} -len 4 -type write create_hw_axi_txn rd_txn [lindex [get_hw_axis] 0] -address 80000000 \ -len 4 -type read run_hw_axi [get_hw_axi_txns wr_txn] set wr_report [report_hw_axi_txn wr_txn -w 32] puts $wr_report run_hw_axi [get_hw_axi_txns rd_txn] set rd_report [report_hw_axi_txn rd_txn -w 32] puts $rd_report close_hw_target; disconnect_hw_server; See Also create_hw_axi_txn delete_hw_axi_txn get_hw_axis get_hw_axi_txns refresh_hw_axi reset_hw_axi

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #UG835 [Reference Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: Vivado Design Suite Tcl Command Reference Guide (UG835)
tool: Vivado Design Suite
url: https://docs.amd.com/r/en-US/Vivado-Design-Suite-Tcl-Command-Reference-Guide-UG835/create_hw_axi_txn
version: 2023.1, 2023.2, 2024.1, 2025.1, 2025.2

Title: Vivado Design Suite Tcl Command Reference Guide (UG835)  ###  Page Content: Create hardware AXI transaction object Syntax create_hw_axi_txn [address <arg>] [data <arg>] [size <arg>] type <arg> [len <arg>] [burst <arg>] [cache <arg>] [id <arg>] [force] [quiet] [verbose] <name> <hw_axi> Returns New hardware AXI transaction object. Usage Name Description [-address] AXI read or write address. Default: Address zero [-data] Transaction data. Default: All zeroes [-size] Deprecated. Data word size in bits. This is now automatically set based on the IP core properties. -type READ or WRITE transaction. [-len] Length of the transaction in data words. Default: 1 [-burst] Burst type: INCR,FIXED or WRAP. Default: INCR [-cache] AXI cache type. Default: 3 [-id] Address ID. Default: 0 [-force] Overwrite an existing transaction with the specified name if it exists, otherwise create a new transaction. Default: 0 [-quiet] Ignore command errors [-verbose] Suspend message limits during command execution <name> Name of new object. <hw_axi> Associated hardware AXI core object. Categories Hardware Description Define a read or write transaction for the JTAG to AXI Master core, hw_axi object, specified by the get_hw_axis command. The JTAG to AXI Master is a customizable IP core that works as an AXI Master to drive AXI transactions and drive AXI signals that are internal to the hardware device. The JTAG-AXI core supports all memory-mapped AXI interfaces, except AXI4-Stream, and supports the AXI-Lite protocol. Detailed documentation on the IP core can be found in the LogiCORE IP JTAG to AXI Master Product Guide (PG174). AXI transactions are read/write burst transactions from the JTAG to AXI Master core onto AXI signals connected to the core. The AXI transaction lets you configure aspects of the read or write transaction such as the data to send and the address to send it to. These defined transactions are stored as properties of the specified hw_axi object, waiting to be run and reported using the run_hw_axi and report_hw_axi_txn commands. The command returns the name of the hw_axi_txn object created, or returns an error if it fails. Arguments -address <arg> - (Optional) Specify the address of the register on the hw_axi object to read from, or write into. Default address 0000. -data <arg> - (Optional) The data value specified in hexadecimal format to write into the address location of the hw_axi for WRITE transactions. The default data value is all zeros. -type [ READ | WRITE ] - (Required) Specify the AXI transaction to READ from the specified address, or WRITE into it. -len <arg> - (Optional) The length of the READ or WRITE transaction, specified as the number of data words to read or write, based on the -size option. The default is 1. -burst <arg> - (Optional) The type of AXI bursts to perform. Bursts can be specified as INCR, FIXED, or WRAP. The default data burst is incremental (INCR). -cache <arg> - (Optional) The AXI command cache to implement, specified in decimal form. The default value is 3. For more information on read/write cache settings refer to the LogiCORE IP Product Guide: JTAG to AXI Master (PG174). -id <arg> - (Optional) The ID

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #UG835 [Reference Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: Vivado Design Suite Tcl Command Reference Guide (UG835)
tool: Vivado Design Suite
url: https://docs.amd.com/r/en-US/Vivado-Design-Suite-Tcl-Command-Reference-Guide-UG835/run_hw_axi
version: 2023.1, 2023.2, 2024.1, 2025.1, 2025.2, 2026.1

Title: Vivado Design Suite Tcl Command Reference Guide (UG835)  ###  Page Content: Run hardware AXI read/write transaction(s)and update transaction status in hw_axi object.. Syntax run_hw_axi [queue] [quiet] [verbose] <hw_axi_txns>... Usage Name Description [-queue] Queue Transaction. Default: 0 [-quiet] Ignore command errors [-verbose] Suspend message limits during command execution <hw_axi_txns> hardware AXI Transaction object to execute on the AXI bus. Categories Hardware Description Run the AXI transactions defined on the specified JTAG to AXI Master core. AXI transactions are created with the create_hw_axi_txns command. Run the specified hardware AXI read/write transactions on the AXI bus, and update the transaction status on the associated hw_axi object. Arguments -queue - (Optional) Run the specified hw_axi transactions in queue mode. Queued operation allows up to 16 read and 16 write transactions to be queued in the JTAG to AXI Master FIFO and issued back-to-back for low latency and higher performance between the transactions. Non-queued transactions are simply run as submitted. -quiet - (Optional) Execute the command quietly, returning no messages from the command. The command also returns TCL_OK regardless of any errors encountered during execution. Note: Any errors encountered on the command-line, while launching the command, will be returned. Only errors occurring inside the command will be trapped. -verbose - (Optional) Temporarily override any message limits and return all messages from this command. Note: Message limits can be defined with the set_msg_config command. <hw_axi_txns> - (Required) Specify the hardware AXI Transaction objects to run on the AXI bus. The objects can be returned by the get_hw_axi_txns command. Example The following example runs the AXI transactions currently defined on the specified hw_axi object: run_hw_axi [get_hw_axi_txns [get_hw_axis]] This example runs four AXI transactions in queued mode: run_hw_axi -queue [get_hw_axi_txns txn_1] [get_hw_axi_txns txn_2] \ [get_hw_axi_txns txn_3] [get_hw_axi_txns txn_4] This example creates AXI read and write transactions, runs the hw_axi, and reports on the results: create_hw_axi_txn wr_txn [lindex [get_hw_axis] 0] -address 80000000 \ -data {11112222 33334444 55556666 77778888} -len 4 -type write create_hw_axi_txn rd_txn [lindex [get_hw_axis] 0] -address 80000000 \ -len 4 -type read run_hw_axi [get_hw_axi_txns wr_txn] set wr_report [report_hw_axi_txn wr_txn -w 32] puts $wr_report run_hw_axi [get_hw_axi_txns rd_txn] set rd_report [report_hw_axi_txn rd_txn -w 32] puts $rd_report close_hw_target; disconnect_hw_server; See Also create_hw_axi_txn delete_hw_axi_txn get_hw_axis get_hw_axi_txns refresh_hw_axi reset_hw_axi

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #UG908 [User Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: Vivado Design Suite User Guide: Programming and Debugging (UG908)
tool: Vivado Design Suite
url: https://docs.amd.com/r/en-US/ug908-vivado-programming-debugging/Description-of-hw_axi-and-hw_axi_txn-Tcl-Commands
version: 2023.1, 2023.2, 2024.1, 2025.1, 2026.1, 2025.2

Title: Vivado Design Suite User Guide: Programming and Debugging (UG908)  ###  Page Content: The following table contains descriptions of all Tcl commands used to interact with JTAG-to-AXI Master cores. Table 1. Description of hw_axi and hw_axi_txn Tcl Commands Tcl Command Description create_hw_axi_txn Creates hardware AXI transaction object. delete_hw_axi_txn Deletes hardware AXI transaction objects. get_hw_axi_txns Gets a list of hardware AXI transaction objects. get_hw_axis Gets a list of hardware AXI objects. refresh_hw_axi Refreshes hardware AXI object status. report_hw_axi_txn Reports formatted hardware AXI transaction data. reset_hw_axi Resets hardware AXI core state. run_hw_axi Runs hardware AXI read/write transactions and update transaction status in the corresponding hw_axi object.




## Query 3

Vitis XRT supported devices Versal Zynq UltraScale+ FPGA platforms Spartan-7


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #Vitis-Tutorials [GitHub]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: Vitis-Tutorials - Vitis_Platform_Creation - README.md
tool: All
url: https://github.com/Xilinx/Vitis-Tutorials/blob/2026.1/Vitis_Platform_Creation/README.md
version: 2026.1

Hardware design: Creating the hardware design from scratch without any help from Vivado example design templates.

Software design: Using `createdts` and Common Image to quick start.

Verification: Vector Addition and Vitis-AIFeature TutorialsThese tutorials illustrate various platform features and how you can incorporate them into your own custom platforms.Tutorial
Device Family
Board
Platform Type
IDE Flow
Design Target
Incorporating Stream Interfaces
Generic, but using Versal AI Core as example
VCK190
Flat
Vivado &Vitis IDEHighlights:

Adding custom IP into the platform hardware
Using AXI Stream IP in platform and kernel
PetaLinux Building and System Customization
ZYNQ UltraScale+ MPSoC and Versal AI Core
ZCU104 and VCK190
Flat
Vivado &Vitis IDEHighlights: Customize the software components with PetaLinux

Hardware Design Fast Iteration with Vitis Export to Vivado
Versal AI Core
VCK190
Block Design Container
Vivado &Vitis IDEHighlights:

Skip creating the platform before v linking
Using Vivado to do design implementation and timing closure
Fast iteration for hardware design
Hardware Design Validation
Versal AI Core
VCK190
Flat & Block Design Container
Vivado &Vitis IDEHighlights:

Link kernel with XSA directly
Validation against hardware platform interfaces
Validate the hardware design with bare-metal applicationAbbreviation- XSA : Vivado exported archive file that contains hardware information required for Vitis and PetaLinux
- DFX Dynamic Function eXchange
- SOM : System-on-Modules
- DTB : Device Tree Binary
- DTBO: Device Tree Binary Overlay
Copyright  20202025 Advanced Micro Devices, Inc.

Terms and Conditions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #Alveo-Versal-Platforms [GitHub]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: Alveo-Versal-Platforms - README.md
tool: All
url: https://github.com/Xilinx/Alveo-Versal-Platforms/blob/main/README.md
version: All

Alveo Versal Vitis Platforms
[Alveo Versal Documentation](https:xilinx.github.io/Alveo-Versal-Platforms/)
Copyright 2022-2023 Xilinx

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #Alveo-Versal-Platforms [GitHub]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: Alveo-Versal-Platforms - site - README.md
tool: All
url: https://github.com/Xilinx/Alveo-Versal-Platforms/blob/main/site/README.md
version: All

Alveo Versal Vitis Platforms
[Alveo Versal Documentation](https:xilinx.github.io/Alveo-Versal-Platforms/)
Copyright 2022-2023 Xilinx

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #3011838141 [Wiki page]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: AMD Embedded+ Platforms
tool: All
url: https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/3011838141/AMD+Embedded+Platforms
version: All

(note: prebuilts not available for this device) Sapphire FPGA I/O Boards (https://www.sapphiretech.com/en/embedded-plus-explore) Supporting SW Examples: Vitis XRT Platform Vitis HW Platform: https://github.com/Xilinx/emb_plus_vitis_platforms (https://github.com/Xilinx/emb_plus_vitis_platforms) Versal APU & Runtime SW: https://github.com/Xilinx/meta-embedded-plus (https://github.com/Xilinx/meta-embedded-plus) Example applications: https://github.com/Xilinx/emb-plus-examples

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #4019978241 [Wiki page]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: 2026.1 Release Notes for Open Source Components
tool: All
url: https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/4019978241/2026.1+Release+Notes+for+Open+Source+Components
version: 2026.1

imports and examples for unsupported platforms in Vitis IDESupported ID-Only Regeneration for Spartan Ultrascale+ exampleRenamed PPK Secure control bits for Spartan Ultrascale+Added SMC support for client applicationsAdded support for xilpuf on PL-Microblaze in server mode | ASUFW | Versal Gen 2 | None | Linux crypto drivers | Versal | None | PMUFW (Platform Management Unit Firmware) | Zynq UltraScale+ MPSoC | None | FSBL | Zynq 7000Zynq UltraScale+ MPSoC | None | Image Selector, Image Recovery

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #2743468485.0 [Wiki page]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: Porting embeddedsw components to system device tree (SDT) based flow
tool: All
url: https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/2743468485/Porting+embeddedsw+components+to+system+device+tree+SDT+based+flow
version: All

| Missing Support | Isolation support for ZynqMP platforms. Only supports Versal platforms. Vitis Unified specific Gaps | Baremetal/RTOS | Missing Support | The AMD Vitis unified software still takes design file (.xsa) as an user input for some of the debugging purposes.It internally converts the .xsa into system device tree and use the generated SDT directory for rest of the build flow.Paths with spaces arent supported in the flow. Please ensure that there are no spaces in the path.




## Query 4

Spartan-7 XC7S100 hard PCI Express PCIe block device features


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC # []
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: XTP227 - AC701 PCIe Design Creation
tool: All
url: https://docs.amd.com/v/u/en-US/XTP227-AC701-PCIe-Design-Creation
version: All

INTRODUCTION
Generate x4 Gen 2 PCIe Core Right click on 7 Series Integrated Block for PCI Express  Select Customize IP Note: Presentation applies to the AC701

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC # []
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: XTP227 - AC701 PCIe Design Creation
tool: All
url: https://docs.amd.com/v/u/en-US/XTP227-AC701-PCIe-Design-Creation
version: All

INTRODUCTION
Generate x4 Gen 2 PCIe Core Select 7 Series Integrated Block for PCI Express, v3 0 under Standard Bus Interfaces Note: Presentation applies to the AC701

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC # []
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: XTP227 - AC701 PCIe Design Creation
tool: All
url: https://docs.amd.com/v/u/en-US/XTP227-AC701-PCIe-Design-Creation
version: All

7 Series Integrated Block for PCI Express
 See PG054 for details Note: Presentation applies to the AC701

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #UG341 [User Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: LogiCORE IP Endpoint Block Plus v1.15 for PCI Express User Guide (UG341)
tool: All
url: https://docs.amd.com/v/u/en-US/pcie_blk_plus_ug341
version: All

INTRODUCTION
Endpoint Block Plus for PCI Express User Guide www xilinx com UG341 June 22, 2011

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC # []
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: XTP227 - AC701 PCIe Design Creation
tool: All
url: https://docs.amd.com/v/u/en-US/XTP227-AC701-PCIe-Design-Creation
version: All

INTRODUCTION
Generate x4 Gen 2 PCIe Core Click Finish Note: Presentation applies to the AC701

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOC #UG185 [User Guide]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
family: All
title: LogiCORE IP Endpoint for PCI Express v3.7 User Guide (UG185)
tool: All
url: https://docs.amd.com/v/u/en-US/pci_exp_ep_ug185
version: All

7 pci_exp_txp7 Output PCI Express Transmit Positive: Serial
Differential Output 7 (+)


