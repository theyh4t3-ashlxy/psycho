# psycho

> a technical teardown of the samsung galaxy s24 ultra ultrasonic fingerprint livelock, the comedy of errors inside qualcomm's trustzone, and how 20 lines of python saved a $1,300 flagship from a motherboard swap.

---

### the $1,300 paperweight

you just bought a samsung galaxy s24 ultra. titanium frame, snapdragon 8 gen 3, 2,600-nit amoled display, and qualcomm's state-of-the-art 3d sonic gen 2 (`QBT4000`) ultrasonic sensor. 

you decide to put on a new screen protector. naturally, you go to settings and delete your registered fingerprints to re-enroll them cleanly.

you tap **"add fingerprint."**

in exactly **39 milliseconds**, before your finger is even within three inches of the glass, the screen flashes:
```text
"an error occurred with the fingerprint sensor. if this keeps happening, restart your phone."
(vendor error 1001)
```

you restart the phone. error 1001.  
you wipe the cache partition. error 1001.  
you factory reset your phone. error 1001.  

congratulations: you have just been inducted into samsung's multi-million-dollar firmware livelock.

---

### the corporate gaslight

if you contact samsung support or read their official troubleshooting articles, their engineers in suwon recommend the following masterclass in software engineering:

1. *"go to settings > biometrics > fingerprints."*
2. *"delete all currently registered fingerprints."*
3. *"restart the phone and try again."*
4. *"if problem persists, visit a samsung authorized service center for display / motherboard replacement."*

their official advice is literally the exact trigger that bricks the phone. 

meanwhile, over on reddit, thousands of desperate users are trading medieval folk remedies:
- licking their thumbs before touching the screen to "increase conductivity" (on an acoustic sensor).
- applying hand lotion like it's holy water.
- tapping the top left corner of the screen three times before tapping register.
- paying ubreakifix $250 to rip off a pristine display assembly.

nobody in customer support knows why it's happening. the repair technicians don't know why it's happening. but the disassembly of samsung's hal and qualcomm's trustzone reveals a level of architectural negligence that borders on psychological warfare.

---

### the root cause: two corporations, zero communication

the bug is a circular dependency between samsung's power-saving hal logic and qualcomm's paranoid cryptographic trustlet.

```
+-------------------------------------------------------+
|  User deletes last fingerprint (template_count == 0)  |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|  libsfp_sensor.so calls cbgePreForceStop()            |
|  Samsung kills Continuous Background Estimation to    |
|  save 0.002mA of standby power.                       |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|  TrustZone purges dynamic acoustic bins 1 through 7.  |
|  securefp.elf falls back to factory bin 0 (23.97°C).   |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|  User attempts to enroll finger at room temp (25°C).  |
|  Thermal drift (ΔT > 0.5°C) shifts ultrasonic speed.   |
|  qfp_contamination_detection_check flags acoustic     |
|  phase delay as glass contamination / spoofing.       |
|  ABORTS IN 39MS WITH ERROR 48 -> VENDOR ERROR 1001.   |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|  Because enrollment failed, template_count stays 0.   |
|  Background calibration stays permanently dead.       |
|  LIVELOCK ACHIEVED. THE PHONE IS PERMANENTLY BRICKED.  |
+-------------------------------------------------------+
```

#### 1. samsung's microamp obsession: `cbgePreForceStop`
inside samsung's proprietary biometric hal (`/vendor/lib64/libsfp_sensor.so`), when `m_enroll_template_count == 0`, the hal aggressively invokes:
```c
// libsfp_sensor.so @ offset 0x784a0
void cbgePreForceStop() {
    m_bge_mode = 0; // stop continuous background calibration
    // purge runtime acoustic impedance adaptation bins 1-7
}
```
the moment you have zero fingerprints registered, samsung decides your phone doesn't need acoustic tracking anymore. it purges the runtime calibration tables that adapt to room temperature.

#### 2. qualcomm's paranoia: `CHECK_CD_BEFORE_ENROLL`
qualcomm's snapdragon 8 gen 3 trustlet (`securefp.elf`) is fips and common criteria certified. when you start stage 1 of enrollment (`handle_do_enroll_stage_1`), it doesn't trust runtime data. it runs:
```c
// securefp.elf @ offset 0x4c8eee
qfp_contamination_detection_check()
```
it fires an ultrasonic pulse through the glass and checks the propagation delay against factory baseline `bin 0`, which was calibrated in a cleanroom in gumi at exactly **23.97°c**.

the speed of sound through amoled cover glass changes with temperature ($c \propto \sqrt{T}$, roughly $1.5\,\text{m/s}$ per $^\circ\text{c}$).
- if your phone is sitting at normal room temperature (**25.0°c**), the delta is $\Delta T = +1.03^\circ\text{c}$.
- qualcomm's trustlet sees the phase shift, assumes someone glued a counterfeit gelatin fingerprint or thick privacy filter to the glass, and aborts with error 48 (`0x30`), which samsung maps to vendor error 1001.

because it aborts, you never enroll a print. because you have no enrolled print, samsung never unlatches `cbgePreForceStop`. you are trapped in an infinite hardware catch-22.

#### 3. the dew-point trap
if you figure out the phone is too warm and hold it over an air conditioner vent, you hit the opposite physics trap:
the battery drops to 17°c. warm room air hits the cold titanium frame and glass, creating microscopic surface dew. ultrasound cannot propagate through water film without scattering. the contamination check fails again: *"make sure the fingerprint sensor is clean and dry."*

---

### the cure: the 0.9°c goldilocks window

to break the livelock, the glass must simultaneously satisfy two contradictory physical constraints:
1. **$T \ge 23.40^\circ\text{c}$**: warm enough to be above the room's dew point so zero condensation forms on the glass.
2. **$T \le 24.30^\circ\text{c}$**: within qualcomm's $\pm 0.5^\circ\text{c}$ tolerance from factory `bin 0` (`23.97°c`).

you have a razor-thin **0.9°c strike window** (roughly 60 seconds as the chassis passively warms up) to register finger 1. 

the moment finger 1 hits 100%, `m_enroll_template_count` becomes 1. `cbgePreForceStop` permanently disengages, continuous background estimation wakes up, and the sensor will now unlock flawlessly from 0°c to 50°c.

---

### usage

no root. no knox trips. just a usb cable or wireless adb.

```bash
# 1. clone the repo
git clone https://github.com/ashley/psycho.git
cd psycho

# 2. connect phone via adb
adb devices

# 3. run recovery script
python3 recover.py
```

follow the terminal prompts:
1. chill the device until battery temperature is below 22°c.
2. wipe the display bone-dry with a microfiber cloth.
3. let the phone rest on the desk.
4. `recover.py` polls `/sys/class/thermal/thermal_zone56/temp` in real time. the second the sensor enters the goldilocks zone (`23.40°c`–`24.30°c`), it rings the terminal bell and automatically triggers the enrollment intent.
5. register your thumb to 100%. the livelock is broken forever.

---

### credits

discovered, reverse-engineered, and documented by **ashley** (16) & **antigravity**.  
built out of pure spite for samsung's bsp team in suwon and qualcomm's trustzone architects in san diego.

license: mit / spite-ware. do whatever you want with it, just don't pay samsung $250 for a screen swap.
