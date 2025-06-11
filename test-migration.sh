#!/bin/bash
# Test script to validate DHI migrations

echo "Testing DHI Migration Tool..."

# Test cases directory
TEST_DIR="examples"
RESULTS_DIR="test-results"
mkdir -p $RESULTS_DIR

# Test each example
for app_dir in $TEST_DIR/*/; do
    app_name=$(basename "$app_dir")
    echo "Testing $app_name..."
    
    # Run migration
    python3 ../../dhi_migrate.py \
        "$app_dir/Dockerfile.original" \
        "myorg/dhi-${app_name%%'-app'}:latest-dev" \
        --output "$RESULTS_DIR/${app_name}.dockerfile" \
        --verbose > "$RESULTS_DIR/${app_name}.log" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ $app_name migration successful"
    else
        echo "❌ $app_name migration failed"
        cat "$RESULTS_DIR/${app_name}.log"
    fi
done

echo "Migration tests complete. Results in $RESULTS_DIR/"