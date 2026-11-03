# 部署配置与密钥

仓库里只放**模板与占位符**；令牌、OSS AccessKey、TLS 私钥都放在本地或被 Git 忽略的位置。

## 本地 Docker Compose

```bash
cp deploy/.env.example deploy/.env
# 编辑 deploy/.env，填入 PUBLISH_TOKEN 与 OSS_ACCESS_KEY_*
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d
```

- `deploy/.env` 已被 `.gitignore` 忽略，不要提交。
- 不填 `OSS_*` 时，服务会退回到本地的文件对象存储，只适合本地验证。
- 生产部署必须填完整的 `OSS_BUCKET`、`OSS_ENDPOINT`、`OSS_PREFIX`、`OSS_ACCESS_KEY_ID`、`OSS_ACCESS_KEY_SECRET`。

## K3s

`deploy/k8s/overlays/prod-oss/` 是模板：host、OSS bucket 与 endpoint 都是占位值。真实值放在本地 overlay（如 `deploy/k8s/overlays/local/`，已被 `.gitignore` 忽略）或用本地 patch 覆盖，不要提交。

`deploy/k8s/base/secret.yaml` 只是字段说明，**不参与** `kubectl apply -k`。真实 Secret 在集群里按需创建，命令从本地环境读取，不要把值写进 YAML：

```bash
kubectl create secret generic situlearn-secrets -n situlearn \
  --from-literal=PUBLISH_TOKEN="$PUBLISH_TOKEN" \
  --from-literal=OSS_ACCESS_KEY_ID="$OSS_ACCESS_KEY_ID" \
  --from-literal=OSS_ACCESS_KEY_SECRET="$OSS_ACCESS_KEY_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -
```

拉取私有镜像的 `registry-credentials` 与 TLS 证书 `situlearn-tls` 同样在集群内创建，不进入仓库。

## OSS 权限

RAM 子账号只需要 `situlearn/` 前缀下的对象权限：

```json
{
  "Effect": "Allow",
  "Action": ["oss:GetObject", "oss:PutObject", "oss:DeleteObject", "oss:ListObjects"],
  "Resource": ["acs:oss:*:*:<OSS_BUCKET>/situlearn/*"]
}
```

Bucket 保持私有读，不开静态网站托管；部署时使用同地域内网 endpoint。

## 提交前自检

```bash
git status --short
git check-ignore -v deploy/.env          # 应命中 .gitignore
grep -RInE "LTAI[0-9A-Za-z]{10,}|BEGIN .*PRIVATE KEY" --exclude-dir=.git .
```
