FROM node:18-alpine
RUN apk add --no-cache python3 make g++
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY claude_proxy.js .
# NOTE: .env.jarvis는 런타임에 --env-file 또는 docker-compose env_file로 주입
# 절대 이미지에 포함하지 마세요 (시크릿 노출 위험)
EXPOSE 8765
CMD ["node", "claude_proxy.js"]
