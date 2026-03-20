#!/bin/bash
# CARINA Automatic DEB Packager
# This script takes the 'dist/carina' compiled folder and generates a professional .deb installer.

echo "==========================================================="
echo "  CARINA - Automatic .deb Packager"
echo "==========================================================="

VERSION="1.0.0"
PACKAGE_NAME="carina_${VERSION}_amd64"
BUILD_DIR="./dist/${PACKAGE_NAME}"

# 1. Verify existence of the PyInstaller output
if [ ! -d "./dist/carina" ]; then
    echo "ERROR: './dist/carina' not found! Make sure you ran 'build_installer.sh' first."
    exit 1
fi

echo "[1/4] Preparing DEB directory structure..."
# Clean previous builds
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/opt"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${BUILD_DIR}/DEBIAN"

# 2. Copy the files into the structure
echo "[2/4] Copying files to package directory..."
# The main binary folder
cp -r ./dist/carina "${BUILD_DIR}/opt/carina"

# The Desktop shortcut
cp ./carina.desktop "${BUILD_DIR}/usr/share/applications/"

# The Icon
cp ./ui/assets/images/logo.png "${BUILD_DIR}/usr/share/icons/hicolor/256x256/apps/carina.png"

# 3. Create the DEBIAN/control and postinst files
echo "[3/4] Generating DEBIAN control and post-installation files..."

cat <<EOF > "${BUILD_DIR}/DEBIAN/control"
Package: carina
Version: ${VERSION}
Architecture: amd64
Maintainer: Gabriel Moraes <your-email@example.com>
Description: Controlled Artificial Road-traffic Intelligence Network Architecture
 A complete AI ecosystem for real-time, adaptive control of urban traffic light networks.
EOF

cat <<EOF > "${BUILD_DIR}/DEBIAN/postinst"
#!/bin/bash
chmod +x /opt/carina/carina
# Update the desktop database so the icon appears immediately
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications/
fi
# Update icon cache
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor
fi
exit 0
EOF

chmod 755 "${BUILD_DIR}/DEBIAN/postinst"
# Important Debian policy: DEBIAN/control must have proper permissions
chmod 644 "${BUILD_DIR}/DEBIAN/control"

# 4. Build the .deb file
echo "[4/4] Building the .deb package..."
dpkg-deb --build "${BUILD_DIR}"

if [ $? -eq 0 ]; then
    echo "==========================================================="
    echo "  SUCCESS!"
    echo "  Your installer is ready at: ./dist/${PACKAGE_NAME}.deb"
    echo "  You can install it with: sudo dpkg -i ./dist/${PACKAGE_NAME}.deb"
    echo "==========================================================="
else
    echo "ERROR: Failed to build the DEB package."
fi
