# FIRM_CARD_01 TinyTapeout 工程准备结果

日期：2026-10-11。实际工程：WSL Ubuntu `/home/derrykervin/FIRM_CARD_01_ASIC`。

## 输入与文件

此会话未直接挂载历史 `/mnt/data` 上传目录。使用本机前次输出保存的同名 ZIP：
`C:/Users/DERRYKERVIN/Documents/Codex/2026-10-10/referenced-chatgpt-conversation-this-is-an-3/outputs/FIRM_CARD_01_TAPEOUT.zip`。
SHA256：`283f8bf10a3093fbefb7492e906622e25ab50c5a3a15ab91924fe617e190d27b`。
解压至目标工程 `work/original/FIRM_CARD_01_TAPEOUT/`，源码定位到其 `src/`。

复制 `card.v`、`card_cpu.v`、`program_rom.v`、`uart_tx.v`、`uart_rx.v`、`spi_master.v` 到工程 `src/`。六个文件逐字节及 SHA256 对比全部一致，未修改 Card 核心。
新增 `src/project.v` 和 `info.yaml`；另外复制原有两份测试，新增顶层 smoke test、检查脚本和报告。

配置：title=FIRM_CARD_01，author=Derry，language=Verilog，clock_hz=10000000，tiles=1x1，top_module=tt_um_derrykervin_firm_card_01；source_files 列出全部七个 Verilog 文件，24 个 pinout 字段齐全。

## 顶层映射

| TinyTapeout 信号 | Card 信号 / 行为 |
|---|---|
| clk / rst_n | clk / reset_n，低有效复位 |
| ui_in[0] | uart_rx |
| uo_out[0] | uart_tx |
| uo_out[1] | spi_sclk |
| uo_out[2] | spi_mosi |
| uo_out[3] | spi_cs_n |
| uo_out[4] | halted |
| uo_out[7:5] | debug_pc[2:0] |
| ui_in[7:1] / uio_in | 未使用 |
| uio_out / uio_oe | 均固定 0，双向脚始终为输入 |
| Card gpio_in / spi_miso | 固定为 0 |
| ena | 未使用，符合官方模板允许忽略的接口说明 |

Card GPIO 输出、其余 PC 位、debug_r0 未引出。全部外部输出和 Card 输入均明确连接。

## 检查结果

- 模块声明 grep 和目录检查通过，src 中正好七个 Verilog 文件。
- Icarus Verilog `-Wall -g2001` 顶层编译通过，无日志警告。
- 本地 TinyTapeout `tt_tool.py --print-top-module` 成功加载配置并输出预期顶层名。
- Yosys 0.52 完成顶层通用综合，`check -assert` 为 0 problems，无锁存器断言通过。
- 综合统计：2970 cells（包括 6 个 scopeinfo 元数据项），375 个触发器，无 memory。此结果经过通用 ABC 优化及常量输入优化，不能直接当作标准单元面积或与原包不同综合流程的统计直接比较。
- 原包 UART 仿真 CPB=8、16、434 全部 PASS，覆盖 VERSION、ID、AUTH、重复/未知命令及部分接收/复位。
- 原包 MMIO 测试 PASS，覆盖 endian、readonly、DONE、CLEAR、GPIO、Timer、SPI。
- 新增顶层测试 PASS：复位、10000 周期输出无 X、双向脚不驱动。未进行顶层外部 UART 的完整协议回归；上述协议测试使用原有 Card testbench。

## 报错、警告与限制

- precheck 首次连帮助命令也因 `PDK_ROOT environment variable not set` 退出 1；设置为 `/home/derrykervin/ttsetup/pdk` 并指定 sky130A 后，帮助命令退出 0。
- 这仅确认 precheck 能启动。实际物理 precheck 要求 GDS，当前尚无 GDS，因此未执行 DRC/LVS 等物理签核，不能宣称 precheck 通过。
- Yosys 唯一警告：`Replacing memory \regs with list of registers. See src/card_cpu.v:69`，来自原核心寄存器堆展开，不是新增错误。
- 环境探测时将 pip 列表截断显示曾产生无关的 broken pipe 提示；不影响任何工程检查。
- `1x1` 按要求保留为初始值，尚未证明能容纳设计或满足 10 MHz 时序。
- UART 保留默认分频 434，因此 10 MHz 时约 23041.47 baud，而非 115200。

## 下一步

1. 确认目标 shuttle/PDK，采用对应官方完整模板补充工作流及项目说明。
2. 运行目标工艺标准单元映射和布局布线，评估 1x1 面积及 10 MHz 时序，必要时调整 tiles。
3. 与外部串口设备确认波特率；若希望 115200，可另行在 wrapper 参数实例化中评估分频 87，核心源码无需改动。
4. 生成 GDS/LEF/门级网表后运行正式 precheck、DRC/LVS 和时序检查。

复现基础检查：在 WSL 执行 `bash ~/FIRM_CARD_01_ASIC/tools/check.sh`。脚本使用此次确认的本机工具位置。
所有当前日志保存在 `reports/`。交付 ZIP 包含源码、配置、测试、脚本及报告，不包含历史构建产物和原始解压树。

官方参考：https://github.com/TinyTapeout/ttihp-verilog-template/blob/main/src/project.v
配置参考：https://github.com/TinyTapeout/ttihp-verilog-template/blob/main/info.yaml
