# A  basic 'free roaming' robot
# uses the FRont and rear ultrasonic sensors to avoid obstacles
# if an ultrasonic is not fitted it will return -1
#uses the onboard button for a start / stop command via an IRQ.

from PicoAutonomousRobotics import KitronikPicoRobotBuggy as KPRB
from time import sleep_ms
import machine

buggy = KPRB()
startStop = False

ZONE_INVALID = -1 # unknown
ZONE_1 = 0 # < 8 inches
ZONE_2 = 1
ZONE_3 = 2
ZONE_CNT = 3

def valid_zone(z):
    return (z > ZONE_INVALID) and (z < ZONE_CNT)

ENABLE = "enabled"

MOTOR = "motor"
MOTOR_LEFT  = "l"
MOTOR_RIGHT = "r"
MOTOR_FWD   = "f"
MOTOR_REV   = "r"

DIR = 1
FWD = 2
REV = 3

LED_COLOR = "leds"

CAR_END = "end"
CAR_FRONT = "f"
CAR_BACK =  "r"
DIST = "distance"

LED_IDLE_COLOR = KPRB.BLUE


LED_FRONT = (0, 1)
LED_BACK  = (2, 3)

def ButtonIRQHandler(pin):
    global startStop, buggy
    if pin == buggy.button: 
        if startStop == True:
            startStop = False
        else:
            startStop = True

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

Zone2Dist = {ZONE_1: ( 0, 18),
             ZONE_2: (18, 40),
             ZONE_3: (40, -1)}

# Index by Front zone
ZONE_MAP = ( \
    {DIST: Zone2Dist[ZONE_1], LED_COLOR: KPRB.RED, CAR_BACK: ( # Front ZONE_1
        {DIST: Zone2Dist[ZONE_1],  LED_COLOR: KPRB.RED,     MOTOR_LEFT: (MOTOR_FWD,  30),  MOTOR_RIGHT: (MOTOR_REV,  30)},   # Back ZONE_1
        {DIST: Zone2Dist[ZONE_2],  LED_COLOR: KPRB.YELLOW,  MOTOR_LEFT: (MOTOR_FWD,  30),  MOTOR_RIGHT: (MOTOR_REV,   0)},   # Back ZONE_2
        {DIST: Zone2Dist[ZONE_3],  LED_COLOR: KPRB.GREEN,   MOTOR_LEFT: (MOTOR_REV,  50),  MOTOR_RIGHT: (MOTOR_REV,  20)})}, # Back ZONE_3
    {DIST: Zone2Dist[ZONE_2], LED_COLOR: KPRB.YELLOW, CAR_BACK: ( # Front ZONE_2
        {DIST: Zone2Dist[ZONE_1],  LED_COLOR: KPRB.RED,     MOTOR_LEFT: (MOTOR_FWD,  30),  MOTOR_RIGHT: (MOTOR_REV,  30)},   # Back ZONE_1
        {DIST: Zone2Dist[ZONE_2],  LED_COLOR: KPRB.YELLOW,  MOTOR_LEFT: (MOTOR_FWD,  50),  MOTOR_RIGHT: (MOTOR_REV,  10)},   # Back ZONE_2
        {DIST: Zone2Dist[ZONE_3],  LED_COLOR: KPRB.GREEN,   MOTOR_LEFT: (MOTOR_FWD,  60),  MOTOR_RIGHT: (MOTOR_FWD,   0)})}, # Back ZONE_3
    {DIST: Zone2Dist[ZONE_3], LED_COLOR: KPRB.GREEN, CAR_BACK: ( # Front ZONE_2
        {DIST: Zone2Dist[ZONE_1],  LED_COLOR: KPRB.RED,     MOTOR_LEFT: (MOTOR_FWD, 100),  MOTOR_RIGHT: (MOTOR_FWD, 100)},   # Back ZONE_1
        {DIST: Zone2Dist[ZONE_2],  LED_COLOR: KPRB.YELLOW,  MOTOR_LEFT: (MOTOR_FWD,  80),  MOTOR_RIGHT: (MOTOR_FWD,  80)},   # Back ZONE_2
        {DIST: Zone2Dist[ZONE_3],  LED_COLOR: KPRB.GREEN,   MOTOR_LEFT: (MOTOR_FWD,  60),  MOTOR_RIGHT: (MOTOR_FWD,  60)})}, # Back ZONE_3
    )

def map_zone(dist):
    global Zone2Dist
    zone = -1
    for z, d in Zone2Dist.items():
        if dist >= d[0] and ((d[1] > 0 and dist < d[1]) or (d[1] < 0)):
            zone = z
            break
    return zone

def roam_free():
    global startStop, buggy
    init_env()

    while True:
        if startStop == True:
            frontDistance = buggy.getDistance("f")
            rearDistance = buggy.getDistance("r")

            fz = map_zone(frontDistance)
            #assert valid_zone(fz)
            if valid_zone(fz):
                buggy.setLED(LED_FRONT[0], ZONE_MAP[fz][LED_COLOR])
                buggy.setLED(LED_FRONT[1], ZONE_MAP[fz][LED_COLOR])
            else:
                buggy.setLED(LED_FRONT[0], KPRB.WHITE)
                buggy.setLED(LED_FRONT[1], KPRB.WHITE)

            rz = map_zone(rearDistance)
            # assert valid_zone(rz)
            if valid_zone(rz):
                buggy.setLED(LED_BACK[0], ZONE_MAP[fz][CAR_BACK][rz][LED_COLOR])
                buggy.setLED(LED_BACK[1], ZONE_MAP[fz][CAR_BACK][rz][LED_COLOR])
            else:
                buggy.setLED(LED_BACK[0], KPRB.PURPLE)
                buggy.setLED(LED_BACK[1], KPRB.PURPLE)
            
            if fz == ZONE_1:
                buggy.motorOff("l")
                buggy.motorOff("r")

            buggy.motorOn(MOTOR_LEFT, 
                          ZONE_MAP[fz][CAR_BACK][rz][MOTOR_LEFT][0],
                          ZONE_MAP[fz][CAR_BACK][rz][MOTOR_LEFT][1])
            buggy.motorOn(MOTOR_RIGHT, 
                          ZONE_MAP[fz][CAR_BACK][rz][MOTOR_RIGHT][0],
                          ZONE_MAP[fz][CAR_BACK][rz][MOTOR_RIGHT][1])
            buggy.show()
        else: #motors turned off
            set_buggy_idle()

        sleep_ms(50)


if __name__ == "__main__":
    roam_free()
