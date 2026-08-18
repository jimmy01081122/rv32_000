# RV32IMF Out-of-Order Processor ASIC 研究與實作計畫書

**文件版本：** v1.2 (G0 Frozen — 2026-08-08)
**狀態：** G0 Frozen
**專案類型：** 數位 IC 設計作品集、處理器微架構研究、ASIC PPA 分析
**目標平台：** 純模擬與 ASIC RTL-to-GDSII，不進行 FPGA 實作
**預定 ISA：** RV32IMF + Zicsr
**軟體執行環境：** Bare-metal
**主要工具：** Verilator、Spike、Yosys、OpenSTA、OpenROAD/OpenLane 2
**主要製程基準：** Nangate45 快速架構探索、SKY130HD 實體設計基準

---

# 1. 專案摘要

本專案將設計一顆可綜合、可進行 RTL-to-GDSII 實作的 32-bit RISC-V 亂序執行處理器。核心採用：

* register renaming
* physical register file
* reorder buffer
* reservation station／issue queue
* out-of-order issue and completion
* in-order retirement
* precise exception
* conservative load/store ordering
* independent integer and floating-point execution domains
* 自行設計的 IEEE 754 single-precision floating-point datapath

最終成果不只要求功能正確，還需要建立可重現的：

1. ISA compliance 流程
2. differential testing 流程
3. assertion／formal verification 流程
4. CoreMark 效能測試流程
5. synthesis、STA、place-and-route 與 PPA 分析流程
6. 微架構 design-space exploration

---

# 2. 架構重新審核結論

## 2.1 此核心應定義為 Scalar Out-of-Order，而不是完整 Superscalar

目前規格採：

* 1-wide decode
* 1-wide rename
* 1-wide dispatch
* 1-wide retirement

因此理論最大 sustained retirement IPC 為 1。

後端可以允許一條 integer/memory uop 與一條 FP uop 同時執行，以重疊不同 execution domain 的 latency，但這不代表核心是完整的 2-wide superscalar processor。

正式定位應為：

> 單指令前端與單指令提交、具多 execution domain 重疊能力的 scalar out-of-order processor。

如果後續研究 2-wide rename／dispatch／retirement，應建立為獨立延伸版本，不納入第一版完成條件。

---

## 2.2 未完整通過 F Extension 前，不得將核心標示為 RV32IMF

RISC-V F extension 不只是 FADD、FSUB 和 FMUL，還包括：

* FP load/store
* fused multiply-add
* divide
* square root
* integer/FP conversion
* comparison
* sign injection
* min/max
* classification
* rounding modes
* accrued exception flags
* NaN、infinity、subnormal、signed zero 等語意

F extension還依賴 Zicsr，並包含 32 個 32-bit floating-point registers 與 `fcsr` architectural state。

因此專案版本命名必須分開：

| 版本狀態                         | 可使用的名稱                          |
| ---------------------------- | ------------------------------- |
| 僅完成部分 FP 指令                  | RV32IM + experimental FP subset |
| 完成全部 F 指令但尚未通過完整驗證           | RV32IMF development candidate   |
| 完成 F 語意、rounding、flags 並通過測試 | RV32IMF                         |

FMADD、FMSUB、FNMSUB、FNMADD 必須具備真正 fused、single-rounding 語意，不能用已完成 rounding 的 FMUL 再接 FADD 取代。

---

## 2.3 CoreMark 不能驗證 FPU

CoreMark主要測量：

* integer operation
* branch/control behavior
* load/store behavior
* pipeline performance

其主要 workload 不含浮點運算，而且記憶體 footprint 很小，因此不能作為 FPU 或大型 memory subsystem 的驗證基準。

CoreMark 在本專案中的定位是：

> Integer pipeline、branch、load/store、OoO scheduling 與 PPA-normalized performance benchmark。

FPU 必須使用另外的 FP directed tests、random differential tests 和 F architectural tests。

---

## 2.4 RISC-V Architectural Tests 不是完整驗證流程

目前官方 `riscv-arch-test` 使用 ACT4 Framework；舊的 RISCOF 流程已被取代。ACT4 會產生 self-checking ELF，由使用者自行在 DUT 執行。官方同時明確指出 architectural certification tests 不是完整 processor verification tests。

因此不能將：

> RISC-V ISA tests 全數通過

等同於：

> OoO 微架構沒有錯誤。

仍必須進行：

* dependency stress tests
* branch recovery tests
* LSQ ordering tests
* random differential testing
* formal invariant checking
* long-latency completion and flush tests

---

# 3. 專案目標與非目標

## 3.1 必須完成

1. 可綜合 RV32IMF + Zicsr processor RTL
2. scalar out-of-order execution
3. integer/FP register renaming
4. physical register files
5. ROB-based in-order retirement
6. precise synchronous exceptions
7. branch speculative execution與 recovery
8. conservative load/store queue
9. store-to-load forwarding
10. 自行設計 integer multiplier/divider
11. 自行設計 FP add、multiply、FMA、divide、sqrt、conversion 與 miscellaneous operations
12. bare-metal ELF 執行
13. Spike commit-level differential testing
14. RISC-V ACT4 architectural test execution
15. CoreMark execution與 cycle-based analysis
16. Yosys synthesis
17. OpenSTA timing analysis
18. OpenROAD/OpenLane physical implementation
19. architecture parameter sweep
20. PPA 與 IPC trade-off 報告

## 3.2 不納入第一版

* FPGA implementation
* Linux
* Supervisor mode
* MMU/TLB
* virtual memory
* RV32C
* RV32A
* cache coherence
* non-blocking cache
* speculative load bypass across unresolved stores
* memory-dependence predictor
* simultaneous multithreading
* debug module/JTAG
* asynchronous interrupt完整支援
* 2-wide rename／dispatch
* 2-wide retirement

---

# 4. 最終基線規格

| 項目                       | 基線規格                                      |
| ------------------------ | ----------------------------------------- |
| ISA                      | RV32IMF + Zicsr                           |
| Privilege                | Machine-mode execution environment subset |
| Instruction width        | 固定 32-bit，不支援 C                           |
| Fetch width              | 1                                         |
| Decode width             | 1                                         |
| Rename width             | 1                                         |
| Dispatch width           | 1                                         |
| Retirement width         | 1                                         |
| Maximum issue            | 1 integer/memory + 1 FP                   |
| ROB                      | 16 entries                                |
| Integer PRF              | 48 × 32-bit                               |
| FP PRF                   | 48 × 32-bit                               |
| Integer Issue Queue      | 8 entries                                 |
| FP Issue Queue           | 4 entries                                 |
| Load Queue               | 4 entries                                 |
| Store Queue              | 4 entries                                 |
| Instruction Queue        | 8 entries                                 |
| Integer ALU              | 1 principal ALU                           |
| Branch unit              | 與 integer execution cluster 整合            |
| Integer multiplier       | pipelined 或固定 latency                     |
| Integer divider          | iterative、non-pipelined                   |
| FP add/sub               | pipelined                                 |
| FP multiply              | pipelined                                 |
| FP FMA                   | pipelined、single rounding                 |
| FP divide/sqrt           | iterative                                 |
| Memory interface         | blocking、ready/valid                      |
| Outstanding load request | 1                                         |
| Store visibility         | retirement 時才能對外可見                        |
| Branch predictor         | static baseline                           |
| Recovery                 | ROB reverse rollback                      |
| Integer writeback ports  | 1                                         |
| FP writeback ports       | 1                                         |
| Cache                    | 無，使用 testbench memory model               |
| FPGA                     | 不支援                                       |

---

# 5. 整體微架構

```text
PC Generation
    ↓
Instruction Fetch
    ↓
Instruction Queue
    ↓
Decode / Uop Generation
    ↓
Rename / ROB Allocation / LSQ Allocation
    ↓
Dispatch
    ├── Integer Issue Queue
    ├── FP Issue Queue
    └── Load / Store Queue
          ↓
Execution Units
    ├── Integer ALU / Branch
    ├── Integer Multiply / Divide
    ├── Load / Store Unit
    ├── FP Add / Multiply / FMA
    └── FP Divide / Square Root / Conversion
          ↓
Writeback Arbitration
          ↓
Physical Register Files + ROB Completion
          ↓
In-order Retirement
```

---

# 6. Pipeline 與資料流規劃

## 6.1 Frontend

建議邏輯階段：

```text
F0: PC selection
F1: instruction memory request
F2: instruction response / instruction queue
D0: decode and immediate generation
R0: rename / allocate
D1: dispatch
```

Frontend baseline：

* conditional branch：predict not taken
* JAL：decode 後計算 direct target
* JALR：執行階段計算 target
* no compressed instructions
* instruction address 必須 4-byte aligned
* memory response 使用 ready/valid handshake
* instruction queue 吸收 memory latency與後端 stall

後續 predictor 研究版本：

* direct-mapped BTB
* 2-bit BHT
* optional return-address stack

---

## 6.2 Micro-op 格式

Micro-op 必須是後端唯一接受的指令描述，不應讓 execution unit 重複解析完整 instruction。

```systemverilog
// Note: See uop_spec.md §15 for the normative definition of decoded_uop_t
typedef struct packed {
    logic [31:0] pc;
    logic [31:0] insn;
    fetch_meta_t fetch;

    uop_op_e     op;
    fu_class_e   fu_class;

    decoded_src_t src0;
    decoded_src_t src1;
    decoded_src_t src2;
    decoded_dst_t dst;

    imm_kind_e    imm_kind;
    logic [31:0]  imm;
    mem_ctrl_t    mem;
    branch_ctrl_t branch;
    csr_ctrl_t    csr;
    fp_ctrl_t     fp;

    logic serializing;
    logic requires_rob_head;
    logic alloc_lq;
    logic alloc_sq;

    exception_t exception;
} decoded_uop_t;
```

不能只使用 `is_fp` 表示 register domain，因為以下指令會跨 integer／FP domain：

* FCVT.W.S
* FCVT.WU.S
* FCVT.S.W
* FCVT.S.WU
* FMV.X.W
* FMV.W.X
* FLW
* FSW

---

# 7. Rename Architecture

## 7.1 分離式 rename domain

```text
Integer Domain:
    Integer RAT
    Integer Retirement Map
    Integer Free List
    Integer PRF Ready Table
    Integer PRF

FP Domain:
    FP RAT
    FP Retirement Map
    FP Free List
    FP PRF Ready Table
    FP PRF
```

### Integer register x0

* 永遠 mapping 到 reserved physical register `p0`
* `p0` 永遠 ready
* `p0` 不在 free list
* 對 x0 的 write 不配置 physical destination
* 對 x0 的 write 不產生 PRF writeback

### Floating-point f0

`f0` 是一般 floating-point register，不是 constant zero register。

---

## 7.2 Rename 操作

目的 register 指令在 rename 時：

1. 從 RAT 取得 source physical tags
2. 從 ready table 取得 source ready state
3. 從 free list 配置新 physical destination
4. 讀取目前 architectural destination 的舊 mapping
5. RAT 更新為新 mapping
6. ROB 保存：

   * architectural destination
   * new physical destination
   * old physical destination
   * destination domain
7. 新 physical destination ready bit 清為 0

retirement 時：

1. retirement map 更新為 new physical destination
2. old physical destination 回收至 free list
3. ROB head 釋放

禁止在 writeback 時回收 old physical register。

---

# 8. Reorder Buffer

## 8.1 ROB Entry

```systemverilog
// Note: See uop_spec.md §20 for the normative definition of rob_entry_t
typedef struct packed {
    logic        valid;
    logic        completed;
    rob_tag_t    tag;

    logic [31:0] pc;
    logic [31:0] insn;
    uop_op_e     op;

    renamed_dst_t dst;

    logic is_branch;
    logic is_load;
    logic is_store;
    logic is_csr;
    logic serializing;

    exception_t exception;

    logic      fp_flags_valid;
    fp_flags_t fp_flags;

    logic        branch_resolved;
    logic        branch_mispredict;
    logic [31:0] branch_target;

    logic    lq_valid;
    lq_tag_t lq_tag;
    logic    sq_valid;
    sq_tag_t sq_tag;

    logic store_req_sent;
    logic store_rsp_done;
} rob_entry_t;
```

## 8.2 ROB 不應保存正式 result data

PRF 是執行結果的正式 speculative storage。

為了 differential testing 而將每筆 32-bit result 放入 ROB 會增加合成面積。建議：

* synthesis core 不包含 debug result array
* testbench monitor 監看 accepted writeback
* testbench 以 ROB tag 建立 shadow result table
* commit 時由 monitor 產生 architectural trace
* verification-only logic 使用條件編譯隔離

---

# 9. ROB Tag 與 Late Writeback 防護

這是架構正確性的必要項目。

branch flush 後，舊的 multiply、divide、FPU 或 memory request 仍可能完成。如果 ROB index 已被新指令重用，只有 index 不足以判斷 completion 是否有效。

ROB tag 必須包含 12-bit monotonic sequence number 與 entry index（參見 architecture_spec.md §15.2 與 uop_spec.md §4.2）：

```systemverilog
typedef struct packed {
    logic [ROB_SEQ_WIDTH-1:0] seq; // 12-bit sequence number
    logic [ROB_IDX_W-1:0]     idx; // 4-bit ROB index
} rob_tag_t;
```

每個 execution request 必須攜帶：

* ROB tag
* destination physical tag
* destination domain
* optional LSQ tag

writeback 前必須確認：

1. ROB entry 仍為 valid
2. entry tag 與 completion ROB tag 完全相同
3. entry 尚未完成
4. completion 未被 flush
5. destination physical tag 與 ROB 記錄一致

只有條件成立才能：

* 寫 PRF
* 更新 ready table
* 廣播 wakeup
* 設定 ROB completed

否則 completion 必須被丟棄。

這也避免 wrong-path completion 寫入已被重新配置的 physical register。

---

# 10. Issue Queue 與 Wakeup/Select

## 10.1 Integer Issue Queue Entry

```systemverilog
// Note: See uop_spec.md §17 for the normative definition of issue_entry_t
typedef struct packed {
    logic         valid;
    renamed_uop_t uop;
} issue_entry_t;
```

## 10.2 FP Issue Queue Entry

完整 FMA 需要三個 source operand，因此 FP issue entry 必須支援：

* src1
* src2
* src3
* 三組 ready bits
* 三組 physical tags

## 10.3 Select Policy

Baseline：

* oldest-ready-first
* 使用 ROB age comparison
* 每 cycle 最多選擇一條 integer/memory uop
* 每 cycle 最多選擇一條 FP uop
* cross-domain operand 發生 register-port conflict 時，由 arbiter 停止其中一條

ROB circular buffer 的 age comparison 必須使用 wrap-aware function，不能直接比較 index 大小。

## 10.4 Wakeup 時機

Baseline 採：

> 實際取得 PRF writeback port後，才廣播 destination ready。

不能在 FU 宣告完成但結果尚未取得 writeback port時先設 ready，否則 dependent instruction 可能讀到未更新的 PRF。

---

# 11. Physical Register File 與 Writeback

## 11.1 Baseline Port Configuration

### Integer PRF

* 3 read ports
  * 2 ports for two-source Integer IQ issue (ALU, branch, AGU)
  * 1 port dedicated exclusively to SQ integer store-data (`SB`/`SH`/`SW`) capture; never contested due to rename width 1
* 1 write port

### FP PRF

* 4 read ports
  * 3 ports for three-source FP IQ issue (FMA)
  * 1 port dedicated exclusively to SQ FP store-data (`FSW`) capture; never contested due to rename width 1
* 1 write port

## 11.2 Writeback Arbitration

每個 multi-cycle execution unit 必須具有 output holding register：

```text
FU completes
    ↓
output valid remains asserted
    ↓
wait for writeback grant
    ↓
PRF write accepted
    ↓
ROB completion accepted
    ↓
clear FU output
```

禁止 execution unit只產生單 cycle completion pulse，因為 writeback port可能正在被其他 unit 使用。

## 11.3 Same-domain Collision

可能同時完成：

* ALU result 與 integer conversion result
* load result 與 integer divider result
* FP add result 與 FLW result

每個 domain baseline 只有一個 write port，因此必須：

* 固定 arbitration priority或 round-robin
* 保留未取得 grant 的 completion
* 不丟失 result
* 不重複 writeback
* 避免 starvation

---

# 12. Execution Units

| Unit                    | 建議 latency |          Throughput | 備註                    |
| ----------------------- | ---------: | ------------------: | --------------------- |
| Integer ALU             |          1 |             1/cycle | add、logic、compare     |
| Branch                  |          1 |             1/cycle | 與 ALU cluster 共用      |
| Integer multiply        |        2–3 | 1/cycle 或固定 latency | 參數化                   |
| Integer divide          |      16–34 |       non-pipelined | iterative             |
| Load address generation |          1 |             1/cycle | 進入 LSU                |
| FP add/sub              |          4 |             1/cycle | 自行設計                  |
| FP multiply             |          4 |             1/cycle | 自行設計                  |
| FP FMA                  |        4–6 |             1/cycle | single rounding       |
| FP compare/misc         |        1–2 |             1/cycle | sign/min/max/class    |
| FP conversion           |        2–4 |             1/cycle | int↔FP                |
| FP divide               |  iterative |       non-pipelined | 固定或資料相關 latency       |
| FP sqrt                 |  iterative |       non-pipelined | 可與 divide 共用 datapath |

latency 是設計參數，不應散落在 control logic 中。

---

# 13. Floating-Point Architecture

## 13.1 FP Add/Sub Pipeline

```text
Stage 0:
    unpack
    classify
    detect NaN/Inf/zero/subnormal
    exponent comparison

Stage 1:
    significand alignment
    sticky-bit generation

Stage 2:
    add/subtract
    preliminary sign selection

Stage 3:
    normalization
    leading-zero detection

Stage 4:
    rounding
    exception generation
    packing
```

## 13.2 FP Multiply Pipeline

```text
unpack/classify
→ sign and exponent calculation
→ 24×24 significand multiplication
→ normalization
→ rounding
→ packing
```

## 13.3 FMA

FMA datapath必須保留乘積的完整中間 precision，與第三 operand 對齊後相加，最後只進行一次 rounding。

不能使用：

```text
rounded_multiply_result
→ FP adder
```

作為 compliant FMADD。

## 13.4 Rounding Mode

支援：

* RNE
* RTZ
* RDN
* RUP
* RMM
* dynamic rounding mode

若 instruction 使用 dynamic mode，實際 rounding mode 必須在 dispatch 前確定並放入 uop。

為避免 speculative CSR dependency，baseline 對 `frm`、`fflags`、`fcsr` 寫入採 serialization：

1. 停止新 FP dispatch
2. 等待較舊 FP instructions retirement
3. 提交 CSR operation
4. 後續 FP instruction才讀取新的 rounding mode

## 13.5 Floating-Point Flags

FPU completion 產生：

```text
NV: invalid operation
DZ: divide by zero
OF: overflow
UF: underflow
NX: inexact
```

flags 存入對應 ROB entry。

只有 instruction retirement 時才：

```text
architectural fflags = architectural fflags OR instruction flags
```

錯誤路徑 FP 指令不得修改 `fflags`。

---

# 14. Load/Store Queue

## 14.1 Load Queue Entry

至少保存：

* valid
* ROB tag
* effective address
* address valid
* size
* sign extension mode
* destination physical tag/domain
* request issued
* response received
* exception state

## 14.2 Store Queue Entry

至少保存：

* valid
* ROB tag
* effective address
* address valid
* store data
* data valid
* byte mask
* store size
* committed／memory issued state

## 14.3 Conservative Load Scheduling

load 只能在以下條件下執行：

1. 所有較舊 store 的 address 已知
2. 沒有較舊同地址 store 的 data 尚未 ready
3. 若有同地址且 data ready 的最近較舊 store，進行 forwarding
4. 若無衝突，才能向 memory 發出 request

Baseline 不允許 load speculative bypass unresolved older store。

## 14.4 Store Visibility

Store address/data 可亂序計算，但 memory write只能在：

* store 位於 ROB head
* store address valid
* store data valid
* 沒有 exception
* memory request ready

時發生。

ROB 只能在 store request 被 memory interface 接受後 retirement。

## 14.5 Memory Port Priority

當 ROB head 是 ready store 時：

* store commit request取得 data memory port優先權
* 暫停新的 load request
* 避免 committed store被 speculative load持續阻塞

## 14.6 Misalignment

Baseline 對 misaligned load/store產生 precise exception，不分割成多筆 memory request。

---

# 15. Branch Prediction 與 Recovery

## 15.1 Baseline Prediction

* conditional branch：not taken
* JAL：decode redirect
* JALR：execute resolution
* no BTB
* no BHT
* no RAS

## 15.2 Branch Misprediction Recovery

Recovery 流程：

```text
detect branch misprediction
→ block fetch/rename/dispatch
→ invalidate younger IQ entries
→ invalidate younger LSQ entries
→ reject younger pending completions
→ move ROB tail backward one entry per cycle
→ restore RAT using old physical mapping
→ return new physical mapping to free list (only when dst.valid == 1)
→ stop at mispredicted branch
→ redirect frontend
→ resume execution
```

## 15.3 Global Control State

建議定義明確 global state：

```text
CORE_RUN
BRANCH_ROLLBACK
TRAP_RECOVERY
MRET_RECOVERY
RESET_INITIALIZE
```

在 `BRANCH_ROLLBACK`：

* 不配置 ROB
* 不 dispatch
* 不 retirement
* older valid execution可完成
* younger completion被 tag check拒絕

## 15.4 延伸研究

比較：

* multi-cycle ROB rollback
* full RAT checkpoint per branch

分析：

* recovery latency
* storage area
* frequency
* branch-heavy workload IPC
* energy per retired instruction

---

# 16. Exception、Trap 與 CSR

## 16.1 Baseline Synchronous Exceptions

* illegal instruction
* instruction-address misaligned
* load-address misaligned
* store-address misaligned
* instruction access fault
* load access fault
* store access fault
* ECALL from M-mode
* EBREAK
* floating-point flags不是 trap，屬 accrued status

## 16.2 最低 CSR 集合

```text
mstatus
mtvec
mepc
mcause
mtval
mscratch
mcycle
mcycleh
minstret
minstreth
fcsr
frm
fflags
```

Zicsr 定義 CSR instruction操作；官方 specification提供獨立 CSR address space與 CSR instruction semantics。

## 16.3 Precise Trap

若 ROB head 發生 exception：

1. faulting instruction不 retirement
2. 所有 older instructions已 retirement
3. 所有 younger instructions flush
4. store不得對 memory產生錯誤 side effect
5. `mepc` 記錄 faulting PC
6. `mcause`、`mtval` 更新
7. RAT 恢復為 retirement map
8. PC redirect 至 `mtvec`

baseline 可以不支援 asynchronous interrupt，但文件中必須明確標記為未支援，不能宣稱完整 privileged architecture。

---

# 17. Bare-metal Simulation Platform

## 17.1 建議 Memory Map

```text
0x8000_0000 – 0x800F_FFFF    Program/Data RAM
0x1000_0000                  SIM_PUTC
0x1000_0004                  SIM_EXIT
0x1000_0008                  SIM_STATUS
0x1000_0100 – 0x1000_01FF    SIM_PERF_COUNTERS (MMIO research counters)
```

instruction port 與 data port可連到同一 testbench memory，但保持獨立 handshake。

## 17.2 ELF Loader

testbench負責：

* 解析 ELF loadable segments
* 載入 instruction/data memory
* 設定 reset PC
* 清除 BSS
* 監看 SIM_EXIT
* 產生 pass/fail status
* 產生 commit trace
* optional signature dump

## 17.3 ASIC Synthesis Boundary

PPA synthesis只包含：

```text
rv32_ooo_core
+ clock/reset wrapper
+ core memory interface pins
```

不包含：

* ELF loader
* simulation RAM
* MMIO console model
* reference model
* commit trace shadow storage
* assertion-only logic

---

# 18. Verification Strategy

## 18.1 Verification Pyramid

```text
Module unit tests
        ↓
Module assertions
        ↓
Integration directed tests
        ↓
RISC-V architectural tests
        ↓
Random differential testing
        ↓
Bare-metal application tests
        ↓
CoreMark and performance workloads
```

---

## 18.2 Unit Tests

必要 module tests：

* decoder
* immediate generator
* ALU
* multiplier
* divider
* FP unpack/classify
* FP aligner
* FP normalizer
* FP rounding unit
* FP add
* FP multiply
* FP FMA
* FP divide/sqrt
* RAT
* free list
* PRF ready table
* ROB
* issue queue
* age comparator
* writeback arbiter
* branch recovery controller
* load queue
* store queue
* forwarding comparator
* CSR file

---

## 18.3 Directed Microarchitecture Tests

### Rename hazards

* RAW
* WAR
* WAW
* repeated writes to same architectural register
* x0 destination
* free-list exhaustion
* ROB full with available IQ
* IQ full with available ROB
* retirement and allocation on same cycle

### Branch recovery

* branch followed by integer write
* branch followed by FP write
* branch followed by store
* branch followed by long integer divide
* branch followed by FP divide
* nested branches
* branch across ROB wraparound
* late wrong-path completion after ROB slot reuse

### LSU

* load after unrelated store
* load after same-address store
* multiple matching older stores
* older store address unresolved
* store data unresolved
* byte/halfword forwarding
* sign-extension tests
* wrong-path store
* store at ROB head while load request active

### FP

* every rounding mode
* positive/negative zero
* normal/subnormal boundary
* overflow
* underflow
* quiet/signaling NaN behavior
* infinity operations
* invalid operation
* divide by zero
* conversion saturation cases
* FMA cancellation
* flags on wrong path
* dynamic rounding mode serialization

---

## 18.4 Differential Testing

Spike 是官方 RISC-V ISA simulator，可作為 architectural reference model。

比較點應位於 retirement，不比較 cycle-by-cycle internal state。

每次 retirement比較：

```text
instruction order
PC
instruction bits
integer destination and value
FP destination and value
memory address
memory byte mask
memory write data
trap
cause
architectural fflags
```

對 FP result 必須 bit-exact 比較，不能使用浮點容差。

---

## 18.5 Formal Properties

### Rename／PRF

* physical register不可重複配置
* free-list entry不得同時存在於 RAT
* x0 mapping固定
* committed mapping不得指向 free register
* allocated destination ready初始為 0
* stale completion不得寫 PRF

### ROB

* ROB occupancy不得 overflow/underflow
* retirement順序單調
* incomplete ROB head不得 retirement
* invalid entry不得 retirement
* exception instruction不得 retirement
* flushed instruction不得 retirement

### Memory

* store不得在 retirement 前對外可見
* younger store不得越過 older store commit
* load forwarding必須選擇最近的 matching older store
* unresolved older store存在時 load不得 request memory

### Recovery

* flush 後所有 younger entries失效
* RAT rollback後 mapping正確
* rollback physical destination回到 free list
* older instruction保持有效
* ROB generation不同的 completion不得被接受

---

# 19. ASIC 設計流程

Verilator提供 SystemVerilog 到 C++／SystemC simulation model 的流程，適合建立高吞吐量測試平台。Yosys負責 RTL synthesis，OpenROAD提供 RTL-to-GDSII physical implementation infrastructure。

OpenLane 2 可建立以開源工具為基礎的 ASIC flow；但官方文件指出其 Classic default flow仍有 beta／silicon-validation 注意事項。因此本專案的 GDS 與 PPA 結果應定位為研究與開源流程結果，不宣稱等同商用 signoff。

## 19.1 流程

```text
SystemVerilog RTL
→ lint
→ elaboration
→ synthesis
→ technology mapping
→ pre-layout STA
→ floorplan
→ placement
→ clock-tree synthesis
→ routing
→ parasitic extraction
→ post-route STA
→ power estimation
→ DRC
→ LVS
→ GDSII
```

## 19.2 PDK 策略

### Nangate45

用途：

* 快速 synthesis sweep
* architecture parameter比較
* 減少完整 SKY130 physical flow的執行成本
* 早期 critical path辨識

OpenROAD官方測試與範例流程包含 Nangate45 design data，可用於快速研究。

### SKY130HD

用途：

* 最終 physical design baseline
* area與routing congestion分析
* post-route timing
* clock-tree overhead
* signoff-style report

## 19.3 固定比較條件

所有 PPA 實驗必須固定：

* tool版本與 commit
* PDK版本
* standard-cell library
* process corner
* voltage
* temperature
* clock uncertainty
* input/output delay
* synthesis effort
* floorplan aspect ratio
* target utilization
* placement density
* routing layer限制
* CTS設定
* benchmark binary
* compiler與 flags
* memory latency model

---

# 20. PPA 與效能指標

## 20.1 Architectural Metrics

* cycles
* retired instructions
* IPC
* cycles per instruction
* branch count
* misprediction count
* branch MPKI
* average recovery latency
* ROB occupancy
* ROB full cycles
* IQ occupancy
* IQ full cycles
* free-list empty cycles
* load blocked by unresolved store cycles
* store-forwarded load count
* FU utilization
* writeback-port conflict cycles
* FP divide busy cycles

## 20.2 Physical Metrics

* total standard-cell area
* combinational area
* sequential area
* buffer/inverter area
* clock-tree area
* cell count
* total wire length
* WNS
* TNS
* maximum closed frequency
* routing congestion
* DRC count
* LVS status
* estimated dynamic power
* estimated leakage power
* energy per retired instruction

## 20.3 Power Methodology

優先採用：

1. 使用相同 benchmark window產生 switching activity
2. 將活動資訊套用到相同 post-route netlist
3. 使用相同 PVT corner
4. 排除 reset、ELF loading 與初始化區段
5. 報告 activity-annotated power

若工具流程只能進行 vectorless estimation，報告必須明確標示：

> Vectorless estimated power，不可與 activity-annotated power直接混用。

---

# 21. Design-Space Exploration

不執行完整笛卡兒積，採單變量與少量組合實驗。

| Experiment              | Configurations                    |
| ----------------------- | --------------------------------- |
| ROB depth               | 8、16、32                           |
| Integer IQ              | 4、8、12                            |
| FP IQ                   | 2、4、8                             |
| Integer PRF             | 40、48、64                          |
| FP PRF                  | 40、48、64                          |
| LQ/SQ                   | 2/2、4/4、8/8                       |
| FP add latency          | 3、4、5                             |
| FP multiply latency     | 3、4、5                             |
| MUL implementation      | iterative、pipelined               |
| Recovery                | rollback、checkpoint               |
| Branch predictor        | static、BHT、BTB+BHT                |
| FP PRF operand strategy | 3 read ports、staged third operand |
| Writeback ports         | single、dual experimental          |

每個實驗至少輸出：

```text
configuration
RTL commit hash
toolchain lock version
benchmark hash
compiler flags
cycle count
IPC
area
Fmax
power estimate
energy/instruction
critical-path category
```

---

# 22. 專案執行流程表

| Stage                     | 主要輸入                 | 核心工作                               | 驗證要求                           | Exit Criteria                    | 主要交付物                |
| ------------------------- | -------------------- | ---------------------------------- | ------------------------------ | -------------------------------- | -------------------- |
| G0 規格凍結                   | ISA、目標與限制            | 固定 ISA、pipeline、queue、interface    | 設計審查                           | 無未決 architectural ambiguity      | architecture_spec.md |
| G1 工具鏈凍結                  | 開源工具                 | 建立 container/lockfile/CI           | hello-world RTL與小模組 GDS        | 所有人可重現                           | toolchain.lock       |
| G2 Simulation Platform    | memory map、ELF       | loader、RAM、MMIO、trace              | bare-metal smoke test          | ELF 可正確執行與退出                     | simulator            |
| G3 RV32I Sequential Model | decoder、ALU          | 建立簡單可比較核心或 backend bypass mode     | directed RV32I                 | 基本 ISA pass                      | reference RTL path   |
| G4 ROB Retirement         | uop、ROB spec         | allocation、completion、retirement   | ROB wrap、stall、exception tests | in-order retirement穩定            | rob.sv               |
| G5 Integer Rename         | RAT、PRF、free list    | RAW/WAR/WAW消除                      | formal invariants              | random rename stress pass        | rename subsystem     |
| G6 Integer OoO            | IQ、wakeup/select     | OoO issue、writeback arbitration    | dependency random tests        | Spike diff穩定                     | integer backend      |
| G7 Branch Recovery        | predictor、rollback   | flush、late completion rejection    | nested branch、wraparound       | wrong-path不可 retirement          | branch recovery      |
| G8 LSU                    | LQ/SQ、memory port    | conservative scheduling、forwarding | memory alias tests             | store side effects precise       | LSU                  |
| G9 M Extension            | MUL/DIV              | 自研 multiplier/divider              | corner與random tests            | M ACT tests pass                 | RV32IM candidate     |
| G10 CSR/Trap              | CSR spec             | precise trap、M-mode subset         | directed trap tests            | exception state precise          | CSR/trap subsystem   |
| G11 FP Rename             | FP RAT/PRF           | separate FP domain                 | cross-domain tests             | FP rename invariants pass        | FP backend shell     |
| G12 Basic FP              | add/mul/misc         | pipeline與rounding                  | bit-exact unit tests           | selected FP tests pass           | basic FPU            |
| G13 Complete FP           | FMA/div/sqrt/convert | 完整 F semantics                     | edge-case與random diff          | full F tests pass                | RV32IMF candidate    |
| G14 Architecture Signoff  | complete RTL         | ACT4、Spike、formal、CoreMark         | full regression                | zero known architectural failure | signoff report       |
| G15 Synthesis Signoff     | RTL與constraints      | Yosys、STA                          | structural checks              | zero latch、timing報告有效            | synthesis reports    |
| G16 Physical Signoff      | netlist、PDK          | floorplan至GDS                      | DRC/LVS/STA                    | flow完成且結果可重現                     | GDS與reports          |
| G17 DSE                   | parameter matrix     | IPC/PPA sweep                      | fixed methodology              | 結果完整且可比較                         | experiment dataset   |
| G18 Portfolio Release     | 全部成果                 | 文件、圖表、demo                         | clean-clone reproduction       | 第三者可重現                           | public repository    |

Stage 必須依 exit criteria 通過，不得只以「RTL 已寫完」視為完成。

---

# 23. 架構簽核清單

## 23.1 Rename Signoff

* [ ] x0 不配置 physical register
* [ ] f0 為一般 register
* [ ] new destination不重複配置
* [ ] old destination只在 retirement回收
* [ ] branch rollback不遺失 register
* [ ] trap recovery恢復 retirement map
* [ ] free list無 duplicate
* [ ] stale completion不寫入已重用 physical register

## 23.2 ROB Signoff

* [ ] wraparound正確
* [ ] tag包含 generation
* [ ] incomplete entry不 retirement
* [ ] exception entry不 retirement
* [ ] store commit ordering正確
* [ ] FP flags僅 retirement更新
* [ ] wrong-path instruction不可 retirement

## 23.3 IQ／Writeback Signoff

* [ ] source ready初始化正確
* [ ] wakeup不遺失
* [ ] simultaneous completion不丟失
* [ ] holding register支援 backpressure
* [ ] writeback collision arbitration正確
* [ ] ROB age comparison支援 wraparound
* [ ] flush後 IQ entry失效

## 23.4 LSU Signoff

* [ ] unresolved older store阻擋 load
* [ ] forwarding選擇最近 older store
* [ ] byte mask正確
* [ ] misaligned request不送至 memory
* [ ] wrong-path store無 external side effect
* [ ] store retirement等待 memory accept
* [ ] late load response受 ROB tag檢查

## 23.5 FPU Signoff

* [ ] 所有 rounding modes
* [ ] subnormal input/output
* [ ] signed zero
* [ ] infinity
* [ ] qNaN/sNaN
* [ ] invalid
* [ ] divide-by-zero
* [ ] overflow
* [ ] underflow
* [ ] inexact
* [ ] FMA single rounding
* [ ] wrong-path fflags被丟棄

---

# 24. 風險登錄表

| 風險                           | 等級 | 影響                     | 控制方式                                    |
| ---------------------------- | -- | ---------------------- | --------------------------------------- |
| 完整 FPU 語意錯誤                  | 極高 | 無法宣稱 RV32F             | 將 classify、normalize、rounding獨立驗證       |
| branch flush後 late writeback | 極高 | silent data corruption | ROB generation tag與writeback validation |
| LSQ ordering錯誤               | 極高 | memory state錯誤         | 保守 scheduling、directed/formal tests     |
| FMA 非 fused                  | 高  | ISA 不合規                | 保留完整乘積 precision並 single rounding       |
| CSR／FP rounding dependency   | 高  | dynamic rounding錯誤     | CSR serialization                       |
| 多埠 PRF 面積過高                  | 高  | PPA 不佳                 | baseline與 staged operand版本比較            |
| standard-cell RAM 結果失真       | 高  | area不代表 SRAM CPU       | 明確拆分 storage面積並揭露限制                     |
| CoreMark RTL simulation過慢    | 中高 | 無法完成長時間 run            | regression與report run分離                 |
| 開源 flow版本變動                  | 中高 | 結果不可重現                 | container與 commit lock                  |
| 直接追求 GDS延誤功能驗證               | 高  | 架構錯誤晚期發現               | 每個 module提早 synthesis，但功能 gate優先        |
| 功能持續擴張                       | 高  | 無法收斂                   | 依非目標清單拒絕 scope creep                    |

---

# 25. Definition of Done

## 25.1 Functional Signoff

* RV32I、M、F、Zicsr所有宣稱指令可執行
* architectural tests通過
* Spike differential regression通過
* CoreMark correctness validation通過
* 所有已知 directed corner tests通過

## 25.2 Microarchitecture Signoff

* rename invariants通過
* ROB wraparound通過
* branch recovery通過
* late completion tests通過
* LSQ ordering tests通過
* precise exception tests通過
* no known wrong-path side effect

## 25.3 Physical Signoff

* synthesis成功
* 無 unintended latch
* post-route STA report完整
* DRC/LVS結果保存
* clock與constraint清楚
* PPA可由 clean checkout重現

## 25.4 Research Signoff

* 至少完成三組 architecture experiments
* 每組固定工具與 constraint
* IPC、area、frequency與power指標完整
* 結果包含原因分析，不只列數值
* 明確揭露 open-source flow與memory implementation限制

## 25.5 Portfolio Signoff

* 完整 architecture diagram
* rename與recovery時序圖
* LSU ordering示意圖
* FP pipeline圖
* verification matrix
* ACT4 report
* CoreMark report
* synthesis與physical reports
* design-space plots
* reproducible commands
* known limitations

---

# Appendix A — CoreMark 首要測試計畫

## A.1 目的

CoreMark作為以下項目的首要 application-level acceptance test：

* bare-metal toolchain
* C ABI
* integer pipeline
* branch behavior
* load/store behavior
* multiplication support
* OoO scheduling correctness
* performance counter
* long-running differential stability

CoreMark不作為：

* FPU correctness benchmark
* floating-point performance benchmark
* external memory bandwidth benchmark
* cache hierarchy benchmark

---

## A.2 Prerequisites

CoreMark前必須完成：

* RV32IM
* basic Zicsr
* `mcycle/mcycleh`
* bare-metal startup
* stack
* linker script
* initialized data copying
* BSS clearing
* minimal printf/MMIO
* program exit
* stable long-run simulation

建議編譯：

```text
-march=rv32im_zicsr
-mabi=ilp32
-O2
```

另建立：

```text
-O0
-O2
-O3
```

三組結果，以區分 compiler與hardware效果。

不得在不同 configuration使用不同 compiler flags進行 PPA對比。

---

## A.3 Porting Layer

只修改官方允許的：

```text
core_portme.c
core_portme.h
core_portme.mak
```

官方 run rules禁止修改其他 benchmark source，要求固定 datatype width、兩組 validation seeds、2000-byte buffer，並要求正式結果的 benchmark duration至少十秒。

CoreMark timer：

```text
barebones_clock() → read mcycle/mcycleh
EE_TICKS_PER_SEC → declared simulation clock frequency
```

RV32 讀取 64-bit `mcycle` 時應使用 high-low-high sequence，避免低 32-bit overflow造成不一致。

---

## A.4 執行模式

### Smoke Mode

用途：

* CI
* 快速 regression
* 非正式 score

特性：

* 少量 iterations
* 執行 validation
* 不宣稱符合官方 run rules

### Analysis Mode

用途：

* architecture experiment
* cycles/iteration
* instructions/iteration
* branch與stall statistics

結果標示：

> Internal research result，不是 EEMBC-certified result。

### Reporting-Compatible Mode

要求：

* 執行時間至少 10 秒的 target time
* 所有 validation成功
* 兩組官方 seeds成功
* buffer size 2000 bytes
* source未非法修改
* compiler與flags完整揭露
* memory configuration揭露

如果因 RTL simulation成本沒有滿足十秒規則，不得將結果描述成官方 compliant CoreMark score。

---

## A.5 計算指標

```text
Iterations per cycle =
    total iterations / measured core cycles

CoreMark/MHz equivalent =
    total iterations × 1,000,000 / measured core cycles

Instructions per iteration =
    retired instructions / total iterations

Cycles per iteration =
    measured core cycles / total iterations
```

CoreMark/MHz比較仍必須固定：

* compiler
* optimization flags
* memory latency
* benchmark version
* code/data placement

---

## A.6 必須收集的計數器

```text
mcycle
minstret
branch count
misprediction count
ROB full cycles
IQ full cycles
load blocked cycles
store forwarding count
multiply utilization
writeback conflict cycles
```

## A.7 CoreMark Pass Criteria

* [ ] performance seed validation成功
* [ ] validation seed validation成功
* [ ] CRC全部正確
* [ ] 無 illegal instruction
* [ ] 無 unexpected trap
* [ ] SIM_EXIT status成功
* [ ] Spike與RTL final architectural state一致
* [ ] cycle counter無 overflow錯誤
* [ ] 結果包含 compiler版本與flags
* [ ] 結果註明是否滿足官方十秒規則

---

# Appendix B — RISC-V ISA／Architectural Tests 首要測試計畫

## B.1 Framework

使用官方：

```text
riscv-non-isa/riscv-arch-test
ACT4 Framework
```

不再以 RISCOF作為新專案主要流程，因官方 ACT4已取代舊 RISCOF workflow。

所有 repository、test suite與 ISA specification均 pin至：

* release tag
* commit hash
* test date

---

## B.2 Test Order

```text
RV32I
→ M
→ Zicsr
→ F load/store
→ F miscellaneous
→ F add/multiply
→ F conversion
→ F FMA
→ F divide/sqrt
→ complete declared ISA set
```

禁止在 RV32I尚未穩定時直接執行完整 RV32IMF regression。

---

## B.3 DUT Adapter

ACT4會產生 ELF。DUT adapter負責：

1. 接收 ELF路徑
2. 載入 testbench memory
3. 設定 reset PC
4. 執行至 pass/fail或 timeout
5. dump signature region
6. 回傳 ACT4所需結果
7. 保存 commit trace
8. 保存 failure instruction附近 trace window

---

## B.4 Timeout Policy

timeout不能只使用固定 wall-clock time。

應使用：

```text
maximum cycle count
maximum retired instruction count
no-retirement watchdog
```

其中 no-retirement watchdog用於偵測：

* deadlock
* LSU stall
* lost writeback
* ROB head永久 incomplete
* recovery state無法退出

---

## B.5 Failure Artifact

每個失敗 test自動保存：

```text
test name
ELF
disassembly
ISA string
tool versions
seed
last N commit records
ROB state
RAT state
free-list state
IQ state
LSQ state
pending FU completions
exception state
signature diff
```

避免只保留「PASS/FAIL」。

---

## B.6 Pass Criteria

* [ ] 所有宣稱 ISA extension的對應 tests通過
* [ ] 沒有以 testbench特殊處理繞過 DUT
* [ ] unsupported extension沒有被錯誤宣稱
* [ ] 每次測試由 clean reset開始
* [ ] signature正確
* [ ] timeout為零
* [ ] report保存版本與commit hash
* [ ] 失敗可由單一 command重現

---

## B.7 限制聲明

Architectural tests是 ISA certification／compliance檢查，不是完整的 OoO correctness證明。

即使全部通過，以下錯誤仍可能存在：

* rare branch recovery corruption
* ROB slot reuse race
* late writeback corruption
* free-list duplicate
* memory ordering race
* simultaneous completion arbitration錯誤
* wrong-path FP flags
* queue wraparound錯誤

因此 ACT4 pass只能作為 architecture signoff的一部分，不能取代 differential、formal和random testing。

---

# Appendix C — 建議 Repository 結構

```text
rv32-ooo/
├── docs/
│   ├── architecture_spec.md
│   ├── isa_support_matrix.md
│   ├── uop_spec.md
│   ├── rename_spec.md
│   ├── rob_spec.md
│   ├── branch_recovery.md
│   ├── memory_ordering.md
│   ├── fp_spec.md
│   ├── verification_plan.md
│   └── ppa_methodology.md
├── rtl/
│   ├── frontend/
│   ├── decode/
│   ├── rename/
│   ├── backend/
│   ├── execute/
│   ├── memory/
│   ├── csr/
│   ├── common/
│   └── top/
├── tb/
│   ├── verilator/
│   ├── unit/
│   ├── integration/
│   ├── assertions/
│   ├── formal/
│   └── reference/
├── software/
│   ├── crt0/
│   ├── linker/
│   ├── directed/
│   ├── coremark/
│   └── fp_tests/
├── tests/
│   ├── act4/
│   ├── random/
│   ├── regression/
│   └── expected/
├── scripts/
│   ├── build.py
│   ├── run_test.py
│   ├── run_regression.py
│   ├── compare_trace.py
│   ├── run_coremark.py
│   ├── run_act4.py
│   ├── run_synthesis.py
│   ├── run_physical.py
│   └── collect_metrics.py
├── synthesis/
├── physical/
│   ├── nangate45/
│   └── sky130hd/
├── experiments/
├── reports/
├── containers/
├── Makefile
└── toolchain.lock
```
