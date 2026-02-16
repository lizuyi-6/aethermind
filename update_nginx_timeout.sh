#!/bin/bash

NGINX_CONF="/etc/nginx/sites-enabled/app-chaozhiyinqing.top"
BACKUP_CONF="${NGINX_CONF}.bak_$(date +%Y%m%d_%H%M%S)"

echo "Checking Nginx config: $NGINX_CONF"

if [ -f "$NGINX_CONF" ]; then
    echo "Backing up config to $BACKUP_CONF"
    cp "$NGINX_CONF" "$BACKUP_CONF"
    
    echo "Updating timeouts to 1200s..."
    
    # Update or add proxy_read_timeout
    if grep -q "proxy_read_timeout" "$NGINX_CONF"; then
        sed -i 's/proxy_read_timeout.*$/proxy_read_timeout 1200s;/' "$NGINX_CONF"
    else
        sed -i '/proxy_pass/a \        proxy_read_timeout 1200s;' "$NGINX_CONF"
    fi
    
    # Update or add proxy_connect_timeout
    if grep -q "proxy_connect_timeout" "$NGINX_CONF"; then
        sed -i 's/proxy_connect_timeout.*$/proxy_connect_timeout 1200s;/' "$NGINX_CONF"
    else
        sed -i '/proxy_pass/a \        proxy_connect_timeout 1200s;' "$NGINX_CONF"
    fi
    
    # Update or add proxy_send_timeout
    if grep -q "proxy_send_timeout" "$NGINX_CONF"; then
        sed -i 's/proxy_send_timeout.*$/proxy_send_timeout 1200s;/' "$NGINX_CONF"
    else
        sed -i '/proxy_pass/a \        proxy_send_timeout 1200s;' "$NGINX_CONF"
    fi
    
    echo "Testing Nginx configuration..."
    nginx -t
    
    if [ $? -eq 0 ]; then
        echo "Reloading Nginx..."
        systemctl reload nginx
        echo "Nginx updated successfully."
    else
        echo "Configuration test failed! Restoring backup..."
        cp "$BACKUP_CONF" "$NGINX_CONF"
        echo "Restored original configuration."
        exit 1
    fi
else
    echo "Config file not found: $NGINX_CONF"
    exit 1
fi
