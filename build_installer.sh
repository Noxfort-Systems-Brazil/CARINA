#!/bin/bash
# CARINA Installer Build Automation (Full Pipeline)
# This script builds the PyInstaller executable using a sterile Docker environment,
# extracts the resulting 'dist/carina' folder, validates it, and generates the .deb installer.

set -e  # Exit on any error

echo "==========================================================="
echo "  CARINA - Full Installer Build Pipeline"
echo "==========================================================="

# 1. Build the Docker Image (This runs PyInstaller inside the sterile PyTorch Ubuntu environment)
echo "[1/5] Building Docker Image (carina-builder)..."
echo "      This will take a while as it downloads dependencies and compiles."
docker build -t carina-builder .

# Check if build was successful
if [ $? -ne 0 ]; then
    echo "ERROR: Docker build failed. Please check the logs above."
    exit 1
fi

# 2. Create a temporary container to extract the files
echo "[2/5] Creating temporary container to extract build artifacts..."
# Remove any old temp container
docker rm -f carina_temp 2>/dev/null || true
docker create --name carina_temp carina-builder

# 3. Copy the 'dist/carina' folder from the container to the host
echo "[3/5] Extracting 'dist/carina' to host..."
# Remove any old dist folder
rm -rf ./dist
mkdir -p ./dist
docker cp carina_temp:/app/dist/carina ./dist/carina

# Clean up the temporary container immediately
docker rm carina_temp

# 4. Quick sanity check — verify the binary can at least start importing
echo "[4/5] Validating compiled binary..."
if [ ! -f "./dist/carina/carina" ]; then
    echo "ERROR: Binary './dist/carina/carina' not found after extraction!"
    exit 1
fi

echo "      Binary exists: $(file ./dist/carina/carina)"

# Check critical modules are present in _internal
MISSING_MODULES=""
for mod in grpc flet paho prometheus_client psycopg2; do
    if [ ! -d "./dist/carina/_internal/$mod" ] && ! ls ./dist/carina/_internal/${mod}* 1>/dev/null 2>&1; then
        MISSING_MODULES="$MISSING_MODULES $mod"
    fi
done

if [ -n "$MISSING_MODULES" ]; then
    echo "WARNING: The following modules may be missing from _internal/:$MISSING_MODULES"
    echo "         The binary may crash at runtime. Consider updating carina.spec."
else
    echo "      All critical modules found in _internal/. ✓"
fi

# 5. Build the .deb package automatically
echo "[5/5] Building .deb package..."
bash ./package_deb.sh

echo "==========================================================="
echo "  FULL PIPELINE COMPLETE!"
echo "  Install with: sudo dpkg -i ./dist/carina_1.0.0_amd64.deb"
echo "  Then launch CARINA from your application menu."
echo "==========================================================="
