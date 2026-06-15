FROM node:22-slim

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

ENV BACKEND_PORT=4000
EXPOSE 4000
CMD ["npm", "start"]
