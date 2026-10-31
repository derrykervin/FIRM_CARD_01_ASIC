版本：0.2.0（2026-10-30）
状态：设计目标 / 审计记录；除明确证据外未实现、未仿真、未物理验证。
负责系统：CARD / READER / FPC / Server。
依赖：锁定源码 SHA、外部安全器件选型、平台权限。
验证标准：下述验收条款逐项提供可复现证据。
已知风险：旧版认证不安全；平台未提交；封装未确认。

# 数据模型候选
accounts(id, status, session_version)；steam_bindings(steam_id UNIQUE, account_id FK)；cards(id, uid CHAR(10) ASCII UNIQUE, printed_number CHAR(16) ASCII UNIQUE, series, key_version, public_key_id UNIQUE, status, supersedes FK)；card_bindings(card_id, account_id, valid_from, valid_to, actor)；challenges(id UNIQUE, nonce_hash, transcript_hash, account_id, card_id, expires_at, consumed_at)；sessions(id, account_id, card_id, expires_at, revoked_at)；audit_events(id, actor, action, object, time, request_id)。
MySQL版本和迁移工具未确认，不提供假称可直接上线的迁移。使用InnoDB外键、二进制/ASCII排序规则并验证十进制长度。一个卡当前绑定以独立current_card_bindings(card_id PRIMARY KEY, account_id FK)保证；历史表保留审计。账号是否允许多卡是待定产品策略。
挑战消费用事务内条件UPDATE（consumed_at IS NULL且未过期）并验证affected_rows=1；验签与签发流程必须防并发TOCTOU并复核状态版本。日志不得写票据、私钥或完整可重用token。
