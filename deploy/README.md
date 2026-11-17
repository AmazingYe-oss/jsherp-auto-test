# 现有环境恢复与自启动

2026-11-11：Ubuntu 已启用 systemd，docker.service 与 containerd.service 已 enabled。ERP 四个现有容器 erp-practice-mysql-1、erp-practice-redis-1、erp-practice-api-1、erp-practice-web-1 均设为 restart=always。

WSL Ubuntu 启动 → systemd 启动 Docker → Docker 启动 ERP 容器。服务初始化需要时间。该配置不会主动在 Windows 开机时启动 WSL。

## 恢复说明与限制

- nginx.conf 按此前从运行容器读取的原配置恢复，代理 /jshERP-boot/ 到 api:9999。
- 原02-test-config.sql已缺失，当前文件仅为注释占位，满足既有容器的文件挂载要求，没有SQL，不是原脚本恢复版。已有MySQL数据卷已初始化，启动不会重新初始化数据。
- 数据库与上传数据卷保留，未删除、重建或重置。原Compose文件仍缺失，不能声称支持全新环境重建。

## 验证

四容器running，MySQL/Redis healthy，前端HTTP 200，登录用例1 passed, 1 warning in 2.84s。报告：test-results/service-restart-login.xml。

已核验持久化自启动配置；未重启整个WSL做冷启动演练，避免影响其他运行服务。本轮没有执行商品新增或编辑。

```bash
systemctl is-enabled docker.service containerd.service
docker ps --filter name=erp-practice
curl -I http://127.0.0.1:18090/
```
