# CDJ-100X Installation Guide

Complete step-by-step guide to install the CDJ-100X software on a Raspberry Pi 3B+.

## Prerequisites

Before starting, make sure you have:

- Raspberry Pi 3B+ with all hardware wired (buttons, encoders, LEDs, pitch fader, ADS1115)
- 5" DSI capacitive touch display connected
- MicroSD card (16GB minimum, 32GB recommended)
- Ethernet cable (for Pro DJ Link between two units)
- A PC with SD card reader
- WiFi network (for initial setup over SSH)

---

## Step 1: Flash Raspberry Pi OS

1. Download and install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your PC
2. Insert the MicroSD card into your PC
3. Open Raspberry Pi Imager:
   - **Device**: Raspberry Pi 3
   - **OS**: Raspberry Pi OS Lite (64-bit) — no desktop environment needed
   - **Storage**: Select your SD card
4. Click the **gear icon** (or Edit Settings) before flashing and configure:
   - **Hostname**: `cdj100x-1` (use `cdj100x-2` for the second unit)
   - **Enable SSH**: Yes, use password authentication
   - **Username**: `pi`
   - **Password**: choose a password
   - **WiFi**: enter your network name and password (needed for initial setup)
   - **Locale**: set your timezone and keyboard layout
5. Click **Write** and wait for flashing to complete

---

## Step 2: First Boot

1. Insert the SD card into the Raspberry Pi
2. Connect the 5" DSI display
3. Power on the Pi
4. Wait about 60 seconds for first boot to complete

### Connect via SSH

From your PC, open a terminal:

```bash
# Connect using the hostname you set
ssh pi@cdj100x-1.local

# Or find the Pi's IP from your router and use that
ssh pi@192.168.1.xxx
```

Enter the password you set in Step 1.

---

## Step 3: Clone and Install

```bash
# Update the system first
sudo apt-get update && sudo apt-get upgrade -y

# Clone the CDJ100X-rework repository
cd ~
git clone https://github.com/Lukaszm328/CDJ100X-rework.git

# Enter the project folder
cd CDJ100X-rework

# Run the installation script
sudo bash system/install.sh
```

### What the Install Script Does

The script runs automatically and handles everything:

| Step | What it does |
|------|-------------|
| 1 | Installs Mixxx, Python 3, pip, I2C tools, audio libraries |
| 2 | Enables I2C interface in `/boot/config.txt` |
| 3 | Creates `/opt/cdj100x/` with Python virtual environment and all dependencies |
| 4 | Clones python-prodj-link for Pro DJ Link support |
| 5 | Copies CDJ100X skin and controller mapping to `~/.mixxx/` |
| 6 | Installs and enables systemd services (cdj-bridge + Mixxx auto-start) |
| 7 | Configures display output for 800x480 resolution |

The installation takes about 10-15 minutes depending on your internet speed.

---

## Step 4: Configure Player Number

Each unit on the Pro DJ Link network needs a unique player number (1-4).

```bash
sudo nano /etc/cdj-link.conf
```

Edit the file:

```ini
[player]
# Set to 1 for the first unit, 2 for the second, etc.
number = 1
name = CDJ-100X

[network]
interface = eth0
addressing = link-local
```

Save with `Ctrl+O`, `Enter`, then exit with `Ctrl+X`.

---

## Step 5: Reboot

```bash
sudo reboot
```

After reboot:
- The **cdj-bridge** service starts first (reads GPIO, opens MIDI ports)
- **Mixxx** starts in fullscreen mode automatically

---

## Step 6: Configure Mixxx (First Time Only)

On the first launch, you need to tell Mixxx to use the CDJ100X controller and skin:

1. Touch the screen or use the browse encoder to open Mixxx
2. Go to **Preferences** (Options → Preferences, or `Ctrl+,`)
3. **Sound Hardware**:
   - Set your audio output (HDMI, 3.5mm jack, or USB audio)
4. **Controllers**:
   - Find **CDJ100X** in the list
   - Make sure it is **Enabled**
5. **Interface**:
   - Select **CDJ100X** as the skin
6. Click **OK** and restart Mixxx

After this, Mixxx will remember your settings on every boot.

---

## Step 7: Set Up the Second Unit

Repeat **Steps 1-6** on a second SD card for the second CDJ-100X unit, with these differences:

- **Step 1**: Set hostname to `cdj100x-2`
- **Step 4**: Set player number to `2`

### Linking Two Units

Connect both units with a standard RJ45 Ethernet cable:

```
CDJ-100X (Player 1) ──── RJ45 cable ──── CDJ-100X (Player 2)
```

They will auto-discover each other using link-local addressing (169.254.x.x). No switch or router needed for a direct connection.

### Linking with Real Pioneer Gear

Connect all devices to an Ethernet switch:

```
Ethernet Switch
├── CDJ-100X  (Player 1) ── DJM Channel 1
├── CDJ-100X  (Player 2) ── DJM Channel 2
├── CDJ-2000  (Player 3) ── DJM Channel 3
└── DJM-900NXS2 (Mixer)
```

---

## Troubleshooting

### Check Service Status

```bash
# Check if the bridge is running
sudo systemctl status cdj-bridge

# Check if Mixxx is running
sudo systemctl status mixxx
```

### View Live Logs

```bash
# Bridge logs (GPIO, MIDI, Pro DJ Link)
sudo journalctl -u cdj-bridge -f

# Mixxx logs
sudo journalctl -u mixxx -f

# Both together
sudo journalctl -u cdj-bridge -u mixxx -f
```

### Test the Bridge Manually

Stop the service and run the bridge by hand to see full debug output:

```bash
# Stop the auto-started service
sudo systemctl stop cdj-bridge

# Run manually with debug logging
cd /opt/cdj100x
source venv/bin/activate
python3 -m bridge.main --log-level DEBUG

# Run without GPIO (test on PC or Pi without wiring)
python3 -m bridge.main --no-gpio --log-level DEBUG

# Run without Pro DJ Link (test GPIO only)
python3 -m bridge.main --no-prodj --log-level DEBUG
```

### Verify I2C (Pitch Fader)

```bash
# Check if ADS1115 is detected on the I2C bus
i2cdetect -y 1
```

Expected output — `48` should appear in the grid:

```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

If `48` does not appear:
- Check SDA (GPIO 2) and SCL (GPIO 3) wiring to ADS1115
- Check ADS1115 VDD is connected to 3.3V or 5V
- Check ADDR pin on ADS1115 is connected to GND (for address 0x48)

### Test Individual Buttons

```bash
python3 -c "
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

buttons = {
    20: 'Play/Pause',
    21: 'Cue',
     4: 'Next Track',
    17: 'Back',
    27: 'Search Forward',
    22: 'Search Backward',
    10: 'Jet',
     9: 'Zip',
    11: 'Wah',
    24: 'Hold/Mode',
     5: 'Auto Cue',
     6: 'Remove Disc',
    13: 'Tempo Master',
    12: 'Browse Encoder BTN',
}

for pin in buttons:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print('Press buttons to test (Ctrl+C to exit)...')
print()

try:
    while True:
        for pin, name in buttons.items():
            if GPIO.input(pin) == GPIO.LOW:
                print(f'  PRESSED: {name} (GPIO {pin})')
        time.sleep(0.1)
except KeyboardInterrupt:
    GPIO.cleanup()
    print('Done.')
"
```

### Test Jog Wheel Encoder

```bash
python3 -c "
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # CLK
GPIO.setup(25, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # DT

last_clk = GPIO.input(18)
count = 0

print('Turn jog wheel (Ctrl+C to exit)...')

try:
    while True:
        clk = GPIO.input(18)
        if last_clk == 1 and clk == 0:
            dt = GPIO.input(25)
            if dt == 0:
                count += 1
                print(f'  Clockwise     (count: {count})')
            else:
                count -= 1
                print(f'  Counter-CW    (count: {count})')
        last_clk = clk
        time.sleep(0.001)
except KeyboardInterrupt:
    GPIO.cleanup()
    print('Done.')
"
```

### Test LEDs

```bash
python3 -c "
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(19, GPIO.OUT)  # Play LED
GPIO.setup(26, GPIO.OUT)  # Cue LED

print('Testing LEDs...')

# LEDs are active LOW
print('  Play LED ON')
GPIO.output(19, GPIO.LOW)
time.sleep(1)
GPIO.output(19, GPIO.HIGH)

print('  Cue LED ON')
GPIO.output(26, GPIO.LOW)
time.sleep(1)
GPIO.output(26, GPIO.HIGH)

print('  Both LEDs blinking...')
for i in range(6):
    GPIO.output(19, GPIO.LOW)
    GPIO.output(26, GPIO.LOW)
    time.sleep(0.3)
    GPIO.output(19, GPIO.HIGH)
    GPIO.output(26, GPIO.HIGH)
    time.sleep(0.3)

GPIO.cleanup()
print('Done.')
"
```

### Test Pro DJ Link Discovery

Connect two units via Ethernet, then on either unit:

```bash
cd /opt/cdj100x
source venv/bin/activate

python3 -c "
from prodj.core.prodj import ProDj
import time

p = ProDj()
p.set_client_keepalive_callback(
    lambda n: print(f'  Discovered Player {n}')
)
p.start()
p.vcdj_set_player_number(5)  # Use 5 to avoid conflicts
p.vcdj_enable()

print('Listening for Pro DJ Link devices (Ctrl+C to exit)...')
print()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    p.stop()
    print('Done.')
"
```

### Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| No display output | Wrong display config | Check `/boot/config.txt` for `hdmi_cvt=800 480 60` |
| Buttons not responding | Wrong GPIO wiring | Run the button test script above |
| Pitch fader not working | I2C not enabled | Run `sudo raspi-config` → Interface → Enable I2C |
| No sound | Wrong audio output | Check Mixxx Preferences → Sound Hardware |
| Bridge won't start | Missing dependencies | Run `cd /opt/cdj100x && source venv/bin/activate && pip install -r requirements.txt` |
| Pro DJ Link not connecting | Firewall blocking UDP | Run `sudo ufw allow 50000:50002/udp` |
| Units don't discover each other | Wrong IP config | Check both have link-local IPs: `ip addr show eth0` |
| Mixxx crashes on start | GPU memory too low | Set `gpu_mem=128` in `/boot/config.txt` |

---

## Updating

To update the CDJ-100X software after a new release:

```bash
cd ~/CDJ100X-rework
git pull

# Re-run the installer to apply changes
sudo bash system/install.sh

sudo reboot
```

---

## Uninstalling

```bash
# Stop and disable services
sudo systemctl stop cdj-bridge mixxx
sudo systemctl disable cdj-bridge mixxx

# Remove installed files
sudo rm -rf /opt/cdj100x
sudo rm /etc/systemd/system/cdj-bridge.service
sudo rm /etc/systemd/system/mixxx.service
sudo rm /etc/udev/rules.d/99-usb-mount.rules
sudo rm /etc/cdj-link.conf

# Remove Mixxx config
rm -rf ~/.mixxx/controllers/CDJ100X.*
rm -rf ~/.mixxx/skins/CDJ100X

sudo systemctl daemon-reload
```
