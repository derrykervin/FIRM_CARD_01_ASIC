版本：0.2.0（2026-10-30）
状态：设计目标 / 审计记录；除明确证据外未实现、未仿真、未物理验证。
负责系统：CARD / READER / FPC / Server。
依赖：锁定源码 SHA、外部安全器件选型、平台权限。
验证标准：下述验收条款逐项提供可复现证据。
已知风险：旧版认证不安全；平台未提交；封装未确认。

# 接续开发记录

## 2026-11-13 十三命令与配置/公钥精确比较接入完整CARD实验：2150FF/92003.2384µm²，正式封装/注册身份/物理签核仍未完成

独立engineering/2026-11-13-personalized-session，base400d8e08d8514004e1d576df3d3b6e8f351f9c45。先读最新接续/remote-upload/两gate/上轮证据，实时PR2/Reader1仍330c670/94a50b5、base main feaa556/2e3a9cf；最新工程CI42926442424/42926434671/42926434658成功、Reader41419425879联合成功/41419417088 GDS整体失败仍旧Viewer部署404。未重复推已有改动、未改main/C0/正式src/info.yaml；代码写权限历史成功不被本机网络失败推翻。

新的atecc_proof_session在锁定RAM完整22源CARD树中替换旧三命令owner，复用统一producer/exchange和原wake/共享总线：四Config32读+GenKey PUBLIC→Random/Nonce/Sign→四Config32读+GenKey PUBLIC，共十三命令。逐命令payload长度、CRC/count/STOP、完成掩码、64签名字节、分层deadline/abort/removal仍为成功前提。签名字节只临时输出，末次读回失败不能commit。新增所提议slot2/0x60/M0/revision/锁/2087与0033策略检查、空序列号拒绝；保存完整20B不可变header和64B公钥做精确读后比较，不用公开CRC/XOR摘要替代。公共bank未物理擦除，仅逻辑资格管理；未比较可信工厂注册记录，不能称硬件认证/真实安全器件或P256验证。

Icarus/CVC分别按14个源绑定配置验收（六正常166完成场景、八真实RTL反例；Icarus慢div100与其余配置分开记录，最终资格由具体日志/源码/TB哈希汇总，非伪称每个目录全矩阵重跑）。各32768单字节配置变化与Python所提议策略一致、672逐位精确比较控制通过。完整CARD CVC三正常CPB16/DIV2、CPB32/DIV8、CPB434/DIV100各31场共93，另三真实反例；Icarus完整低速31场。40MHz完整CARD CVC四慢配置：十三命令SDK M0 READ5/GENKEY115/Random23/Nonce20/Sign115ms实际STOP/ACK窗口、old20在预公钥计算按预期失败、提前ACK模型拒绝、最后公钥不匹配在64签名字节后失败并无外复位恢复。两摘要上下文26个命令包由原厂固定C构造器/CRC严格原生编译对齐；公钥fixture曲线有效但已知测试标量，签名数据是形状fixture，不是器件密码验证。没有100%覆盖率主张。

同完整边界、同锁Yosys/Liberty+LEF且所有generic FF保留：1450FF/64847.1936→2150FF/92003.2384，增加700FF/27156.0448µm²；新增160header+512公钥位、净28元数据位，另1446状态位以共同命名Q一一对应保留，非形式等价证明。整矩形占比1×2=253.12%、2×2=121.69%、3×2=80.10%、4×2=59.70%；前两连原始cell面积也容不下当前版本，后两尚未P&R，不称物理适配、未选购/确认价格或库存。不能为面积回退到缺少必要比较的版本冒充完整产品。

新2150FF净表的25ns clock-only SDC/Tcl已绑定实际22源/净表/库/根时钟，九坏输入拒绝控制通过；IO/reset/RC仍显式缺失，未设假例外、未运行原生STA，WNS/TNS=null。核对当前Reader正式入口40MHz/CPB347并补测该参数的完整CARD慢M0十三命令；实验CARD默认仍434，最终TT wrapper引脚/波特率对齐及新Reader RTL联合回归仍待完成，不能拿旧联测替代。代码与说明experimental/personalized_session；deliverables/personalized-session保存原始失败/反例、最终资格、冻结重放、全卡面积与FF账本、原厂C、源码zip/SHA/PR草案/发布记录。初始fixture错误、宿主Icarus600s长仿真超时、后续独立1800s宿主限时重跑均真实保留；DUT一秒总期限/200ms命令期限及全部检查未放宽。

两正式维持INCOMPLETE/NOT_SUBMITTED。下一优先正式TT引脚/347分频接入和当前Reader联合、数值STA/物理面积闭合，同时补可信工厂SKU/配置批准、注册UID/key绑定与实际安全器件/HAL/服务器动态挑战。FPGA/实体卡/FPC/触点/Reader实物DEFERRED_BY_USER并保留电气机械残余风险。平台付款/人工配置须基于实际准备与回执报告，push/PR/GDS均不算提交；发布结果单独见publication.json，无回执不称新PR/CI。
远程创建engineering/2026-10-29-tapeout-audit在CARD/READER均403 Resource not accessible by integration；账号为derrykervin，仓库metadata报告admin/push，但连接token没有实际写分支权限。重新配置GitHub连接/安装，向目标仓库授权Contents read/write、Pull requests read/write；修改workflows还需相应workflow权限。不得展示或索取token正文。
三个软件主仓库：Unity、FastAPI/SQLAlchemy/MySQL、Drive/OS均未确认。当前账号仓库搜索仅发现已知五仓库；初始/workspace没有Git项目/本地修改。武器编辑器和WFSM不充当主系统。
两个软件工具仓库默认main：WFS 001fcccaa7493618708a0b9312f11d57d0bf278b，WFSM ac82ec6c55e60220ffb4102ea84c7ffda085ddd0；无开放PR。五仓库审计时均无开放PR。没有改动C0稳定源码。
截止11/30建议内部门禁（非已完成承诺）：11/03前安全器件/引脚冻结及权限恢复，11/10前RTL和服务器接口冻结，11/17前联合回归和综合/时序，11/24前物理签核/官方预检及Revision准备，剩余时间处理平台反馈。发现时程不可达必须立即报告。
下一次先检查本地补丁、上游HEAD有无变化；不要覆盖稳定版本。先获得HDL执行能力，验证MISO补丁；然后解决动态挑战/器件桥与协议RTL。授权后基于上游新分支应用补丁、跑CI、建PR；最后才推进平台。

## 2026-10-30 接续工作包：v2流式接收参考
上游C0/CARD/READER HEAD均未变化。环境revision2已running，但代理8080连接仍失败；iverilog/vvp/yosys仍缺失。没有重复执行远程写入，403权限状态未重新验证。完成stream_parser.py及10项新增测试，合计17项通过。下一步优先恢复HDL仿真，验证MISO补丁；若仍不能执行，准备与参考语义一致的流式RTL接收器与testbench，但未运行前不得标验证通过。参考接收器不执行命令，不含安全器件认证、去重缓存或RTL集成。

## 2026-10-30 接续工作包：实验性流式RTL草案
三仓库上游HEAD仍未变化。新增experimental/protocol_v2/firm_frame_rx.v、生成向量及字段级scoreboard和check.sh；未修改流片source list，未接入CARD/READER。验证命令实际返回127（缺少iverilog）；只完成向量生成和shell语法检查，HDL完全未验证。1024位候选+1024位发布缓冲明显需要面积评估，不可直接集成1x2。下一步：取得仿真器后先跑check.sh，核实CRC/超时/clear语义和周期边界，再做面积合理化及产品命令层；同时验证早先MISO补丁。远程403未重探，无PR或平台提交。

## 2026-10-30 接续：HDL向量独立参考回放
上游三仓库HEAD未变；代理仍连接失败，无新增HDL工具。为已有HDL测试台增加严格语句子集回放器check_vectors.py，校验其10个预期发布帧与Python模型的字段/帧数及超时/clear输入语义；加入错误期望字段、错误计数、缺少结束和未知语句的故障注入测试。Python21项通过。check.sh先验证向量再查HDL工具。注意回放不执行Verilog、不验证HDL错误脉冲计数或寄存器清零，仍不得声称RTL仿真通过。下一步仍须恢复iverilog并验证MISO及实验RX；不再以增加参考测试代替HDL签核。

## 2026-10-30 接续：可执行CI工作包
新增CARD engineering-regression.yaml：core脚本(含MISO)/参考回归/通用综合，以及独立实验RX仿真job；新增READER joint-regression.yaml：锁定CARD feaa5568基线执行18组合+3故障参数矩阵，记录双方SHA与工具版本，always上传证据。保留原test/GDS/Precheck/GL/Viewer检查，没有关闭失败任务。仅YAML解析、结构检查与shell语法验证，工作流尚未上传或运行。中断后查询远程engineering分支404，未产生可核实远程分支；不把超时调用认作成功。需要GitHub Contents/PR/workflow写权限或用户手动应用补丁，才能触发真实CI。下一步优先应用CI补丁运行HDL，不能继续用参考测试冒充芯片进度。

## 2026-10-30 接续：修复补丁基线字节一致性
对照上游Git tree发现最初API快照存在CRLF归一化，READER README还存在Latin-1转码。已获取base64并以Git SHA核验恢复原字节（README按Latin-1逆转码后SHA完全相符）。CARD43/READER19个upstream blob全部匹配；本地缺失空文件补回精确基线。deliverables/rebuild-bundles.py生成exact-upstream.patch，并在临时精确基线上git am --keep-cr后比对目标tree，双仓库通过。必须优先用exact-upstream补丁或已更新的主补丁；旧分阶段增量只适合旧本地快照，不再推荐直接应用真实上游。没有新HDL/GDS/PR/平台证据。

## 2026-10-30 接续：UART停止位/BREAK修复（未仿真）
三上游HEAD未变。CARD和READER旧uart_rx在S_STOP不检查RX就发布valid，低停止位与持续BREAK可被误认数据。两端均加入停止位高校验、错误后等待线路回高再接收的S_RECOVER，以及非法状态恢复；未加新端口，不改变现有例化。新增相同的串行输入测试台，覆盖连续合法帧、坏停止位、持续BREAK、正常恢复、部分帧复位；纳入CARD CPB8/16/347/434与READER CPB8/16/347 CI入口。bash语法及diff检查通过；HDL实际入口127缺iverilog，修复未获仿真/综合签核，不得上传替代稳定main。现阶段仍没有对上层输出独立framing_error，也未解决UART CDC/过载/同周期读接收优先级，后续须分别审查。下一步先执行新UART台与既有核心/联合回归，取得证据后再推进其他功能。

## 2026-10-30 接续：物理基线证据审查
上游HEAD均未变。取得CARD/READER已有GDS及Precheck完整日志并保存带行号/时间戳摘录到deliverables，两者最终routing0/antenna0，流程LVS/DRC通过，独立Precheck通过。发现build KLayoutDRC跳过、fallback PNR/signoff SDC、lint5/3条；不能等价40MHz完整签核。新增PHYSICAL_BASELINE_AUDIT.md列阶段面积、证据链接及必须补提的最差corner/实际SDC/未约束路径。新MISO/UART/实验RTL仍没有新物理结果，不改SUBMITTED状态。下一步优先恢复CI上传/HDL执行与提取signoff artifacts，不再无验证地扩充RTL。

## 2026-10-30 接续：完整lint处置与artifact访问
上游三HEAD未变，取得两端artifact清单（均未过期）并提取CARD5/READER3条完整lint位置。新增LINT_DISPOSITION.md：CARD阻塞ALU临时计算不能直接改非阻塞；READER索引扩展需显式宽度，phase3需最高优先级fail closed防后续FSM覆盖。全部是待验证建议，无告警抑制。GitHub工具物化CARD tt_submission与GDS_logs文件服务引用，但执行器代理仍失败，ZIP未落地，未解析SDC/最差时序，不冒充已有数值签核。下一步恢复网络/工具后提取签核产物并跑新RTL CI。

## 2026-10-31 接续：READER内部故障优先保护（未仿真）
三上游HEAD均未变化。本地READER新增最高优先级phase=3/state>FAILED/AUTH索引>8保护；在普通FSM之外强制FAILED、清auth_pass与响应、关card_reset_n/TX，并保留错误4直到拔卡/复位。索引计算显式32位，receive phase case加default但非法处理在外层，避免被后续状态赋值覆盖。新增tb_reader_internal_faults验证非法phase+残留pass、非法state、越界索引，以及错误粘滞/拔卡/重插/复位，CPB8/16/347纳入现有joint CI。实际入口127缺iverilog；无HDL/lint/综合/GL新结果。不宣称已消除告警或完成安全认证；测试pass依旧是公开算法原型。下一步必须运行此台、UART故障台和完整联合回归，恢复平台权限后再建PR。

## 2026-10-31 接续：修复联合仿真UART来源覆盖
网络附加权限检查被中断，未取得联网成功结果；没有安装工具。三上游HEAD未变。发现原联合脚本只编译READER UART、让CARD也复用它，无法覆盖CARD真实UART实现。新增prepare_joint_sources.py，仅在build副本重命名Reader UART module/type（保持端口和实例名），编译双方各自UART；源和生成副本SHA256写入joint-sources.json，逐字节逆变换断言保证只改类型名。对当前两仓库实际生成9条来源记录、验证端口名保留、脚本语法与workflow YAML通过。尚未HDL编译/仿真，不能称联合回归通过。CI仍锁定公开CARD基线，验证本地修复需显式使用本地CARD或未来已验证SHA。下一步优先执行双方UART和联合台，恢复授权后上传CI。

## 2026-10-31 接续：C0官方合并与收录核实
正确官方仓库为TinyTapeout/tinytapeout-sky-26d（不是ttsky26d）。PR58 merged=true，2026-10-02T16:46:11Z，明确项目6057及a6b79b46源码。官方当前HEAD5b12186d项目目录包含commit_id/pdk/OAS/LEF/网表/统计；commit_id字段再次确认6057/源码/工作流。因此C0可标SUBMITTED（仅收录，不声称制造交付），稳定C0不动。归档公共机器证据至release/C0_OFFICIAL_EVIDENCE.json和deliverables/c0-official/。当前官方完整树无CARD/READER目录，公开PR搜索未匹配，不推断平台一定未建项目，正式两颗状态仍提交未确认。三源码上游HEAD未变。下一步利用已确认官方流程准备两颗Revision证据清单，同时优先恢复HDL及GitHub写权限。

## 2026-10-31 接续：官方共享芯片接口核实
三源码上游HEAD未变。锁定官方SKY26d子模块tt-multiplexer@8fbe6cd3，读取docs/INFO.md和rtl/tt_top.v。确认SKY130 Open Frame QFN64管理脚22/24/25=ena/inc/sel_reset，用户clk50/reset51，UART ui0=31/uo0=62；多电源域存在。归档官方表到deliverables/tt-sky130-pinout-source.md，新增硬件接口约束文档。特别禁止把平台ID6057当mux计数，最终地址需交付Revision分配。8触点必须本地管理/复位/稳压支持，目前没有载板验证；封装尺寸/2.20mm厚度未确认。下一步取得最终封装/管理时序和选择地址，优先恢复HDL/CI执行。

## 2026-10-31 接续：离线发布证据门禁
三源码上游HEAD未变。新增release_gate.py核对14项签核记录的精确源码SHA、结果和证据链接，以及GDS/OAS哈希；旧基线绿色记录不能验证新源码。官方样式JSON即使字段一致，也只输出REQUIRES_LIVE_VERIFICATION，绝不由离线输入自动断言SUBMITTED。新增5项门禁反向测试，全部Python回归26项通过。当前正式两颗manifest未填已执行证据，门禁应返回INCOMPLETE非零；不代表新HDL验证、产品安全认证或平台提交。下一步仍以恢复HDL/CI和真实Revision证据为优先。

## 2026-10-31 接续：认证挑战规范编码参考
三上游HEAD未变。定义候选固定123字节transcript v1，绑定域/版本/密钥查找ID/挑战ID/32B nonce/账号UUID/SteamID/UID/AppID/audience/过期，适配v2<=128B payload，公开参考编码无秘密。新增字段绑定/范围/传输预算测试，全部Python29项通过；合成向量hashlib与OpenSSL SHA256独立比对一致。没有安全器件签名、验签、真实随机数或后端/RTL集成，不声称安全认证完成。下一步冻结器件接口并执行真实互通；HDL/CI和远程写权限仍优先阻塞。

## 2026-10-31 接续：P-256软件参考签名互通
三上游HEAD未变。新增proof_signature.py成熟库P256预哈希验签、DER/raw低S转换；临时内存测试密钥签名由OpenSSL对原始transcript验签成功，篡改/错key/错curve/highS/错误DER/重复哈希均拒绝。完整Python34项通过。锁定cryptography50.0.0参考依赖，工程CI增加安装步骤（远程未跑）。没有私钥落盘或入RTL；不代表安全器件、个性化、后端/Steam集成完成，更不改变原型公开认证。下一步器件接口和实际硬件互通仍缺，HDL/CI执行及写权限仍是流片优先阻塞。

## 2026-10-31 接续：CARD RX读确认竞争修复（未仿真）
三上游HEAD未变。没有额外执行会话；apt-get download iverilog返回100 Unable to locate package，未安装工具；没有绕过网络策略。CARD同沿UART有效脉冲与CPU读UART_DATA时，旧代码先置pending后读清零，新字节变成不可见。最小改动改为先确认旧字节、后接收新字节，接收优先。新增uart_pending_tb在SoC字节缓冲边界注入同沿事件，检查旧字节采样、新字节pending保留、空缓冲同沿读取、普通ACK/status读/reset，并纳入核心检查入口。bash/diff检查通过，实际HDL入口127缺iverilog，回归台未执行。此修复不解决未读取时连续新字节overrun，不声称FIFO或错误码已实现。下一步优先运行该台与既有UART/联合/物理流程，不能用参考Python通过替代。

## 2026-10-31 接续：解除本地RTL执行阻塞，40场景实际通过
使用现有GCC/Make构建CVC锁定分支1c5e043e，73个源blob逐一核验，许可证已读并保留，仅工具目录本地使用、不随ASIC补丁分发。40正向RTL+1预期fatal控制通过（41/41runner）；覆盖全部已准备核心/联合/故障/实验RX矩阵。旧UART/pending/MISO/Reader guard源码均触发新增测试fatal，证明缺陷可检出。CVC的fatal返回0，因此严格要求明确PASS、无fatal、零错误，新增5个runner判定测试；Python合计39通过。代码tools/run_cvc_regression.py可复跑，报告validation/CVC_RTL_RESULTS.md，日志/工具与源码SHA在deliverables。三上游HEAD未变。Icarus仍缺、官方CI/GitHub写权限/新综合STA-GDS-GL未解决；下轮优先补官方同等执行和覆盖率/时序，避免继续累积功能。C0不动，正式两颗仍发布INCOMPLETE。

## 2026-10-31 接续：实际toggle覆盖与语句口径控制
三上游HEAD未变。run_cvc_regression新增--toggle-coverage，按DUT模块范围重跑40场+fatal控制41/41通过，40份报告/tgldat已落盘；summarize_cvc_toggle.py检查分母和模块总数一致，不平均不兼容场景。控制模块3bit仅1bit双向翻转，计数验证1hit/2miss/3bits。语句覆盖控制用例存在未执行分支但CVC报告ALL，故拒绝语句100%结论，不将此项标PASS，原因待查。新增3个汇总器反向测试，Python合计42项通过。完整说明validation/TOGGLE_COVERAGE.md。下轮优先官方同等执行、可靠语句/分支覆盖与新综合/STA，不能把toggle当产品验收。

## 用户最新授权与本轮目标（2026-10-31）
用户已要求暂缓FPGA/实体卡/FPC/触点/Reader实物测试，采用更强软件、RTL、故障注入与安全模型测试尽量弥补；实物项标DEFERRED_BY_USER，不能标PASS，综合/STA/P&R/DRC/LVS/Precheck/GL等流片硬验收仍必须。远程创建分支权限已由实际创建和回读确认恢复，不再沿用“分支必定403”的旧结论；代码、workflow和PR权限本轮分别核验。优先上传已有经过补充仿真的修复到新工程分支，保持main及C0不变，真实运行新版官方CI。
