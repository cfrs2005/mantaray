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

LAN 直连 → 敏感服务固定代理 → CN 直连 → 海外代理 → GeoIP CN 直连 → FINAL 代理

## 结构

```
configs/   daily.conf / strict.conf / debug.conf
rules/     lan_direct / direct_cn / proxy_global / sensitive_services / custom
dns/       simple_dns.conf / strict_dns.conf
docs/      config-vs-scene / rule-priority / troubleshooting / risk-control / migration
```

## 文档

- [配置 vs 场景](docs/config-vs-scene.md)
- [规则优先级](docs/rule-priority.md)
- [排障手册](docs/troubleshooting.md)
- [风控指南](docs/risk-control-guidelines.md)

## License

MIT
