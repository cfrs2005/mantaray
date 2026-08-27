# Mantaray

个人出口一致性分流配置。仅自用，切勿照搬。

核心目标：降低因出口漂移、DNS 不一致导致的 AI 平台及海外服务账号风控风险。

## 使用

```
# 日常
https://raw.githubusercontent.com/cfrs2005/mantaray/main/configs/daily.conf

# 严格（高风控场景）
https://raw.githubusercontent.com/cfrs2005/mantaray/main/configs/strict.conf
```

配置模式导入，不要用场景模式。严格模式搭配固定节点。

## 分流逻辑

LAN 直连 → 私有域出口绑定 → 敏感服务固定代理 → CN 直连 → 海外代理 → GeoIP CN 直连 → FINAL 代理

## 出口一致性有两条链

出口由 `[Rule]` 决定，解析源由 `dns-server` / `[Host]` / 落地节点决定。两条链必须配对：

| 出口 | 解析源 | |
|------|--------|---|
| DIRECT | 本地国内 DNS 或静态 Host | ✅ |
| PROXY | 落地节点解析 | ✅ |
| DIRECT | 海外 DNS | ❌ 海外 IP 走国内出口 |
| PROXY | 本地 DNS | ❌ 国内 IP 走海外出口 |

由此得到全项目唯一一条 DNS 铁律：

> **只给 DIRECT 出口的域名做 DNS 绑定。走 PROXY 的域名不要写进 `[Host]`。**

逐域名绑定在 `dns/pinning.conf`，原理与踩坑见 [DNS 出口绑定](docs/dns-pinning.md)。

## 改配置

`[Host]` 段不支持 RULE-SET 远程加载，只能内联进每个 conf。所以真源只有一份，
`configs/*.conf` 是产物：

```bash
vim dns/pinning.conf        # 改这里，不要改 configs/ 里的标记区块
python3 scripts/sync.py     # 注入 configs/ 和 configs/local/
python3 scripts/verify.py   # 门禁，改完必跑
```

`verify.py --live` 追加 RULE-SET 可达性和实测解析对照。

仓库公开 + `[Host]` 只能内联 = 写进 `dns/pinning.conf` 的东西等于公开发布。
所以那里只放公开可查的域名，个人基础设施走私有层：

```bash
cp dns/pinning.local.example.conf dns/pinning.local.conf   # 已 gitignore
vim dns/pinning.local.conf                                  # 机场域名 / 内网 IP / 内部服务
python3 scripts/sync.py                                     # 产物落 configs/local/
```

`configs/local/*.conf` 手动导入 Shadowrocket，代价是放弃 `update-url` 自动更新。
判据：这条信息公开出去，会不会给别人多一个打你的入口。

## 结构

```
configs/   daily.conf / strict.conf / debug.conf / main.conf
rules/     lan_direct / direct_cn / proxy_global / sensitive_services / custom
dns/       pinning.conf（绑定真源）/ simple_dns / strict_dns
scripts/   sync.py（注入）/ verify.py（门禁）
docs/      dns-pinning / rule-priority / troubleshooting / risk-control / config-vs-scene / migration
```

## 文档

- [DNS 出口绑定](docs/dns-pinning.md)
- [规则优先级](docs/rule-priority.md)
- [排障手册](docs/troubleshooting.md)
- [风控指南](docs/risk-control-guidelines.md)
- [配置 vs 场景](docs/config-vs-scene.md)

## License

MIT
