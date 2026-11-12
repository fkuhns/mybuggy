# Create a simple UI for editing ZONE_MAP

Project: Free Roaming Buggy (car)

Buggy

- Has two RGB LEDs in the front and two LEDs in the back
- Has two distance sensors, one in the front and one in the back

Zone

- Every zone has a unique variable name associated with a distance tuple.
The following example is used throughout:

```python
    ZONE2DIST = {ZONE_1: ( 0, 12),
                 ZONE_2: (12, 30),
                 ZONE_3: (30, 54),
                 ZONE_4: (54, -1)}
```

- A zone's distance tuple defines the `min` and `max` distances, in inches, to an
obstacle, `(min, max)`.

```text
    Zone_1: (0, 12) =>
        min distance = 0"
        max distance = 12"
```

- if the buggy's distance to an obstacle is represented by `d`, then it is
assigned to a zone where the following is true:

```test
    Zone_X (min, max): min <= d < max
```

- Since a buggy has both a front and back distance sensor, each will have
  an assigned distance zone.
    - For example, if a buggy's front is 11" from a wall, and back 48" from an
      obstacle, the buggy front belongs to ZONE_1 and the back to ZONE_3.

```text
    Buggy Front: d = 11"; zone = ZONE_1, 0 <= d < 12
    Buggy Back: d = 48"; zone = ZONE_3, 30 <= d < 54
```

- It's expected that a naive user will use the ZONE2DIST object to set the
  zone distances (see Zone Rules).

Zone Rules

- The min distance for ZONE_1 must always be 0
- The min distance for ZONE_2 must be equal to the max distance for ZONE_1.
  This is a genal rule so each subsequent zone's min distance must be equal to
  the max distance of the preceding zone
- Front and rear LED colors are set based on the assigned zone. That means LED
  color is associated with a zone.
- A max distance of -1 means there is no distance upper limit
    - By default ZONE_4 has a max distance of -1
    - However if a preceding zone is assigned a max distance of -1 then that
      zone is considered to be the last valid zone.
    - So for example, if ZONE_3 has a max distance of -1, then ZONE_4 will
      not be used.

ZONE_MAP

- The ZONE_MAP list controls the Front/Back LED's color along with the each
  motor's speed and direction
- Its expected that a naive user will use the ZONE_MAP to set the following
    - Front LED colors based on its assigned zone
    - Back LED colors based on the assigned zone
    - Left and Right Motor direction and speed based on both the front and back
      assigned zones.

UI

- Basic UI implemented using a browser, can assume Google Chrome or Firefox.
- User can set per zone min and max distances. UI must enforce the above rules
  and ensure code consistency and reliability.
- User can set the per Zone LED colors.
- For each combination of front and rear zone, user can set the left and right
  motor's direction and speed.
- Let the structure of ZONE_MAP drive the solution.
- The UI will record desired settings within the ZONE_MAP, this means no new
  code paths or variables can be created that are used in the main loop and code