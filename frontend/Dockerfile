# Frontend dev container (Vite + HMR). Vite proxies /api -> localhost:8001, so this runs
# with host networking in compose to reach the host-networked API. For a prod build you'd
# instead `npm run build` and serve dist/ via nginx.
FROM node:20-alpine
WORKDIR /app

# Install deps first for layer caching (node_modules is built in-image; .dockerignore keeps
# the host's copy out so the container's arch-correct modules are used).
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3001
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3001"]
