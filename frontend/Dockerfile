# BiYou 前端独立 Dockerfile (Multi-stage: Node.js 20 构建 + Nginx 镜像运行)

# Stage 1: 构建静态资源
FROM node:20-alpine AS builder

WORKDIR /app

# 复制依赖声明文件并安装依赖
COPY package.json ./
RUN npm install

# 复制前端项目代码
COPY tsconfig*.json vite.config.ts index.html ./
COPY src ./src
COPY public ./public

# 执行 Vite 生产环境打包构建
RUN npm run build

# Stage 2: 使用 Nginx 托管前端静态资源
FROM nginx:alpine

# 复制打包好的产物到 Nginx 目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置文件
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
