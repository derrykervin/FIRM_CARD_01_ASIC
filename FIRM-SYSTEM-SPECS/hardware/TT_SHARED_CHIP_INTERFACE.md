版本：0.2.4（2026-10-31）
状态：官方锁定版本逻辑/引脚资料已核实；载板/机械未验证。
负责系统：FPC、CARD、READER、载板管理。
依赖：官方SKY26d HEAD5b12186dac87496dfeaabcf9d9aa2460b399c58a；其tt-multiplexer子模块8fbe6cd3ebc3808a4cb3d589d1a2728c46a7054c。
验证标准：载板网表逐引脚对照官方表，制造前取得实际交付封装与电气规格。
已知风险：管理时序、最终项目选择地址、供电电压/顺序、机械尺寸与厚度未冻结。

# 官方共享芯片接口约束
来源：https://github.com/TinyTapeout/tt-multiplexer/blob/8fbe6cd3ebc3808a4cb3d589d1a2728c46a7054c/docs/INFO.md
顶层RTL：https://github.com/TinyTapeout/tt-multiplexer/blob/8fbe6cd3ebc3808a4cb3d589d1a2728c46a7054c/rtl/tt_top.v
官方文档blob be55ef2488f0cf1fba6b69ba33b8333340e8c233。官方项目通过.gitmodules指向此mux，不能拿其它工艺的QFN表直接套用。

| SKY130 Open Frame QFN64脚 | 信号 | 当前FIRM用途/限制 |
|---|---|---|
|22|ctrl_ena|共享设计使能；必须定义上电安全值|
|24|ctrl_sel_inc|项目地址计数脉冲；不能随意悬空|
|25|ctrl_sel_rst_n|项目地址计数复位；不同于用户复位|
|50|u_clk|用户ASIC时钟|
|51|u_rst_n|用户项目复位|
|31|ui[0]|CARD或READER UART RX|
|32|ui[1]|CARD本地MISO补丁/READER检测输入；两颗用途不同|
|62|uo[0]|UART TX|
|17、64|VDD IO|电压/去耦以最终电气图为准|
|18、49、63|VDD Core|不能假设和IO同电压直接短接|
|9、30、40、47|VDD Analog|最终资料规定接法；不能自行省略|
|EPAD及其它GND脚|GND|按官方封装/载板网表完整连接|

此为官方Open Frame表，不是已收到封装的BOM或引脚签发图；QFN64名称不提供本体尺寸、高度、焊盘或装配厚度。resetb脚21在文档标为/，不得凭名称当作u_rst_n或擅自给定接法。

## 上电项目选择目标流程
载板保持用户复位低、ctrl_ena禁用；电源/时钟稳定后复位选择计数器，再向ctrl_sel_inc输入与最终官方项目地址相同的N个脉冲，最后使能目标并释放用户复位。此流程来自mux操作说明的逻辑要求，脉宽/顺序/上电电平需要电气规格和实测确认。
项目6057是平台项目ID，不是选择计数N；不得发送6057个脉冲。最终mux地址必须取对应交付Revision的分配文件。不能用固定电平假设可选择任意非零项目。

## 八触点结论
此前电源/GND/UART2/eMMC3/时钟1已占8触点，用户复位、管理3信号、机械检测及可能的多电压域没有余量。要保留STARCORE八触点，必须在卡内承担项目选择、POR/复位、必要稳压/转换，并使用独立机械检测；这些附加器件及走线必须纳入厚度/面积/启动功耗评估。若无法实现，必须调整接触接口或封装方案，而不是删去管理/复位条件。
SPI安全器件留在卡内；eMMC走独立host链路。没有FPC布线、BOM、信号完整性或样卡证据前，不能声称八触点已可生产。2.20mm仍是目标。
