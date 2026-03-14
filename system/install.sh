#!/bin/bash
# CDJ-100X Installation Script for Raspberry Pi OS Lite
# Run as root: sudo bash install.sh

set -e

echo "=== CDJ-100X Installation ==="

# --- System packages ---
echo "[1/7] Installing system packages..."
apt-get update
apt-get install -y \
    mixxx \
    python3-pip \
    python3-venv \
    python3-smbus \
    i2c-tools \
    git \
    libasound2-dev \
    libjack-dev

# --- Enable I2C, disable SPI and serial console ---
echo "[2/8] Configuring GPIO interfaces..."

# Enable I2C (needed for ADS1115 pitch fader)
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" >> /boot/config.txt
fi
if ! grep -q "^i2c-dev" /etc/modules; then
    echo "i2c-dev" >> /etc/modules
fi

# Disable SPI (GPIO 7/8 are SPI CE1/CE0 — can block boot if buttons pull them low)
# GPIO 9/10/11 are SPI MISO/MOSI/SCLK — used for Zip/Jet/Wah buttons instead
if ! grep -q "^dtparam=spi=off" /boot/config.txt; then
    echo "dtparam=spi=off" >> /boot/config.txt
fi

# Disable serial console (GPIO 14/15 are UART TX/RX — used for browse encoder)
if [ -f /boot/cmdline.txt ]; then
    sed -i 's/console=serial0,[0-9]* //g' /boot/cmdline.txt
    sed -i 's/console=ttyAMA0,[0-9]* //g' /boot/cmdline.txt
fi
systemctl disable serial-getty@ttyS0.service 2>/dev/null || true
systemctl disable serial-getty@ttyAMA0.service 2>/dev/null || true

# --- Install Python dependencies ---
echo "[3/7] Installing Python dependencies..."
INSTALL_DIR="/opt/cdj100x"
mkdir -p "$INSTALL_DIR"
cp -r bridge/ "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"

cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# --- Clone python-prodj-link ---
echo "[4/7] Setting up python-prodj-link..."
if [ ! -d "$INSTALL_DIR/python-prodj-link" ]; then
    git clone https://github.com/Lukaszm328/python-prodj-link.git "$INSTALL_DIR/python-prodj-link"
fi

# --- Install Mixxx skin and controller mapping ---
echo "[5/7] Installing Mixxx configuration..."
MIXXX_DIR="/home/pi/.mixxx"
mkdir -p "$MIXXX_DIR/controllers"
mkdir -p "$MIXXX_DIR/skins"

cp mixxx/controllers/CDJ100X.midi.xml "$MIXXX_DIR/controllers/"
cp mixxx/controllers/CDJ100X.js "$MIXXX_DIR/controllers/"
if [ -d "mixxx/skins/CDJ100X" ]; then
    cp -r mixxx/skins/CDJ100X "$MIXXX_DIR/skins/"
fi

chown -R pi:pi "$MIXXX_DIR"

# --- Install systemd services ---
echo "[6/7] Installing systemd services..."
cp system/cdj-bridge.service /etc/systemd/system/
cp system/mixxx.service /etc/systemd/system/
cp system/99-usb-mount.rules /etc/udev/rules.d/
cp system/cdj-link.conf /etc/

systemctl daemon-reload
systemctl enable cdj-bridge.service
systemctl enable mixxx.service
udevadm control --reload-rules

# --- Display configuration ---
echo "[7/7] Configuring display..."
if ! grep -q "hdmi_force_hotplug" /boot/config.txt; then
    cat >> /boot/config.txt << 'EOF'

# CDJ-100X Display Configuration (5" DSI capacitive touch)
gpu_mem=128
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt=800 480 60 6 0 0 0
EOF
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit /etc/cdj-link.conf to set unique player number (1-4)"
echo "  2. Reboot: sudo reboot"
echo "  3. Mixxx will auto-start in fullscreen"
echo "  4. Select 'CDJ100X' controller in Mixxx preferences"
echo ""
