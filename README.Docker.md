# Docker 部署指南

## 快速开始

### 1. 准备环境变量

复制环境变量模板并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写你的 API Key 等配置。

### 2. 构建并启动服务

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 3. 访问应用

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 4. 停止服务

```bash
# 停止服务
docker-compose stop

# 停止并删除容器
docker-compose down

# 停止并删除容器、网络、卷
docker-compose down -v
```

## 开发模式

如果需要在开发模式下运行（支持热重载）：

```bash
# 仅启动后端
docker-compose up backend

# 前端在本地运行
cd frontend
npm install
npm run dev
```

## 生产部署

### 使用 Docker Compose

```bash
# 构建生产镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看运行状态
docker-compose ps
```

### 单独构建镜像

```bash
# 构建后端镜像
docker build -t ai-test-backend:latest ./backend

# 构建前端镜像
docker build -t ai-test-frontend:latest ./frontend

# 运行后端
docker run -d \
  --name ai-test-backend \
  -p 8000:8000 \
  --env-file .env \
  ai-test-backend:latest

# 运行前端
docker run -d \
  --name ai-test-frontend \
  -p 3000:80 \
  --link ai-test-backend:backend \
  ai-test-frontend:latest
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| LLM_PROVIDER | LLM 提供商 | openai |
| LLM_API_KEY | API 密钥 | - |
| LLM_BASE_URL | API 基础 URL | https://api.deepseek.com |
| LLM_MODEL | 模型名称 | deepseek-chat |
| LLM_TIMEOUT_SECONDS | 请求超时时间（秒） | 60 |
| LLM_TEMPERATURE | 温度参数 | 0.2 |

### 端口映射

- 前端：3000 -> 80
- 后端：8000 -> 8000

如需修改端口，编辑 `docker-compose.yml` 中的 `ports` 配置。

## 故障排查

### 查看容器状态

```bash
docker-compose ps
```

### 查看日志

```bash
# 所有服务日志
docker-compose logs

# 实时日志
docker-compose logs -f

# 特定服务日志
docker-compose logs backend
```

### 进入容器调试

```bash
# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

## 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 清理旧镜像
docker image prune -f
```
