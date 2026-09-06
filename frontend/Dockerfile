FROM nginx:alpine

# Pull in OS-level security patches (util-linux, etc.) before serving.
# Resolves CVE-2026-53612/53613/53614/76642/78408/78409/78410 when Alpine has backported.
RUN apk upgrade --no-cache

COPY dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
