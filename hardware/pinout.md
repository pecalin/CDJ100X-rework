# CDJ-100X GPIO Pinout

All connections use BCM pin numbering on Raspberry Pi 3B+.
Buttons use internal pull-up resistors (active LOW).
LEDs are active LOW (GPIO LOW = LED ON).

## Buttons (Input, Pull-Up)

| Function         | GPIO | CDJ-100 Wire  | MIDI Note |
|------------------|------|----------------|-----------|
| Play/Pause       |  20  | Play button    | 0x3C      |
| Cue              |  21  | Cue button     | 0x3D      |
| Next Track       |   4  | Track >> button| 0x49      |
| Back/Prev        |  17  | Track << button| 0x3F      |
| Search Forward   |  27  | Search >> button| 0x43     |
| Search Backward  |  22  | Search << button| 0x42     |
| Jet (EFX 1)      |  10  | Jet button     | 0x44      |
| Zip (EFX 2)      |   9  | Zip button     | 0x45      |
| Wah (EFX 3)      |  11  | Wah button     | 0x46      |
| Hold/Mode        |  24  | Hold button    | 0x48      |
| Auto Cue (Shift) |   5  | Time/Auto Cue  | 0x47      |
| Remove Disc      |   6  | Eject button   | 0x4A      |
| Tempo Master     |  13  | Master Tempo   | 0x3E      |

## LEDs (Output, Active Low)

| Function   | GPIO | CDJ-100 Wire |
|------------|------|--------------|
| Play LED   |  19  | Play LED     |
| Cue LED    |  26  | Cue LED      |

## Jog Wheel Encoder

| Signal | GPIO | Description           |
|--------|------|-----------------------|
| CLK    |  18  | Encoder clock phase   |
| DT     |  25  | Encoder data phase    |

## Browse Encoder

| Signal | GPIO | Description           |
|--------|------|-----------------------|
| CLK    |  15  | Encoder clock phase   |
| DT     |  14  | Encoder data phase    |
| Button |   7  | Encoder push button   |

## Pitch Fader (I2C via ADS1115)

| Signal      | Connection         | Description              |
|-------------|--------------------|--------------------------|
| I2C SDA     | GPIO 2 (I2C1 SDA)  | I2C data line            |
| I2C SCL     | GPIO 3 (I2C1 SCL)  | I2C clock line           |
| ADS1115 A0  | Pitch fader wiper  | Analog input             |
| ADS1115 VDD | 3.3V or 5V         | Power supply             |
| ADS1115 GND | Ground             | Ground                   |
| ADS Address | 0x48               | I2C address (ADDR→GND)   |

## Raspberry Pi 3B+ GPIO Header Reference

```
                    3V3  (1)  (2)  5V
          I2C SDA   GP2  (3)  (4)  5V
          I2C SCL   GP3  (5)  (6)  GND
  Browse Enc BTN    GP4  (7)  (8)  GP14  Browse Enc DT
                    GND  (9)  (10) GP15  Browse Enc CLK
        Auto Cue    GP17 (11) (12) GP18  Jog Enc CLK
      Remove Disc   GP27 (13) (14) GND
        Search +    GP22 (15) (16) GP23  (ADS Alert)
                    3V3  (17) (18) GP24  Hold/Mode
            Zip     GP10 (19) (20) GND
            Jet     GP9  (21) (22) GP25  Jog Enc DT
            Wah     GP11 (23) (24) GP8   (unused)
                    GND  (25) (26) GP7   Browse Enc BTN
                    GP0  (27) (28) GP1
      Next Track    GP5  (29) (30) GND
       Back/Prev    GP6  (31) (32) GP12  (unused)
     Tempo Master   GP13 (33) (34) GND
      Play LED      GP19 (35) (36) GP16  (unused)
       Cue LED      GP26 (37) (38) GP20  Play/Pause
                    GND  (39) (40) GP21  Cue
```

Note: Pin numbering above shows physical pin (n) and BCM GPIO number.
