版本：0.2.2（2026-10-30）
状态：已审查旧基线远程日志；不覆盖本地新RTL。
负责系统：CARD / READER 物理验证。
依赖：GitHub日志、完整签核artifact及准确时序约束。
验证标准：每项证据关联源码SHA、流程阶段及原始job。
已知风险：时序数值未获取、fallback SDC、lint告警；没有新版本签核或官方提交。

# 物理基线日志审查
CARD feaa55682afc13b8ef6917de1e913a06ffae8ec0：GDS run40415324245/job121896091478。
READER 2e3a9cfb41424848e4da2e448f9378eef273d1d8：run40415359644/job121896207129。
原始job链接形式 https://github.com/derrykervin/<仓库>/actions/runs/<run>/job/<job> 。机器可读时间戳摘录在deliverables/<仓库>-physical-baseline-evidence.json。

| 指标 | CARD | READER | 范围 |
|---|---:|---:|---|
|最终详细布线违例|0|0|DRT-0199末次结果|
|最终天线net/pin违例|0/0|0/0|ANT-0002/0001|
|Antenna/LVS/DRC流程汇总|Passed|Passed|ReportManufacturability|
|独立Precheck|passed|passed|job121899175046/121898651350|
|全局布局阶段utilization|69.542%|60.731%|不是最终面积/可用余量|
|全局布局placed cell area|25027.3691|20132.6850|日志阶段值，不是最终routed面积|
|lint告警数|5|3|未逐项豁免|

Flow明确Checker.KLayoutDRC=False，并警告klayout__drc_error__count缺失。这里的DRC通过不能解释为构建内所有DRC工具都执行；独立Precheck通过是另一份证据，不能混淆。中途routing/hold/antenna违例是迭代过程，不能直接当最终失败。
两端PNR_SDC_FILE及SIGNOFF_SDC_FILE未定义，使用generic fallback SDC；必须提取实际create_clock周期、I/O delay、uncertainty、时钟/复位例外及未约束路径，不能仅依据info.yaml中的40MHz推断约束完整。需要下载55-openroad-stapostpnr所有corner的setup/hold/WNS/TNS、SPEF、metrics与最终SDC。

优先补证：1. 用当前修改重新跑功能/联合/GL及物理流程；2. 审查SDC覆盖及最差corner数值；3. 定位5/3条lint和2条floating net；4. 关联GDS/OAS SHA256和官方Revision。现有日志只证明原型基线的相应流程检查，不证明产品认证、八触点或封装可行。
