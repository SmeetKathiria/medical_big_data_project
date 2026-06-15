FROM node:22-slim AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY next.config.js postcss.config.js tailwind.config.ts tsconfig.json ./
COPY app ./app
COPY components ./components
ARG NEXT_PUBLIC_API_URL=http://localhost:4000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production
ENV FRONTEND_PORT=3000
COPY --from=build /app/package*.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next
COPY --from=build /app/next.config.js ./next.config.js
COPY --from=build /app/app ./app
COPY --from=build /app/components ./components
EXPOSE 3000
CMD ["npm", "start"]
