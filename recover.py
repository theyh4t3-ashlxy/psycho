#!/usr/bin/env python3
"""
psycho - samsung galaxy s24 ultra ultrasonic fingerprint livelock recovery tool
reverse-engineered by ashley & antigravity

recovers qualcomm qbt4000 3d sonic gen 2 from the 0-template error 1001 acoustic livelock.
requires: adb, python 3.8+
zero root required. knox 0x0 intact.
"""

import subprocess
import sys
import time
import os

TARGET_DEVICE = os.environ.get("ANDROID_SERIAL", "")
TARGET_TEMP_MIN = 23.40
TARGET_TEMP_MAX = 24.30
FACTORY_BASELINE = 23.97

def run_adb(args):
    cmd = ["adb"]
    if TARGET_DEVICE:
        cmd.extend(["-s", TARGET_DEVICE])
    cmd.extend(args)
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.stdout.strip()

def check_connection():
    out = run_adb(["get-state"])
    if "device" not in out:
        print("[!] no adb device detected. connect via usb or wireless adb and ensure debugging is enabled.")
        sys.exit(1)
    model = run_adb(["shell", "getprop", "ro.product.model"])
    chip = run_adb(["shell", "getprop", "ro.board.platform"])
    print(f"[*] target detected: {model} (platform: {chip})")

def get_battery_temp():
    # thermal_zone56 is the battery zone on snapdragon 8 gen 3 (e3quew / SM-S928)
    val = run_adb(["shell", "cat /sys/class/thermal/thermal_zone56/temp 2>/dev/null"])
    try:
        return float(val) / 1000.0
    except (ValueError, TypeError):
        # fallback: dumpsys battery
        b_val = run_adb(["shell", "dumpsys battery | grep temperature"])
        try:
            return float(b_val.split(":")[1].strip()) / 10.0
        except Exception:
            return None

def trigger_enrollment():
    print("\n" + "="*60)
    print(">>> STRIKE WINDOW REACHED <<<")
    print(f">>> LAUNCHING ENROLLMENT INTENT NOW <<<")
    print("="*60 + "\n")
    # ring terminal bell
    sys.stdout.write("\a\a\a")
    sys.stdout.flush()
    run_adb(["shell", "am", "start", "-a", "android.settings.FINGERPRINT_ENROLL"])

def main():
    print(r"""
  ____  ______   ______ _   _  ____  
 |  _ \/ ___\ \ / / ___| | | |/ __ \ 
 | |_) \___ \\ V / |   | |_| | |  | |
 |  __/ ___) || || |___|  _  | |  | |
 |_|   |____/ |_| \____|_| |_|\____/ 
 
 samsung s24 ultra fingerprint livelock recovery
 breaking cbgePreForceStop & trustzone error 1001
""")
    check_connection()

    current_prints = run_adb(["shell", "dumpsys fingerprint | grep -o '\"count\":[0-9]*' | head -n 1"])
    print(f"[*] current registered templates: {current_prints or 'unknown'}")

    print("\n--- INSTRUCTIONS ---")
    print("1. your sensor is trapped in a trustzone livelock because template count == 0")
    print("   purged continuous background acoustic estimation (cbgePreForceStop in libsfp_sensor.so).")
    print(f"2. qualcomm's securefp.elf baseline is locked to factory bin 0 ({FACTORY_BASELINE}°c).")
    print(f"3. we need the battery sensor to cross into the goldilocks window ({TARGET_TEMP_MIN}°c to {TARGET_TEMP_MAX}°c).")
    print("4. cool your phone down (place it in front of an ac vent or on a cool pack) until temp is < 22.0°c.")
    print("5. once cooled, wipe the glass completely bone-dry with a microfiber cloth.")
    print("   (dew-point condensation will scatter ultrasonic pulses and trigger error 48).")
    print("6. let the phone rest at room temp. this script will alert you the second it hits the window.\n")

    input("press [ENTER] once you have cooled the device and are ready to monitor... ")

    print("\n[*] polling thermal sensors...")
    strike_fired = False

    while True:
        temp = get_battery_temp()
        if temp is None:
            print("[!] failed to read thermal sensor. retrying...")
            time.sleep(1)
            continue

        delta = temp - FACTORY_BASELINE
        status = "HOLD (too cold)" if temp < TARGET_TEMP_MIN else ("HOLD (too warm)" if temp > TARGET_TEMP_MAX else "GOLDILOCKS WINDOW")

        bar_len = 20
        # scale from 15C to 35C
        ratio = max(0.0, min(1.0, (temp - 15.0) / 20.0))
        filled = int(ratio * bar_len)
        bar = "#" * filled + "-" * (bar_len - filled)

        sys.stdout.write(f"\r[{bar}] temp: {temp:5.2f}°c (Δ {delta:+5.2f}°c) | status: {status:18s}")
        sys.stdout.flush()

        if TARGET_TEMP_MIN <= temp <= TARGET_TEMP_MAX:
            if not strike_fired:
                trigger_enrollment()
                strike_fired = True
                print("[*] complete enrollment on phone now. do not stop until it hits 100%.")
                print("[*] once finger 1 is registered, the livelock is permanently broken.")
                break
        elif temp > TARGET_TEMP_MAX and strike_fired:
            break

        time.sleep(0.5)

    print("\n[*] finished. reboot phone and verify lockscreen unlock.")

if __name__ == "__main__":
    main()
