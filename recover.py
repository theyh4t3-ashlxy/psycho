#!/usr/bin/env python3
"""Monitors battery temp via ADB and opens fingerprint enrollment in the target window."""

import os
import re
import shutil
import subprocess
import sys
import time

TARGET_DEVICE = os.environ.get("ANDROID_SERIAL", "")
TARGET_TEMP_MIN = 23.40
TARGET_TEMP_MAX = 24.30
COOL_THRESHOLD = 22.00
BASELINE_TEMP = 23.97


def run_adb(args, timeout=5):
    cmd = ["adb"]
    if TARGET_DEVICE:
        cmd.extend(["-s", TARGET_DEVICE])
    cmd.extend(args)
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "adb command timed out"


def check_connection():
    if not shutil.which("adb"):
        print("[!] adb not found in PATH. install Android Platform-Tools first.")
        sys.exit(1)

    code, out, err = run_adb(["get-state"])
    if code != 0 or out != "device":
        if "unauthorized" in err or "unauthorized" in out:
            print("[!] device is unauthorized. tap 'Allow' on the USB debugging prompt on your phone.")
        elif "more than one" in err:
            print("[!] multiple ADB devices detected. set ANDROID_SERIAL to pick one.")
        else:
            print("[!] no ADB device detected. plug in via USB (or wireless ADB) with USB debugging enabled.")
        sys.exit(1)

    _, model, _ = run_adb(["shell", "getprop", "ro.product.model"])
    _, chip, _ = run_adb(["shell", "getprop", "ro.board.platform"])
    print(f"[*] connected: {model or 'unknown'} ({chip or 'unknown'})")


def get_template_count():
    code, out, _ = run_adb(["shell", "dumpsys", "fingerprint"])
    if code != 0:
        return None
    match = re.search(r'"count"\s*:\s*(\d+)', out)
    return int(match.group(1)) if match else None


def get_battery_temp():
    # High-res thermal zone first (millidegrees C)
    code, val, _ = run_adb(["shell", "cat", "/sys/class/thermal/thermal_zone56/temp"])
    if code == 0 and val:
        try:
            temp = float(val) / 1000.0
            if 0.0 < temp < 80.0:
                return temp
        except ValueError:
            pass

    # Fallback: dumpsys battery (tenths of a degree C)
    code, out, _ = run_adb(["shell", "dumpsys", "battery"])
    if code == 0:
        match = re.search(r"temperature:\s*(\d+)", out)
        if match:
            temp = int(match.group(1)) / 10.0
            if 0.0 < temp < 80.0:
                return temp

    return None


def launch_enrollment():
    print("\n\n[*] target temp reached — opening fingerprint enrollment...")
    sys.stdout.write("\a")
    sys.stdout.flush()
    code, _, err = run_adb(["shell", "am", "start", "-a", "android.settings.FINGERPRINT_ENROLL"])
    if code != 0:
        print(f"[!] couldn't open enrollment automatically ({err or 'unknown error'}).")
        print("    open Settings -> Security and privacy -> Biometrics -> Fingerprints manually.")
        return False
    return True


def render_bar(temp):
    bar_len = 20
    ratio = max(0.0, min(1.0, (temp - 15.0) / 20.0))
    filled = int(ratio * bar_len)
    return "#" * filled + "-" * (bar_len - filled)


def main():
    check_connection()

    count = get_template_count()
    print(f"[*] registered fingerprints: {count if count is not None else 'unknown'}")
    print(f"[*] target window: {TARGET_TEMP_MIN:.2f}°C - {TARGET_TEMP_MAX:.2f}°C (cool under {COOL_THRESHOLD:.0f}°C first)")
    print("[*] see INSTRUCTIONS.md for full steps. press Ctrl+C to quit.\n")

    armed = False
    first_read = True

    try:
        while True:
            temp = get_battery_temp()
            if temp is None:
                print("\n[!] couldn't read battery temp, retrying...")
                time.sleep(1)
                continue

            # If you already cooled the phone before starting the script, arm right away.
            # Otherwise wait until it cools below 22°C so it doesn't fire on the way down.
            if first_read and temp < TARGET_TEMP_MIN:
                armed = True
            elif temp <= COOL_THRESHOLD:
                armed = True
            first_read = False

            delta = temp - BASELINE_TEMP
            bar = render_bar(temp)

            if not armed:
                status = f"cool below {COOL_THRESHOLD:.0f}°C first"
            elif temp < TARGET_TEMP_MIN:
                status = "warming up (wait)"
            elif temp > TARGET_TEMP_MAX:
                status = "too warm (cool again)"
            else:
                status = "in target window"

            sys.stdout.write(f"\r[{bar}] {temp:5.2f}°C ({delta:+5.2f}°C) | {status:<24}")
            sys.stdout.flush()

            if armed and TARGET_TEMP_MIN <= temp <= TARGET_TEMP_MAX:
                launch_enrollment()
                print("[*] finish registering your first fingerprint all the way to 100%.")
                print("[*] once it saves, reboot your phone and test unlocking.")
                break

            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[*] stopped.")


if __name__ == "__main__":
    main()
