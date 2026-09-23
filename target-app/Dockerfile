# Node.js Lightweight Base Image
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package metadata & install production dependencies
COPY package.json ./
RUN npm install --only=production

# Copy application source code
COPY . .

# Expose default port 3001
EXPOSE 3001

# Start target app server
CMD ["node", "server.js"]
