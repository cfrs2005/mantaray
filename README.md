# Mantaray

> 一个面向稳定出口一致性的网络分流配置管理方案。
>
> 本项目关注的不是「规则越多越强」，而是「出口是否一致、行为是否可解释、风控场景是否足够稳」。

适用于希望通过 GitHub 维护个人代理配置，并降低因分流混乱、DNS 不一致、敏感服务规则漂移而带来的账号风险的用户。

## 核心原则

| 原则 | 含义 |
|------|------|
| 出口一致性优先 | 同区域、同节点、同解析策略、同分流结果 |
| 可解释优先 | 每条规则可追溯，命中逻辑透明 |
| 最小复杂度 | 不追求策略组炫技，不追求极限测速 |
| 敏感服务隔离 | 高风控服务从普通分流中独立出来 |

## 快速开始

1. 复制日常配置的 raw URL：

```
https://raw.githubusercontent.com/cfrs2005/mantaray/main/configs/daily.conf
```

2. 在代理客户端中使用 **配置模式** 导入（不要使用场景模式，详见 [配置 vs 场景](docs/config-vs-scene.md)）

3. 验证出口：
   - 访问国内站点 → 应为直连（本地 IP）
   - 访问海外站点 → 应为代理出口 IP

4. 如需高风控场景，切换为严格配置：

```
https://raw.githubusercontent.com/cfrs2005/mantaray/main/configs/strict.conf
```

## 三种模式

| 模式 | 文件 | 适用场景 | DNS | 规则集 |
|------|------|----------|-----|--------|
| 日常 | `configs/daily.conf` | 日常浏览 | 双源 DoH | 全量 |
| 严格 | `configs/strict.conf` | 高风控服务 | 单源 DoH | 精简（无 custom / proxy_global） |
| 调试 | `configs/debug.conf` | 排障定位 | 双源 + fallback | 全量 + IPv6 |

### 模式选择建议

- **日常**：大部分时间用这个，体验与稳定性兼顾
- **严格**：登录高价值账号前切换，用固定节点
- **调试**：出口异常时临时使用，定位命中规则

## 默认分流逻辑

```
请求 → ① LAN 直连
     → ② 敏感服务 → 固定代理
     → ③ CN 域名 → 直连
     → ④ 海外域名 → 代理
     → ⑤ 自定义规则
     → ⑥ GeoIP CN → 直连
     → ⑦ FINAL → 代理
```

一句话总结：**中国直连，海外代理，敏感服务固定出口。**

## 项目结构

```
mantaray/
├── configs/                    # 主配置文件
│   ├── main.conf              # 基础模板
│   ├── daily.conf             # 日常模式
│   ├── strict.conf            # 严格模式
│   └── debug.conf             # 调试模式
├── rules/                      # 模块化规则
│   ├── lan_direct.list        # 局域网/保留地址
│   ├── direct_cn.list         # 中国域名直连
│   ├── proxy_global.list      # 海外服务代理
│   ├── sensitive_services.list # 高风控服务
│   └── custom.list            # 用户自定义
├── dns/                        # DNS 配置参考
│   ├── simple_dns.conf        # 双源 DoH
│   └── strict_dns.conf        # 单源 DoH
├── docs/                       # 文档
│   ├── config-vs-scene.md     # 配置 vs 场景
│   ├── rule-priority.md       # 规则优先级
│   ├── troubleshooting.md     # 排障手册
│   ├── risk-control-guidelines.md # 风控指南
│   └── migration-guide.md     # 迁移指南
└── .github/
    └── ISSUE_TEMPLATE/         # Issue 模板
```

## 文档

- [配置模式 vs 场景模式](docs/config-vs-scene.md) — 首先理解这个
- [规则优先级说明](docs/rule-priority.md) — 理解请求为什么走了这条路
- [排障手册](docs/troubleshooting.md) — 出问题时从这里开始
- [风控场景指南](docs/risk-control-guidelines.md) — 高价值账号必读
- [迁移指南](docs/migration-guide.md) — 从其他配置迁移

## 重要声明

本项目旨在降低因分流混乱、DNS 不一致、出口漂移而导致的网络环境不稳定问题。

**不能保证账号绝对安全。** 平台风控可能基于设备指纹、Cookie、登录行为、历史异常等多维度判断，出口一致性只是其中一个因素。

## License

MIT
