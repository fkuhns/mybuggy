# A  basic 'free roaming' robot
# uses the FRont and rear ultrasonic sensors to avoid obstacles
# if an ultrasonic is not fitted it will return -1
#uses the onboard button for a start / stop command via an IRQ.

from PicoAutonomousRobotics import KitronikPicoRobotBuggy as KPRB
from time import sleep_ms
import machine
import config

buggy = KPRB()
Running = False

LED_IDLE_COLOR = KPRB.WHITE

LEDS_FRONT = (0, 1)
LED_BACK  = (2, 3)

def ButtonIRQHandler(pin):
    global Running, buggy
    if pin == buggy.button:
        if Running == True:
            Running = False
        else:
            Running = True

def set_buggy_idle():
    global buggy
    buggy.motorOff("l")
    buggy.motorOff("r")

    for l in range(4):
        buggy.setLED(l, LED_IDLE_COLOR)
    buggy.show()

def init_env():
    global buggy

    startStop = False

    buggy.button.irq(trigger=machine.Pin.IRQ_RISING, handler =  ButtonIRQHandler)

    set_buggy_idle()

def roam_free():
    global Running, buggy
    init_env()

    while True:
        try:
            if not Running:
                set_buggy_idle()
                continue

            # Assume usonic for front and back - always!
            fd = buggy.getDistance("f")
            rd = buggy.getDistance("r")

            if fd == -2: # timeout waiting for pulse to start
                continue
            elif fd == -1: # timeout waiting for pulse echo
                fz = config.max_zone()
            else:
                # returns a valid zone or raises a ValueError exception
                fz = config.dist2zone(fd)

            # may raise KeyError
            front_map = config.ZONE_MAP[fz]

            buggy.setLED(LEDS_FRONT[0], front_map[config.LED_COLOR])
            buggy.setLED(LEDS_FRONT[1], front_map[config.LED_COLOR])

            # returns a valid zone or raises a ValueError exception
            try:
                rz = config.dist2zone(rd)
                # may raise KeyError
                back_map = front_map[config.CAR_BACK][rz]
            except:
                rz = config.max_zone()
                back_map = front_map[config.CAR_BACK][rz]

            buggy.setLED(LED_BACK[0], back_map[config.LED_COLOR])
            buggy.setLED(LED_BACK[1], back_map[config.LED_COLOR])

            if fz == config.ZONE_1:
                buggy.motorOff("l")
                buggy.motorOff("r")

            buggy.motorOn(config.MTR_LEFT,
                        back_map[config.MTR_LEFT][0],
                        back_map[config.MTR_LEFT][1])
            buggy.motorOn(config.MTR_RIGHT,
                        back_map[config.MTR_RIGHT][0],
                        back_map[config.MTR_RIGHT][1])

            buggy.show()
        except Exception as e:
            print("fz = ", fz, "fd = ", fd)
            print("roam_free: outer loop caught exception: ", e)
            set_buggy_idle()

        sleep_ms(50)


if __name__ == "__main__":
    roam_free()
