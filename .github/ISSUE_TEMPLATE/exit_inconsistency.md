---
name: 出口不一致
about: 同一服务出口 IP 不同、区域混用等问题
title: '[Exit] '
labels: exit-inconsistency
assignees: ''
---

## 目标服务

哪个服务出现了出口不一致？

## 不一致表现

- [ ] 同一服务 Web 和 App 出口不同
- [ ] 同一服务 API 和页面出口不同
- [ ] 短时间内出口 IP 地理位置变化
- [ ] DNS 解析区域与出口区域不一致
- [ ] 其他（请描述）

## 出口信息

- 预期出口区域：
- 实际出口 IP / 区域：
- 检查方式（ip.sb / myip.ipip.net 等）：

## 配置信息

- 使用的配置文件：daily / strict / debug
- 该服务是否在 `sensitive_services.list` 中：是 / 否
- 节点选择方式：固定 / 自动选择 / 回退
- DNS 配置：simple / strict

## 网络环境

- [ ] Wi-Fi
- [ ] 蜂窝
- [ ] 切换过网络环境

## 补充信息

如有规则命中截图或请求日志请附上。
