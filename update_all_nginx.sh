#!/bin/bash

LOG_FILE="/root/test_2/nginx_update.log"
echo "Starting Nginx update at $(date)" > "$LOG_FILE"

# Function to update a file
update_conf() {
    local CONF_FILE=$1
    if [ -f "$CONF_FILE" ]; then
        echo "Updating $CONF_FILE" | tee -a "$LOG_FILE"
        cp "$CONF_FILE" "${CONF_FILE}.bak_$(date +%s)"
        
        # Define the timeout settings
        TIMEOUTS="proxy_read_timeout 1800s;\n        proxy_connect_timeout 1800s;\n        proxy_send_timeout 1800s;\n        send_timeout 1800s;\n        uwsgi_read_timeout 1800s;"
        
        # Check if proxy_pass exists (to know where to insert if missing)
        if grep -q "proxy_pass" "$CONF_FILE"; then
            # Update existing values or insert if missing
            
            # proxy_read_timeout
            if grep -q "proxy_read_timeout" "$CONF_FILE"; then
                sed -i 's/proxy_read_timeout.*$/proxy_read_timeout 1800s;/' "$CONF_FILE"
            else
                sed -i '/proxy_pass/a \        proxy_read_timeout 1800s;' "$CONF_FILE"
            fi
            
            # proxy_connect_timeout
            if grep -q "proxy_connect_timeout" "$CONF_FILE"; then
                sed -i 's/proxy_connect_timeout.*$/proxy_connect_timeout 1800s;/' "$CONF_FILE"
            else
                sed -i '/proxy_pass/a \        proxy_connect_timeout 1800s;' "$CONF_FILE"
            fi
            
            # proxy_send_timeout
            if grep -q "proxy_send_timeout" "$CONF_FILE"; then
                sed -i 's/proxy_send_timeout.*$/proxy_send_timeout 1800s;/' "$CONF_FILE"
            else
                sed -i '/proxy_pass/a \        proxy_send_timeout 1800s;' "$CONF_FILE"
            fi
            
             # send_timeout
            if grep -q "send_timeout" "$CONF_FILE"; then
                sed -i 's/send_timeout.*$/send_timeout 1800s;/' "$CONF_FILE"
            else
                sed -i '/proxy_pass/a \        send_timeout 1800s;' "$CONF_FILE"
            fi
            
            echo "Updated $CONF_FILE successfully." | tee -a "$LOG_FILE"
        else
            echo "Skipping $CONF_FILE (no proxy_pass found)" | tee -a "$LOG_FILE"
        fi
    fi
}

# Update all config files in sites-enabled
for file in /etc/nginx/sites-enabled/*; do
    update_conf "$file"
done

# Also check nginx.conf for global settings
MAIN_CONF="/etc/nginx/nginx.conf"
if [ -f "$MAIN_CONF" ]; then
    echo "Updating main config: $MAIN_CONF" | tee -a "$LOG_FILE"
    cp "$MAIN_CONF" "${MAIN_CONF}.bak_$(date +%s)"
    
    # Increase keepalive_timeout
    if grep -q "keepalive_timeout" "$MAIN_CONF"; then
        sed -i 's/keepalive_timeout.*$/keepalive_timeout 1800s;/' "$MAIN_CONF"
    fi
    
    # Increase client_max_body_size just in case
    if grep -q "client_max_body_size" "$MAIN_CONF"; then
        sed -i 's/client_max_body_size.*$/client_max_body_size 50M;/' "$MAIN_CONF"
    else
        sed -i '/http {/a \    client_max_body_size 50M;' "$MAIN_CONF"
    fi
fi

echo "Testing configuration..." | tee -a "$LOG_FILE"
nginx -t 2>> "$LOG_FILE"

if [ $? -eq 0 ]; then
    echo "Reloading Nginx..." | tee -a "$LOG_FILE"
    systemctl restart nginx
    echo "Nginx restarted." | tee -a "$LOG_FILE"
else
    echo "Config test failed!" | tee -a "$LOG_FILE"
fi
