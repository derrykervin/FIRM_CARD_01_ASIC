版本：0.3.0（2026-10-31）
状态：实际补充RTL仿真完成；不属于官方CI/物理签核。
负责系统：CARD、READER、实验协议接收器。
依赖：锁定CVC源码1c5e043ec33ef6f1fdbf38565501c944893a83cf、本地GCC/Make。
验证标准：明确PASS行、无$fatal诊断、零error汇总；不能只用退出码。
已知风险：Icarus/官方CI未运行；综合、STA、GDS、GL、安全器件互通未验证。

# CVC补充RTL结果
从cambridgehackers/open-src-cvc读取73个构建所需文件，逐一核验Git blob SHA，保留许可证；不修改工具源码，make -C src -j4 cvc64成功。本地使用许可证所允许的仿真用途，未将工具源码/二进制加入ASIC补丁或商业分发包。
命令：`python3 -B tools/run_cvc_regression.py --cvc /workspace/toolchain/cvc-source/build64/cvc64 --reader ../FIRM_READER_01_ASIC --output /workspace/deliverables/cvc-regression`。
运行模式+interp；仅在生成测试台副本中覆盖CPB/VECTOR/ALT_ID参数，源码及测试副本SHA256已记录。

40个正向场景通过：
- CARD UART完整协议CPB8/16/347/434：4；CARD RX故障同4参数：4。
- MMIO、wrapper、MISO高低高、pending同沿读接收：4。
- READER RX故障及内部状态注入CPB8/16/347：6。
- 3种CPB×3挑战×2参数身份的联合收发/拔卡/重插/中途移除恢复：18。
- 联合版本错/响应错/无响应/截断/恢复CPB8/16/347：3。
- 实验性v2接收器生成向量、CRC/超时/清除：1。
另1个$fatal冒烟负控制被正确识别，共41个runner检查通过。

## 反向控制
用旧基线相应源码运行新增测试：旧UART接受坏停止位、旧pending同沿丢失、旧wrapper MISO常零、旧Reader非法phase残留成功，均触发预期$fatal且无PASS。日志在deliverables/cvc-negative-logs/，汇总cvc-negative-controls.json。说明测试能区分已定位缺陷，而不只是打印PASS。
CVC的$fatal退出码实测为0！运行器明确拒绝$fatal诊断，即使code=0或此前有PASS；新增5项运行器判定反向测试。完整Python参考/工具测试39项通过。

## 证据与边界
机器结果/每场日志和源码哈希：deliverables/cvc-regression/results.json及各子目录simulation.log。
工具版本、源码和二进制哈希：deliverables/cvc-toolchain-manifest.json。
以上验证了当前测试范围内RTL行为，不是覆盖率数值报告、形式证明或全产品验收；单元pending测试使用缓冲边界force，internal故障测试使用故障注入，联合通信使用实际UART线。
本地MISO、UART停止位/BREAK、pending优先级、Reader内部故障修复取得CVC补充仿真证据；仍需Icarus/官方CI、综合/40MHz时序、GDS/Precheck/GL重新签核。实验RX依旧不接流片顶层，2048bit双缓冲没有面积结论。固定ID与XOR/Rotate仍非产品安全认证，测试身份参数变化不等于制造个性化。
无新增FPGA实测、GitHub PR、平台Revision或SUBMITTED证据。C0稳定源码未改。
