from PicoAutonomousRobotics import KitronikPicoRobotBuggy as KPRB

# Used as fields and values in the ZONE_MAP
DIST      = "distance"
LED_COLOR = "leds"
CAR_BACK =  "r"
MTR_LEFT  = "l"
MTR_RIGHT = "r"
MTR_FWD   = "f"
MTR_REV   = "r"

# Defines the zones based on the distance between the car and any obstacle in
# front of or behind the it. Default zones:
#  ZONE_1 => Critical : "danger-close" to an obstruction, take drastic action
#                       to avoid an obstacle. Likely you'll want to stop, then
#                       make a hard spinning turn.
#  ZONE_2 => Warning  : You should start a moderate turn before you enter the
#                       Critical zone, Zone_1, and risk hitting an obstacle.
#  ZONE_3 => Normal   : you've got space to navigate or to continue going
#                       straight. However you should limit your speed since
#                       the car is approaching the yellow zone (zone_2).
#  ZONE_4 => Wide Open: Plenty of space in front and/or in back. No need to
#                       limit speed or take action.
#
ZONE_INVALID = -1 # Invalid or unknown which zone the car is in
ZONE_1 = 0  # Critical distance, collision is imminent!
ZONE_2 = 1  # Warning, approaching an obstacle but have time to avoid
ZONE_3 = 2  # Normal, obstacles are present but you have space to navigate
ZONE_4 = 3  # Wide open, any obstacles are far away
ZONE_CNT = 4 # just a convenance constant

def valid_zone(z):
    return (z > ZONE_INVALID) and (z < ZONE_CNT)

# Defines the zone specific distance range measured in inches.
# ZONE_1: ( 0, 12) => the car is between 0 and 12 inches from an obstacle
# Notes:
#  - parentheses define the minimum and maximum distance for a zone
#    (min_distance, max_distance). If d = distance between a car and an obstacle
#    then to be in a zone: [ min_distance <= d < max_distance ]
#  - Zone_1 must always start with 0
#  - a -1 for a max distance means there is no upper limit. so (54, -1) means
#    any distance d >= 54 will map to that zone.
#  - if Zone_3 is defined as Zone_3 : (30, -1) then any distance d > 30 will
#    map to zone 3. This means zone_4 is ignored and not used.
#  - the zones must get progressively further away from the obstacle.
#  - The next further away zone must always start at the previous zones
#    max_distance. This means
#      ZONE_1 must start at 0.
#      ZONE_2 must start at the max_distance of Zone_1
#      ZONE_3 must start at the max_distance of Zone_2
#      ZONE_4 must start at the max_distance of Zone_3
ZONE2DIST = {ZONE_1: ( 0,  8),
             ZONE_2: ( 8, 30),
             ZONE_3: (30, 54),
             ZONE_4: (54, -1)}

def min_zone():
    return ZONE_1

def max_zone():
    for z in range(ZONE_CNT):
        zone = z
        if ZONE2DIST[z][1] == -1:
            break
    return zone

def dist2zone(dist):
    for z, d in ZONE2DIST.items():
        if dist >= d[0] and ((d[1] > 0 and dist < d[1]) or (d[1] < 0)):
            return z
    raise ValueError("dist2zone: invalid distance or missing zone")

def zone2dist(z):
    if not valid_zone(z):
        z = max_zone()
    return ZONE2DIST[z]

# The ZONE_MAP is indexed distance zone. Note:
#   - A car will always have a distance zone in front of it, and a possibly
#     different zone behind.
# For example, a Zone2Dist map with ZONE_1: (0, 12) and ZONE_2: (12, 30), and
# a car with an obstacle 24" in front, and another obstacle 8" behind it is
# assigned
#     Front distance zone = ZONE_2
#     Back distance zone = ZONE_1
#
# The ZONE_MAP list maps a given front zone and back zone to
#     - Front LED color
#     - Back LED color
#     - Left Motor direction and speed
#     - Right Motor direction and speed
#
# Do not change any of the values immediately to the left of a colon ':'
# (DIST, LED_COLOR, CAR_BACK, MTR_LEFT, MTR_RIGHT)
# Also do not change any value with Zone2Dist["zone"]. You may change the
# values to the immediate right of (LED_COLOR, MTR_LEFT, MTR_RIGHT).
#
# The ZONE_MAP defines the Left and Right motor's direction and speed for
# every combination of Front and Back distance Zones. So using the table
# below, if a Front Zone is ZONE_3 and Back Zone ZONE_2, then
#      Front LEDs  = Green,
#      Back LEDs   = Yellow,
#      Left Motor  = (Forward, 50)
#      Right Motor = (Forward, 80)
#
# Alternative, if the Front Zone is ZONE_2 and the Back Zone is ZONE_3 then
#      Front LEDs  = Yellow,
#      Back LEDs   = Green,
#      Left Motor  = (Forward, 10)
#      Right Motor = (Forward, 60)
#
# Front Zone  Front LEDs  Back Zone  Back LEDs      Left Motor         Right Motor
# ----------  ----------  ---------  ---------  ------------------  ------------------
#   ZONE_1      Red        ZONE_1     Red      (Direction, Speed)  (Direction, speed)
#                         ------------------------------------------------------------
#                          ZONE_2     Yellow   (Direction, Speed)  (Direction, speed)
#                         ------------------------------------------------------------
#                          ZONE_3     Green    (Direction, Speed)  (Direction, speed)
#                         ------------------------------------------------------------
#                          ZONE_4     Blue     (Direction, Speed)  (Direction, speed)
#  -----------------------------------------------------------------------------------
#   ZONE_2      Yellow     ZONE_1     Red      (Direction, Speed)  (Direction, speed)
#                         ------------------------------------------------------------
#                          ZONE_2     Yellow   (Direction, Speed)  (Direction, speed)
#                         ------------------------------------------------------------
#                        **ZONE_3     Green      (MTR_FWD, 10)      (MTR_FWD, 60)
#                         ------------------------------------------------------------
#                          ZONE_4     Blue     (Direction, Speed)  (Direction, speed)
#  -----------------------------------------------------------------------------------
#   ZONE_3      GREEN      ZONE_1     Red      (Direction, Speed)  (Direction, speed)
#                         ------------------------------------------------------------
#                        **ZONE_2     Yellow     (MTR_FWD, 50)       (MTR_FWD, 80)
#                         ------------------------------------------------------------
#                          ZONE_3     Green    (Direction, Speed)  (Direction, speed)
#                         ------------------------------------------------------------
#                          ZONE_4     Blue     (Direction, Speed)  (Direction, speed)
#  -----------------------------------------------------------------------------------
#   ZONE_4      Blue       ZONE_1     Red      (Direction, Speed)  (Direction, speed)
#                         ------------------------------------------------------------
#                          ZONE_2     Yellow   (Direction, Speed)  (Direction, speed)
#                         ------------------------------------------------------------
#                          ZONE_3     Green    (Direction, Speed)  (Direction, speed)
#                         ------------------------------------------------------------
#                          ZONE_4     Blue     (Direction, Speed)  (Direction, speed)
#  -----------------------------------------------------------------------------------
# Values you may change:
#   1) LED_COLOR: KPRB.BLACK, KPRB.RED,  KPRB.YELLOW, KPRB.GREEN,
#                 KPRB.CYAN,  KPRB.BLUE, KPRB.PURPLE, KPRB.WHITE
#   2) Motor direction: MTR_FWD or MTR_REV
#   3) Motor Speed:     value between 0 and 100
ZONE_MAP = (
    {DIST: ZONE2DIST[ZONE_1], LED_COLOR: KPRB.RED, CAR_BACK: ( # Front ZONE_1
        {DIST: ZONE2DIST[ZONE_1],  LED_COLOR: KPRB.RED,     MTR_LEFT: (MTR_REV,  50),  MTR_RIGHT: (MTR_FWD,  50)}, # Back ZONE_1
        {DIST: ZONE2DIST[ZONE_2],  LED_COLOR: KPRB.YELLOW,  MTR_LEFT: (MTR_REV,  50),  MTR_RIGHT: (MTR_FWD,  50)}, # Back ZONE_2
        {DIST: ZONE2DIST[ZONE_3],  LED_COLOR: KPRB.GREEN,   MTR_LEFT: (MTR_REV,  40),  MTR_RIGHT: (MTR_FWD,  40)}, # Back ZONE_3
        {DIST: ZONE2DIST[ZONE_4],  LED_COLOR: KPRB.BLUE,    MTR_LEFT: (MTR_REV,  40),  MTR_RIGHT: (MTR_FWD,  40)}) # Back ZONE_4
    },
    {DIST: ZONE2DIST[ZONE_2], LED_COLOR: KPRB.YELLOW, CAR_BACK: ( # Front ZONE_2
        {DIST: ZONE2DIST[ZONE_1],  LED_COLOR: KPRB.RED,     MTR_LEFT: (MTR_FWD,  10),  MTR_RIGHT: (MTR_FWD, 100)}, # Back ZONE_1
        {DIST: ZONE2DIST[ZONE_2],  LED_COLOR: KPRB.YELLOW,  MTR_LEFT: (MTR_FWD,  10),  MTR_RIGHT: (MTR_FWD,  80)}, # Back ZONE_2
        {DIST: ZONE2DIST[ZONE_3],  LED_COLOR: KPRB.GREEN,   MTR_LEFT: (MTR_FWD,  10),  MTR_RIGHT: (MTR_FWD,  75)}, # Back ZONE_3
        {DIST: ZONE2DIST[ZONE_4],  LED_COLOR: KPRB.BLUE,    MTR_LEFT: (MTR_FWD,  10),  MTR_RIGHT: (MTR_FWD,  75)}) # Back ZONE_4
    },
    {DIST: ZONE2DIST[ZONE_3], LED_COLOR: KPRB.GREEN, CAR_BACK: ( # Front ZONE_3
        {DIST: ZONE2DIST[ZONE_1],  LED_COLOR: KPRB.RED,     MTR_LEFT: (MTR_FWD,  40),  MTR_RIGHT: (MTR_FWD,  40)}, # Back ZONE_1
        {DIST: ZONE2DIST[ZONE_2],  LED_COLOR: KPRB.YELLOW,  MTR_LEFT: (MTR_FWD,  50),  MTR_RIGHT: (MTR_FWD,  40)}, # Back ZONE_2
        {DIST: ZONE2DIST[ZONE_3],  LED_COLOR: KPRB.GREEN,   MTR_LEFT: (MTR_FWD,  50),  MTR_RIGHT: (MTR_FWD,  30)}, # Back ZONE_3
        {DIST: ZONE2DIST[ZONE_4],  LED_COLOR: KPRB.BLUE,    MTR_LEFT: (MTR_FWD,  40),  MTR_RIGHT: (MTR_FWD,  30)}) # Back ZONE_4
    },
    {DIST: ZONE2DIST[ZONE_4], LED_COLOR: KPRB.BLUE, CAR_BACK: ( # Front ZONE_4
        {DIST: ZONE2DIST[ZONE_1],  LED_COLOR: KPRB.RED,     MTR_LEFT: (MTR_FWD, 100),  MTR_RIGHT: (MTR_FWD, 100)}, # Back ZONE_1
        {DIST: ZONE2DIST[ZONE_2],  LED_COLOR: KPRB.YELLOW,  MTR_LEFT: (MTR_FWD,  80),  MTR_RIGHT: (MTR_FWD,  80)}, # Back ZONE_2
        {DIST: ZONE2DIST[ZONE_3],  LED_COLOR: KPRB.GREEN,   MTR_LEFT: (MTR_FWD,  40),  MTR_RIGHT: (MTR_FWD,  40)}, # Back ZONE_3
        {DIST: ZONE2DIST[ZONE_4],  LED_COLOR: KPRB.BLUE,    MTR_LEFT: (MTR_FWD,  40),  MTR_RIGHT: (MTR_FWD,  40)}) # Back ZONE_4
    }
)

