版本：0.2.3（2026-10-30）
状态：基线日志审查；建议处置，非已批准豁免。
负责系统：CARD/READER RTL验证。
依赖：对应SHA源码、lint job日志及待执行HDL/综合回归。
验证标准：每条告警有代码含义、决策及测试依据；不使用全局关闭lint制造绿色。
已知风险：以下处置尚未获得仿真/等价检查确认；当前修改无物理签核。

# CARD基线 feaa5568
- BLKSEQ card_cpu.v:89/96：ALU临时变量alu_tmp在时钟过程先阻塞计算再用于非阻塞寄存器更新。不能机械替换为<=，否则读到上一周期计算。建议将算术结果改为独立组合wire后做CPU指令/标志回归或保留局部有理由豁免；本轮不修改。
- UNUSEDSIGNAL card_cpu.v:42 flag_c：更新但没有指令读取。规格应明确进位标志当前软件不可见；是否移除或新增条件指令需架构决策，不能为减告警随意改变ISA。
- UNUSEDSIGNAL spi_master.v:19 rx_shift[0]：最终接收拼接路径需确认移位前后采样行为和8bit读回；已有SPI测试在工具恢复后验证，不能直接删除最后一位数据。
- UNUSEDSIGNAL uart_tx.v:13 shift_reg[0]：串行移位输出路径可能使存储最低位不再使用，须核对波形/综合结果后局部说明。

# READER基线 2e3a9cfb
- WIDTHEXPAND firm_reader_01.v:99 tx_index-1：4bit索引与无尺寸整数运算发生扩展。建议显式32位零扩展后计算挑战字节索引，并验证tx_index=1..8的全部字节、边界0分支与非法值保护；未修改。
- UNUSEDSIGNAL uart_tx.v:13 shift_reg[0]：同CARD路径审查。
- CASEINCOMPLETE firm_reader_01.v:76 phase：2位phase只定义VERSION/IDENTIFY/AUTH，未处理3。建议在最高优先级状态保护层对非法phase fail closed、清auth_pass并终止TX；不能仅在接收case内加default，因为后续主FSM非阻塞赋值可能覆盖它。需要非法phase注入、超时、拔卡恢复与联合回归后验证。

这些告警没有被批准豁免，也没有被关闭。下一次开发优先处理非法phase恢复和显式索引，并先取得HDL执行能力。CARD ALU修改必须有独立CPU指令测试，不能仅以lint减少宣称正确。

# Artifact访问结果
两端GDS_logs、tt_submission、gatelevel_test_results、precheck_reports均未过期，清单保存在deliverables/*-artifact-inventory.json。CARD GDS_logs约40.9MB，READER约38.3MB；tt_submission分别约3.21MB/2.79MB。
GitHub下载工具已成功物化CARD tt_submission和GDS_logs文件引用，但工作区代理仍无法联网，当前没有把ZIP字节下载到执行器或解析。不得声称已提取其中SDC、metrics、SPEF、WNS/TNS、GDS SHA256。文件服务引用不是Sediment上传ID，不应错误传给Sediment download_file。
后续在可用网络环境通过GitHub下载日志产物，验证artifact digest，然后提取55-openroad-stapostpnr、最终SDC及各corner数值。独立Precheck通过不能替代时序约束覆盖审查。

2026-10-31本地状态更新：READER已准备显式32位挑战索引和最高优先级内部故障保护，连同故障注入台进入工作分支；未运行Verilator/HDL，以上2条告警尚不可标解决。旧基线摘要保持原样。
