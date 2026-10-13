FROM node:24-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ENV BACKEND_URL=http://backend:8000
RUN npm run build
RUN chown -R node:node /app/.next
USER node
CMD ["npx", "next", "start", "--hostname", "0.0.0.0"]
