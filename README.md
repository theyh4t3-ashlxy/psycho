# psycho

> how samsung's bsp team in suwon and qualcomm's trustzone architects in san diego created a literal psychological warfare simulator on a $1,300 phone, and how a 16-year-old developer beat it with an air conditioner and 20 lines of python.

---

### the $1,300 titanium brick

you buy a samsung galaxy s24 ultra. titanium chassis, snapdragon 8 gen 3, 2,600-nit panel, and qualcomm's "groundbreaking" 3d sonic gen 2 ultrasonic acoustic sensor. 

you wipe the phone, or you peel off a screen protector, or you just delete your fingerprints to re-enroll your thumbs.

you tap **register**.

the screen sits on **"getting ready..."** for a fraction of a second. you dare to bring your finger within three inches of the display, and the phone immediately shrieks:

```text
"make sure the fingerprint sensor is clean and dry"
```

or if you press it, it instantly self-destructs in 39 milliseconds with:

```text
"an error occurred with the fingerprint sensor. if this keeps happening, restart your phone."
(vendor error 1001)
```

you restart the phone. clean and dry.  
you wipe the cache partition. clean and dry.  
you wipe the glass with a microfiber cloth until you can see your ancestors in the reflection. clean and dry.  
you factory reset your phone. clean and dry.  

congratulations. your sensor isn't dirty. your sensor isn't wet. your phone has just been lobotomized by its own firmware.

---

### corporate brainrot vs reddit medieval voodoo

if you contact samsung support, their galaxy-brain engineers recommend their signature corporate lobotomy:

1. *"go to settings > biometrics > fingerprints."*
2. *"delete all registered fingerprints."*
3. *"restart the phone."*
4. *"if problem persists, visit an authorized service center for an amoled panel and motherboard replacement."*

their official advice is literally the exact trigger that bricks the phone. it's the software equivalent of cutting your own brake lines because your check engine light was on.

meanwhile, over on reddit, thousands of confused people are trading actual medieval plague doctor rituals:
- licking their thumbs like fried chicken before touching the screen to "increase conductivity" on an acoustic ultrasound scanner.
- smearing cetaphil lotion on the display like holy water.
- "tap the top left corner of the screen three times before tapping register, support told me this."
- paying $250 out of pocket to have ubreakifix rip off a perfectly functional 120hz display.

nobody in customer support has any idea what's happening. the repair techs don't have any idea what's happening. they just swap the motherboard and charge you for it.

---

### the crime scene: samsung hal meets qualcomm trustzone

the root cause is a catastrophic architectural circle-jerk between samsung's battery-saving obsession and qualcomm's paranoid security policy.

```
+-------------------------------------------------------------+
|  user deletes fingerprints / wipes device                   |
|  (m_enroll_template_count == 0)                             |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  samsung's hal invokes cbgePreForceStop()                   |
|  suwon decides that if you have 0 prints, you don't need    |
|  acoustic tracking anymore, saving 0.0001ma of battery.     |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  trustzone purges dynamic acoustic adaptation bins 1 to 7.  |
|  securefp.elf falls back to factory bin 0 (23.97°c).        |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  user taps enroll at normal room temperature (25°c-28°c).   |
|  thermal expansion shifts acoustic velocity through glass.  |
|  qfp_contamination_detection_check sees phase delay and     |
|  assumes the screen is caked in grease or acoustic spoof.   |
|  ABORTS IN 39MS: "MAKE SURE SENSOR IS CLEAN AND DRY" (1001) |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  because enrollment aborted, template count stays 0.        |
|  because template count stays 0, calibration stays dead.    |
|  INFINITE LIVELOCK ACHIEVED. THE SILICON COMMITS SUICIDE.   |
+-------------------------------------------------------------+
```

#### 1. samsung's microamp lobotomy: `cbgePreForceStop`
inside samsung's proprietary biometric hal (`/vendor/lib64/libsfp_sensor.so`), when `m_enroll_template_count == 0`, suwon's code calls:
```c
// libsfp_sensor.so @ offset 0x784a0
void cbgePreForceStop() {
    m_bge_mode = 0; // stop continuous background calibration
    // purge runtime acoustic impedance adaptation bins 1-7
}
```
the nanosecond your enrolled print count hits zero, samsung kills continuous background estimation. all dynamic acoustic adaptation tables that compensate for room temperature are flushed down the toilet.

#### 2. qualcomm's trustzone paranoia: `CHECK_CD_BEFORE_ENROLL`
qualcomm's snapdragon 8 gen 3 trustlet (`securefp.elf`) is certified to the teeth. when enrollment stage 1 starts, it doesn't trust runtime data. it executes:
```c
// securefp.elf @ offset 0x4c8eee
qfp_contamination_detection_check()
```
it shoots an ultrasonic acoustic ping through the amoled glass and measures the return echo against factory baseline `bin 0`, which was calibrated in a sterile cleanroom in gumi at exactly **23.97°c**.

the speed of sound through amoled glass changes with temperature ($c \propto \sqrt{T}$, roughly $1.5\,\text{m/s}$ per degree celsius):
- if your phone is sitting in your bedroom at **25.5°c**, the delta is $+1.53^\circ\text{c}$.
- qualcomm's trustlet sees the echo delay, assumes someone slapped a layer of gelatin or silicone over the glass to spoof your identity, and aborts with error 48 (`0x30` -> vendor 1001).
- the samsung ui displays: *"make sure the fingerprint sensor is clean and dry"* or gets stuck on *"getting ready..."* before crashing.

you can't enroll without background calibration. you can't get background calibration without enrolling. an absolute masterclass in software engineering.

#### 3. the dew-point trap
if you figure out the phone is too warm and stick it in front of an air conditioner until it's freezing, you walk right into elementary school physics:
the battery drops to 17°c. the moment warm ambient room air touches the cold titanium glass, microscopic condensation forms on the display. ultrasound waves hit the liquid film and scatter like a disco ball. 
the sensor screams *"make sure the fingerprint sensor is clean and dry"* again. this time for real.

---

### the cure: the 0.9°c goldilocks window

to break the livelock, the glass must hit a razor-thin window that satisfies two contradictory physical constraints:
1. **$T \ge 23.40^\circ\text{c}$**: warm enough to be above the room's dew point so zero condensation forms on the glass.
2. **$T \le 24.30^\circ\text{c}$**: cold enough to be within qualcomm's $\pm 0.5^\circ\text{c}$ tolerance from factory `bin 0` (`23.97°c`).

you have a **0.9°c strike window** (roughly 60 seconds as the chassis warms back up) to enroll finger 1.

the nanosecond finger 1 hits 100%, `m_enroll_template_count` becomes 1. `cbgePreForceStop` disengages, background acoustic estimation wakes up, and the sensor will now unlock your phone across any temperature from 0°c to 50°c.

---

### how to run psycho

zero root. zero knox trips. stock firmware.

```bash
# 1. clone the repo
git clone https://github.com/theyh4t3-ashlxy/psycho.git
cd psycho

# 2. connect phone via adb (usb or wireless)
adb devices

# 3. run the recovery script
python3 recover.py
```

follow the terminal:
1. cool your phone down (ac vent or ice pack wrapped in a cloth) until battery is under 22°c.
2. wipe the screen bone-dry with a microfiber shirt or cloth. no moisture.
3. put the phone down at room temp.
4. `recover.py` polls `/sys/class/thermal/thermal_zone56/temp` in real time. the second the chassis warms into the `23.40°c`–`24.30°c` goldilocks band, it rings the terminal bell and fires the enrollment intent.
5. slam your thumb onto the scanner and complete registration to 100%. the livelock is permanently dead.

---

### credits

discovered, decompiled, and documented by **ashley** (16) & **antigravity**.  
built out of pure unapologetic spite for samsung mobile's bsp department in suwon and qualcomm's trustzone team in san diego.

license: mit / spite-ware. do whatever you want with it, just don't pay samsung $250 for a screen swap.
