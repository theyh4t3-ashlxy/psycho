oh, boy.. you buy a samsung galaxy s24 ultra. "it's a cool phone", you say. you even glaze the fingerprint sensor (which you repeat the echo chamber's specs. it's a "qualcomm 3d sonic" sensor. who cares?) 

so:

you get the phone out. you get to the fingerprint screen. you think it's going to be easy.

in the setup wizard, it greets you with:

```text
"when you finish up setting your phone, you can try again in settings. make sure the fingerprint sensor is clean and dry."
```

you just shrug it because it's just a software bug, or you wipe the phone, like a human being. or you peel off a screen protector, if the previous owner had one, or you just delete your fingerprints to re-enroll them cleanly. whatever.

so you finish setup, go into settings, and try to register a thumb. depending on how you hold your finger, the hardware abstraction layer gives you two distinct flavors of software lobotomy:

1. **if you don't press firmly:**  
   the second you tap register, before your skin even touches the glass, it says:
   ```text
   "make sure the fingerprint sensor is clean and dry, then try again."
   ```
2. **if you press your thumb firmly before tapping register:**  
   it says:
   ```text
   "getting fingerprint scanner ready. start registering your fingerprint when you see the icon."
   ```
   and then crashes and kicks you straight back to the biometrics menu in **36 milliseconds**.

regardless of which poison, it closes so aggressively fast that you literally have to take a screen recording video and scrub through the video player frame-by-frame just to screenshot the error dialogue before the activity destroys itself. how ironic.

you restart the phone. clean and dry.  
you wipe the cache partition. clean and dry.  
you wipe the glass with a microfiber cloth until you can see your ancestors in the reflection. clean and dry.  
you factory reset your phone. clean and dry.  
you flash the firmware to `xaa` because you thought it was going to wipe the fingerprint data. (big mistake.)  
you contemplate putting the phone in a clothes dryer. clean and dry.

congratulations: your sensor isn't dirty. your sensor isn't wet. your phone has just been trapped in an unrecoverable firmware livelock.  
you just joined the club where i'm alone and you just got in it. hi viewer!

---

### delusions

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
|  ABORTS IN 36MS: "MAKE SURE SENSOR IS CLEAN AND DRY" (1001) |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  because enrollment aborted, template count stays 0.        |
|  because template count stays 0, calibration stays dead.    |
|  INFINITE LIVELOCK ACHIEVED. THE SILICON COMMITS SUICIDE.   |
+-------------------------------------------------------------+
```

#### 1. samsung's stupid code: `cbgePreForceStop`
inside samsung's super secure proprietary code and hardware layer ("hal") (aka the `/vendor/lib64/libsfp_sensor.so`), when `m_enroll_template_count == 0`, suwon's code calls:
```c
void cbgePreForceStop() {
    m_bge_mode = 0; 
    // stop continuous background calibration
    // purge runtime acoustic impedance adaptation bins 1-7
    // this is in 0x784a0 (offset)
}
```
the _VERY_ nanosecond your enrolled print count hits zero, samsung kills continuous background estimation. all dynamic acoustic adaptation tables that compensate for room temperature are flushed down the toilet.

#### 2. qualcomm's trustzone paranoia: `CHECK_CD_BEFORE_ENROLL`
the trustlet is certified to the teeth. when enrollment stage 1 starts, it doesn't trust runtime data. it executes:

```c
// securefp.elf @ offset 0x4c8eee
qfp_contamination_detection_check()
```

(it's so secure, qualcomm.. so secure that we decompiled it. please don't sue me and google.)  
(aka `securefp.elf`)

it shoots an ultrasonic acoustic ping through the amoled glass and measures the return echo against factory baseline `bin 0`, which was calibrated in a sterile cleanroom in gumi at exactly **23.97°c**.

the speed of sound through amoled glass changes with temperature ($c \propto \sqrt{T}$, roughly $1.5\,\text{m/s}$ per degree celsius):
- if your phone is sitting in your bedroom at **25.5°c**, the delta is $+1.53^\circ\text{c}$.
- qualcomm's trustlet sees the echo delay, assumes someone slapped a layer of gelatin or silicone over the glass to spoof your identity, and aborts with error 48 (`0x30` -> vendor 1001).
- the samsung ui displays: *"make sure the fingerprint sensor is clean and dry"* or gets stuck on *"getting fingerprint scanner ready..."* before crashing.

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

### how do i run this

surprisingly, you don't even need root for this. thank god. you just need to do this:

```bash
git clone https://github.com/theyh4t3-ashlxy/psycho.git
cd psycho

# 2. connect phone via adb (usb or wireless)
adb devices

# 3. run the recovery script
python3 recover.py
```

follow the terminal:
1. cool your phone down (ac vent or ice pack wrapped in a cloth. pick your poision) until the battery is under 22°c. no more, no less.
2. wipe the screen with a microfiber shirt or cloth. no moisture. (until you break your screen or scratch it with deeper grooves at a level 7. real ones know)
3. put the phone down at room temp.
4. `recover.py` polls `/sys/class/thermal/thermal_zone56/temp` in real time. the second the chassis warms into the `23.40°c`–`24.30°c` goldilocks band, it rings the terminal bell and fires the enrollment intent.
5. slam your thumb onto the scanner and complete registration to 100%. the livelock is permanently dead.

---

### credits
samsung's engineers in south korea. also thanks antigravity for reverse engineering it.
