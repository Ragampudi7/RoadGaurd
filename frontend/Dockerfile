# RoadGuard UI.
#
# Two stages: Node builds the bundle, then a much smaller image serves the
# static output. Nothing from the build stage - node_modules, the toolchain,
# the source - reaches the running container.

# ---------------------------------------------------------------- build --
FROM node:22-alpine AS build
WORKDIR /app

# Vite substitutes these into the bundle at BUILD time. A runtime environment
# variable would arrive long after the JavaScript was written to disk and
# would do nothing at all.
#
# Railway passes a service variable into a Dockerfile build ONLY if the
# Dockerfile declares it with ARG. Without these two lines the build quietly
# succeeds against http://localhost:8000 and the deployed site cannot reach
# its own API - with no error anywhere, because nothing failed.
ARG VITE_API_BASE
ARG VITE_USE_MOCK=false
ENV VITE_API_BASE=$VITE_API_BASE \
    VITE_USE_MOCK=$VITE_USE_MOCK

# package files first so the dependency layer survives source changes.
# `npm ci` (not `install`) installs exactly the committed lockfile.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---------------------------------------------------------------- serve --
FROM node:22-alpine
WORKDIR /app

RUN npm install -g serve@14 && npm cache clean --force

COPY --from=build /app/dist ./dist

# -s ("single") rewrites any unknown path to index.html. BrowserRouter needs
# that: without it, a refresh on /app/reports asks the server for a file that
# was never built and gets a 404 instead of a React route.
CMD ["sh", "-c", "serve -s dist -l ${PORT:-3000}"]
