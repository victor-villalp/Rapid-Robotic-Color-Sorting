import cv2
import numpy as np 
import RPi.GPIO as GPIO   
import time
from time import sleep 
from picamera.array import PiRGBArray
from picamera import PiCamera

def motor_gpio_setup(inA, inB, en, pwm_freq = 1000, duty_cycle = 80):
    GPIO.setup(inA,GPIO.OUT)
    GPIO.setup(inB,GPIO.OUT)
    GPIO.setup(en,GPIO.OUT)
    GPIO.output(inA,GPIO.LOW)
    GPIO.output(inB,GPIO.LOW)
    GPIO.PWM(en,pwm_freq).start(duty_cycle)

def start_disk_motor(inA, inB):
    GPIO.output(inA,GPIO.LOW)
    GPIO.output(inB,GPIO.HIGH)

def stop_disk_motor(inA, inB):
    GPIO.output(inA,GPIO.LOW)
    GPIO.output(inB,GPIO.LOW)

def open_door(inA, inB):
    # forward for duration y
    GPIO.output(inA,GPIO.LOW)
    GPIO.output(inB,GPIO.HIGH)
    initial_time = int(round(time.time() * 1000))
    if inA == 20:
        open_door_time = initial_time + 350
        while(int(round(time.time() * 1000))< open_door_time):
            pass
    else:
        open_door_time = initial_time + 275
        while(int(round(time.time() * 1000))< open_door_time):
            pass
    GPIO.output(inA,GPIO.LOW) # stop
    GPIO.output(inB,GPIO.LOW)
    
def close_door(inA, inB):    
    # forward for duration y
    GPIO.output(inA,GPIO.HIGH)
    GPIO.output(inB,GPIO.LOW)
    initial_time = int(round(time.time() * 1000))
    delays = {20:40, 23:50, 26:50, 9:75}
    close_door_time = initial_time + delays.get(inA)
    while(int(round(time.time() * 1000))< close_door_time):
        pass
    GPIO.output(inA,GPIO.LOW)
    GPIO.output(inB,GPIO.LOW)

def create_hsv_mask_limits(color_mask_top, color_mask_mid, color_mask_bot, x_hue, x_sat, x_val):
    # x_hue = hue delta, x_sat = lower saturation limit, x_val = lower value limit
    # Average color mask values in HSV format
    hsv_top = cv2.cvtColor(color_mask_top, cv2.COLOR_BGR2HSV)
    hsv_mid = cv2.cvtColor(color_mask_mid, cv2.COLOR_BGR2HSV)
    hsv_bot = cv2.cvtColor(color_mask_bot, cv2.COLOR_BGR2HSV)
    
    # Using numpy array(byte), to hold HSV(Hue-Saturation_Value) ranges
    lower_top = np.uint8([hsv_top[0][0][0] - x_hue, x_sat, x_val])
    upper_top = np.uint8([hsv_top[0][0][0] + x_hue, 255, 255])
    lower_mid = np.uint8([hsv_mid[0][0][0] - x_hue, x_sat, x_val])
    upper_mid = np.uint8([hsv_mid[0][0][0] + x_hue, 255, 255])
    lower_bot = np.uint8([hsv_bot[0][0][0] - x_hue, x_sat, x_val])
    upper_bot = np.uint8([hsv_bot[0][0][0] + x_hue, 255, 255])
    return (lower_top, upper_top, lower_mid, upper_mid, lower_bot, upper_bot)

def compute_mask_mean(lower_top, upper_top, lower_mid, upper_mid, lower_bot, upper_bot):
    # Mask for top, middle, and bottom section 
    top = cv2.inRange(hsv, lower_top, upper_top)
    mid = cv2.inRange(hsv, lower_mid, upper_mid)
    bot = cv2.inRange(hsv, lower_bot, upper_bot)
    # Apply the mask to the original image to show only the detected color
    mask = cv2.bitwise_or(cv2.bitwise_or(top, mid), bot)
    return cv2.mean(mask)[0]


print("\nCode started")

GPIO.setmode(GPIO.BCM)

# Motor GPIO setup
in1, in2 = 20, 16  # Door 1
in3, in4 = 23, 24  # Door 2 
in5, in6 = 26, 19  # Door 3
in7, in8 = 9, 10   # Door 4 
in9, in10 = 17, 27 # Disk motor
motor_gpio_setup(in1, in2, 21)
motor_gpio_setup(in3, in4, 25)
motor_gpio_setup(in5, in6, 13)
motor_gpio_setup(in7, in8, 22)
motor_gpio_setup(in7, in8, 18, pmw_freq = 13, duty_cycle = 12)

print("\nGPIO INIT Complete")

# Door States: open = 1, closed = 0
door_states = [0, 0, 0, 0] 
door_inputs = [(in1, in2), (in3, in4), (in5, in6), (in7, in8)]
time_door_opened = time_door_should_close = 0

#Camera initialization
camera = PiCamera()
camera.resolution = (160, 128)
while camera.analog_gain < 1:
    time.sleep(0.1)
    print('Gain:' + str(camera.analog_gain))
camera.shutter_speed = camera.exposure_speed
camera.exposure_mode='auto'
camera.awb_mode ='off'
camera.awb_gains = camera.awb_gains
raw_capture = PiRGBArray(camera, size=(160, 128))

print("\nCamera INIT Complete")

# Average (experimentally collected) blue gumball RGB values at top/middle/bottom of free fall
blue_mask_top = np.uint8([[[100, 56, 26]]])
blue_mask_mid = np.uint8([[[87, 50, 13]]])
blue_mask_bot = np.uint8([[[83, 60, 2]]])
(lower_lim_blue_top, upper_lim_blue_top,
 lower_lim_blue_mid, upper_lim_blue_mid,
 lower_lim_blue_bot, upper_lim_blue_bot) = create_hsv_mask_limits(
    blue_mask_top, blue_mask_mid, blue_mask_bot, x_hue=3, x_sat=90, x_val=100)

# Average (experimentally collected) green gumball RGB values at top/middle/bottom of free fall
green_mask_top = np.uint8([[[51, 116, 18]]])
green_mask_mid = np.uint8([[[54, 86, 25]]])
green_mask_bot = np.uint8([[[68, 115, 21]]])
(lower_lim_green_top, upper_lim_green_top,
 lower_lim_green_mid, upper_lim_green_mid,
 lower_lim_green_bot, upper_lim_green_bot) = create_hsv_mask_limits(
    green_mask_top, green_mask_mid, green_mask_bot, x_hue=5, x_sat=90, x_val=90)

# Average (experimentally collected) yellow gumball RGB values at top/middle/bottom of free fall
yellow_mask_top = np.uint8([[[18, 154, 162]]])
yellow_mask_mid = np.uint8([[[30, 165, 170]]]) 
yellow_mask_bot = np.uint8([[[50, 140, 140]]])
(lower_lim_yellow_top, upper_lim_yellow_top,
 lower_lim_yellow_mid, upper_lim_yellow_mid,
 lower_lim_yellow_bot, upper_lim_yellow_bot) = create_hsv_mask_limits(
    yellow_mask_top, yellow_mask_mid, yellow_mask_bot, x_hue=5, x_sat=100, x_val=90)

# Average (experimentally collected) orange gumball RGB values at top/middle/bottom of free fall
orange_mask_top = np.uint8([[[54, 108, 178]]])
orange_mask_mid = np.uint8([[[54, 99, 149 ]]])
orange_mask_bot = np.uint8([[[42, 113, 191]]])
(lower_lim_orange_top, upper_im_orange_top,
 lower_lim_orange_mid, upper_lim_orange_mid,
 lower_lim_orange_bot, upper_lim_orange_bot) = create_hsv_mask_limits(
    orange_mask_top, orange_mask_mid, orange_mask_bot, x_hue=5, x_sat=100, x_val=100)
    
print("\nHSV Thresholds INIT Complete")

# ---------------------- Main Loop ---------------------- #

start_disk_motor(in9, in10)
gumball_counters = {"blue": 0, "green": 0, "yellow": 0, "orange": 0}
door_delays = [1100, 900, 750, 750]

for frame in camera.capture_continuous(raw_capture, format="bgr", use_video_port=True):
    startTime = time.time()
    image = frame.array

    # Convert image to HSV color space
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Masks mean computation
    mask_means = { "blue": compute_mask_mean(lower_lim_blue_top, upper_lim_blue_top,
                                       lower_lim_blue_mid, upper_lim_blue_mid,
                                       lower_lim_blue_bot, upper_lim_blue_bot),
                "green" : compute_mask_mean(lower_lim_green_top, upper_lim_green_top,
                                        lower_lim_green_mid, upper_lim_green_mid,
                                        lower_lim_green_bot, upper_lim_green_bot),
                "yellow" : compute_mask_mean(lower_lim_yellow_top, upper_lim_yellow_top,
                                         lower_lim_yellow_mid, upper_lim_yellow_mid,
                                         lower_lim_yellow_bot, upper_lim_yellow_bot),
                "orange" : compute_mask_mean(lower_lim_orange_top, upper_im_orange_top,
                                         lower_lim_orange_mid, upper_lim_orange_mid,
                                         lower_lim_orange_bot, upper_lim_orange_bot)}

    cv2.imshow("Frame", image)

    # Color dectection and door actuation
    for i, (color, mean) in enumerate(mask_means.items()):
        trigger = ((color == "blue" and mean > 0.75) or 
                   (color == "green" and mean > 0.75) or
                   (color == "yellow" and mean > 1) or
                   (color == "orange" and 0.75 < mean < 4))
        if trigger and door_states[i] == 0:
            print(color)
            gumball_counters[color] += 1
            time_door_opened = int(round(time.time() * 1000))
            time_door_should_close = time_door_opened + door_delays[i]
            open_door(*door_inputs[i])
            door_states[i] = 1

    # Close door after timeout
    if (int(round(time.time() * 1000)) >= time_door_should_close):
        for i in range(4):
            if door_states[i]:
                close_door(*door_inputs[i])
                door_states[i] = 0

    if  cv2.waitKey(1) == 27: # Exit with ESC key 
        break
    
    raw_capture.truncate(0)    
    print('Total Processing Time: ' + str(time.time()-startTime))

# Shutdown 
stop_disk_motor(in9, in10)
cv2.destroyAllWindows()
GPIO.cleanup()

for color, count in gumball_counters.items():
    print(f"# {color}: {count}")
