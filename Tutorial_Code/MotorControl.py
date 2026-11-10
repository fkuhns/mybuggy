from PicoAutonomousRobotics import KitronikPicoRobotBuggy
from time import sleep

buggy = KitronikPicoRobotBuggy()
run = False

DegreesPerSecond = (6/5)*360

print("DegreesPerSecond = ",DegreesPerSecond)

def ButtonIRQHandler(pin):
    global run
    print("Button Pressed")
    if(run):
        run = False
    else:
        run = True
    print("\tRun = ",run)

buggy.button.irq(trigger=machine.Pin.IRQ_RISING, handler =  ButtonIRQHandler)   

def Forwards():
    print("Forwards")
    buggy.motorOn("l","f",100)
    buggy.motorOn("r","f",100)
        
def Reverse():
    buggy.motorOn("l","r",100)
    buggy.motorOn("r","r",100)

def Stop():
    buggy.motorOff("r") 
    buggy.motorOff("l")

def Spin():
    buggy.motorOn("l","f",80)
    buggy.motorOn("r","r",80)

def TurnRight(HowFar):
    buggy.motorOn("l","f",80)
    buggy.motorOn("r","r",80)  
    sleep(HowFar/DegreesPerSecond)
    Stop()

def TurnLeft(HowFar):
    buggy.motorOn("l","r",80)
    buggy.motorOn("r","f",80)  
    sleep(HowFar/DegreesPerSecond)
    Stop()


while True:
    if(run):
        sleep(1) # wait so wa can get the hand clear after pressing start.
        print("Main: Run = True")
        for x in range (0,4):
            Forwards()
            sleep(1)
            TurnLeft (90)
            sleep(1)
        run = False
    else:
        Stop()
