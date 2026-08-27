# Changelog

## [0.2.0] - 2026-08-27

### Added
- **DNS 出口绑定层**：`dns/pinning.conf` 作为「域名 → (解析源, 流量出口)」的唯一真源
- **铁律**：只给 DIRECT 出口的域名绑解析源；PROXY 域名交给落地节点，不写进 `[Host]`
- 三层解析模型：L0 静态 Host / L1 域名级绑定 / L2 全局 dns-server / L3 落地解析
- `scripts/sync.py`：把绑定注入 4 个 conf 的标记区块（`[Host]` 不支持远程 RULE-SET，只能内联）
- `scripts/verify.py`：门禁。守 `[Host]` 三个静默失效的坑、出口/解析源配对、规则顺序与重复、
  conf 与真源漂移；`--live` 追加 RULE-SET 可达性与实测解析
- `pin-exempt` 豁免机制：anycast 域名（解析结果与解析源无关）可标注理由跳过配对检查
- 私有层 `dns/pinning.local.conf`（gitignore）+ `pinning.local.example.conf` 模板，
  产物落 `configs/local/`，个人基础设施不进公开仓库
- `docs/dns-pinning.md`

### Fixed
- 4 个 conf 的 `skip-proxy` 含非法 token `e.]`，换成 `127.0.0.1` + `captive.apple.com`
- `gs-robot.com` 全球服务出口分裂：实测确认区域化靠独立子域而非 GeoDNS，
  补上漏掉的 `bot-us.gs-robot.com`（US/Azure），与 `bot-eu` 一并置于通配之前
- `gs-robot.com` DIRECT 规则重复声明
- `[Host]` 中一条通配绑定的域名后多打了一个空格，整条静默失效
- 实测清理 7 条死绑定：6 个域名无 A 记录，1 个已过期落到域名停放页

### Changed
- 私有域出口绑定提到规则链第 2 位（仅次于 LAN）——确切的知识先于通用清单命中
- `debug.conf` 开启 `dns-direct-fallback-proxy`，并标注该模式会破坏出口一致性
- 外部规则源（blackmatrix7 OpenAI.list）在 `daily.conf` 默认开启、`strict.conf` 默认关闭

## [0.1.0] - 2026-03-09

### Added
- 项目初始化
- 三种配置模式: daily / strict / debug
- 模块化规则: LAN 直连 / CN 直连 / 海外代理 / 高风控服务 / 自定义
- DNS 配置: 简单双源 / 严格单源
- 文档: 配置 vs 场景 / 规则优先级 / 排障手册 / 风控指南 / 迁移指南
- GitHub Issue 模板
