FROM node:22-alpine AS build

# npm 源：默认官方，国内可传 https://registry.npmmirror.com
ARG NPM_REGISTRY=https://registry.npmjs.org

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
