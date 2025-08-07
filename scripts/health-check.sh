#!/bin/bash
# TailSentry Health Monitoring Script
# Run this script periodically to monitor TailSentry health

set -euo pipefail

# Configuration
TAILSENTRY_URL="${TAILSENTRY_URL:-http://localhost:8080}"
LOG_FILE="${LOG_FILE:-/var/log/tailsentry-health.log}"
ALERT_EMAIL="${ALERT_EMAIL:-admin@example.com}"
WEBHOOK_URL="${WEBHOOK_URL:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_service() {
    log "🔍 Checking TailSentry health..."
    
    # Check HTTP health endpoint
    if ! response=$(curl -s -f -m 10 "$TAILSENTRY_URL/health" 2>&1); then
        log "❌ HTTP health check failed: $response"
        return 1
    fi
    
    # Parse JSON response
    if ! echo "$response" | jq -e '.status == "ok"' >/dev/null 2>&1; then
        log "❌ Health endpoint returned non-OK status: $response"
        return 1
    fi
    
    log "✅ TailSentry HTTP health check passed"
    return 0
}

check_tailscale() {
    log "🔍 Checking Tailscale connectivity..."
    
    if ! tailscale status >/dev/null 2>&1; then
        log "❌ Tailscale is not responding"
        return 1
    fi
    
    log "✅ Tailscale connectivity check passed"
    return 0
}

check_disk_space() {
    log "🔍 Checking disk space..."
    
    # Check if disk usage is above 90%
    disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -gt 90 ]; then
        log "⚠️  Disk usage is at ${disk_usage}% - running low on space"
        return 1
    elif [ "$disk_usage" -gt 80 ]; then
        log "⚠️  Disk usage is at ${disk_usage}% - monitor closely"
    else
        log "✅ Disk usage is at ${disk_usage}% - healthy"
    fi
    
    return 0
}

check_memory() {
    log "🔍 Checking memory usage..."
    
    # Get memory usage percentage
    mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [ "$mem_usage" -gt 90 ]; then
        log "⚠️  Memory usage is at ${mem_usage}% - critically high"
        return 1
    elif [ "$mem_usage" -gt 80 ]; then
        log "⚠️  Memory usage is at ${mem_usage}% - monitor closely"
    else
        log "✅ Memory usage is at ${mem_usage}% - healthy"
    fi
    
    return 0
}

send_alert() {
    local message="$1"
    log "🚨 ALERT: $message"
    
    # Send email if configured
    if command -v mail >/dev/null 2>&1 && [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "TailSentry Alert" "$ALERT_EMAIL"
        log "📧 Alert email sent to $ALERT_EMAIL"
    fi
    
    # Send webhook if configured
    if [ -n "$WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"TailSentry Alert: $message\"}" \
            "$WEBHOOK_URL" || log "Failed to send webhook alert"
    fi
}

restart_service() {
    log "🔄 Attempting to restart TailSentry service..."
    
    if systemctl is-active --quiet tailsentry.service; then
        sudo systemctl restart tailsentry.service
        sleep 10
        if systemctl is-active --quiet tailsentry.service; then
            log "✅ Service restarted successfully"
            return 0
        else
            log "❌ Service failed to restart"
            return 1
        fi
    else
        log "❌ Service is not active, attempting to start..."
        sudo systemctl start tailsentry.service
        sleep 10
        if systemctl is-active --quiet tailsentry.service; then
            log "✅ Service started successfully"
            return 0
        else
            log "❌ Service failed to start"
            return 1
        fi
    fi
}

main() {
    log "📊 Starting TailSentry health check..."
    
    local failed_checks=0
    local total_checks=0
    
    # Run all health checks
    checks=(
        "check_service"
        "check_tailscale" 
        "check_disk_space"
        "check_memory"
    )
    
    for check in "${checks[@]}"; do
        total_checks=$((total_checks + 1))
        if ! $check; then
            failed_checks=$((failed_checks + 1))
        fi
    done
    
    # Determine overall health
    if [ $failed_checks -eq 0 ]; then
        log "✅ All health checks passed ($total_checks/$total_checks)"
    elif [ $failed_checks -eq 1 ] && [[ $(check_service; echo $?) -ne 0 ]]; then
        # If only the service check failed, try to restart
        if restart_service && check_service; then
            log "✅ Service recovered after restart"
        else
            send_alert "TailSentry service failed and could not be restarted"
        fi
    else
        send_alert "TailSentry health check failed: $failed_checks/$total_checks checks failed"
    fi
    
    log "📊 Health check completed"
}

# Run main function
main "$@"
