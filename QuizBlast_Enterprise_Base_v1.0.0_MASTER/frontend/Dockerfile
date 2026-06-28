FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json .npmrc ./

RUN npm ci --no-audit --no-fund

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
