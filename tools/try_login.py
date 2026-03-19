#!/usr/bin/env python3
"""
Auto-login attempt script for screen unlock
Password: 12345678
"""

import os
import time
import subprocess

def wake_screen():
    """Try to wake the screen."""
    print("Waking screen...")
    
    # Try xdotool to simulate activity
    try:
        subprocess.run(['xdotool', 'mousemove', '10', '10'], 
                      capture_output=True, timeout=5)
        subprocess.run(['xdotool', 'mousemove', '20', '20'], 
                      capture_output=True, timeout=5)
        print("  ✓ Mouse movement sent")
    except:
        print("  ✗ xdotool not available")
    
    # Try pressing keys
    try:
        subprocess.run(['xdotool', 'key', 'space'], 
                      capture_output=True, timeout=5)
        print("  ✓ Space key sent")
    except:
        pass
    
    # Alternative: xset to wake
    try:
        subprocess.run(['xset', 'dpms', 'force', 'on'], 
                      capture_output=True, timeout=5)
        print("  ✓ DPMS wake attempted")
    except:
        pass
    
    time.sleep(2)

def try_login():
    """Attempt to type password and login."""
    password = "12345678"
    
    print("\nAttempting login...")
    print(f"  Password: {password}")
    
    try:
        # Type password
        subprocess.run(['xdotool', 'type', password], 
                      capture_output=True, timeout=5)
        print("  ✓ Password typed")
        
        time.sleep(0.5)
        
        # Press Enter
        subprocess.run(['xdotool', 'key', 'Return'], 
                      capture_output=True, timeout=5)
        print("  ✓ Enter pressed")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def check_logged_in():
    """Check if we're logged in."""
    try:
        # Check if we can run a simple command
        result = subprocess.run(['whoami'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            print(f"\n✓ Logged in as: {result.stdout.strip()}")
            return True
    except:
        pass
    return False

def main():
    print("="*50)
    print("SCREEN UNLOCK ATTEMPT")
    print("="*50)
    print()
    
    # Check if already logged in
    if check_logged_in():
        print("Already logged in!")
        return
    
    # Wake screen
    wake_screen()
    
    # Try login
    if try_login():
        print("\nWaiting for login...")
        time.sleep(3)
        
        if check_logged_in():
            print("\n✅ LOGIN SUCCESSFUL")
        else:
            print("\n⚠️  Login status unclear - may need visual check")
    else:
        print("\n❌ LOGIN ATTEMPT FAILED")
        print("\nTroubleshooting:")
        print("  - Is xdotool installed? (sudo apt install xdotool)")
        print("  - Is the screen actually at login prompt?")
        print("  - Try manually moving mouse first")

if __name__ == "__main__":
    main()
