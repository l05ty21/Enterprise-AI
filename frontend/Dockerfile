FROM node:22-slim AS build

# 注意：不要用 alpine 构建。musl 的默认线程栈只有 128 KB，
# Rollup 4 的原生解析器在解析 @element-plus/icons-vue 这类深嵌套代码时
# 会报 "Code is nested too deeply"，换成 glibc 镜像即可。
# 另外小规格机器（1 GiB）必须限制 V8 堆，否则 vite build 峰值会直接 abort。
ARG NPM_REGISTRY=https://registry.npmjs.org

ENV NODE_OPTIONS=--max-old-space-size=768

WORKDIR /app

COPY package*.json ./
RUN npm config set registry ${NPM_REGISTRY} \
    && (npm ci --no-audit --no-fund || npm install --no-audit --no-fund)

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
