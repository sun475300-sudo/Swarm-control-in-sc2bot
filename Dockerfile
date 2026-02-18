FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY claude_proxy.js .
COPY .env.jarvis .
EXPOSE 8765
CMD ["node", "claude_proxy.js"]
