from picrawler import Picrawler
from robot_hat import TTS, Music, Ultrasonic
from robot_hat import Pin
from bleak import BleakScanner
import time
import math
import readchar  # Import the readchar library
from vilib import Vilib  # Import the Vilib library for camera
import json
import os
import Adafruit_SSD1306
from PIL import Image, ImageDraw, ImageFont

# Initialize OLED display
RST = None
disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)
disp.begin()
disp.clear()
disp.display()

# Create blank image for drawing.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()

tts = TTS()
music = Music()

crawler = Picrawler() 
sonar = Ultrasonic(Pin("D2"), Pin("D3"))
music.music_set_volume(100)

alert_distance = 15
speed = 150  # 150% of max speed
phone_mac_address = "DC:C4:9C:77:4E:43"  # Your phone's Bluetooth MAC address
recalibration_interval = 5  # Time in seconds to stop and recalibrate

# Initialize the orientation angle
orientation_angle = 0
camera_on = False  # Camera state
manual_control = True  # Start in manual control mode
mapping_mode = False  # Start with mapping mode off

# Map settings
map_file = "room_map.json"
map_size = (20, 20)  # 20x20 grid
map_data = [[0 for _ in range(map_size[1])] for _ in range(map_size[0])]
current_position = [10, 10]  # Start in the middle of the map

def load_map():
    global map_data
    if os.path.exists(map_file):
        with open(map_file, 'r') as f:
            map_data = json.load(f)
        print("Map loaded.")
    else:
        print("No map found. Starting with a new map.")

def save_map():
    with open(map_file, 'w') as f:
        json.dump(map_data, f)
    print("Map saved.")

def update_map(position, value):
    x, y = position
    if 0 <= x < map_size[0] and 0 <= y < map_size[1]:
        map_data[x][y] = value

def find_phone():
    try:
        devices = BleakScanner.discover()
        for device in devices:
            if device.address == phone_mac_address:
                return True
    except Exception as e:
        print(f"Error during Bluetooth scan: {e}")
    return False

def draw_needle(angle):
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    center_x = width // 2
    center_y = height // 2
    radius = min(center_x, center_y) - 5

    # Draw circle
    draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), outline=255, fill=0)

    # Calculate needle end point
    end_x = center_x + int(radius * math.cos(math.radians(angle)))
    end_y = center_y + int(radius * math.sin(math.radians(angle)))

    # Draw needle
    draw.line((center_x, center_y, end_x, end_y), fill=255)

    disp.image(image)
    disp.display()

def toggle_camera():
    global camera_on
    camera_on = not camera_on
    if camera_on:
        print("Camera turned ON")
        Vilib.camera_start()
        Vilib.display()
    else:
        print("Camera turned OFF")
        Vilib.camera_stop()

def toggle_manual_control():
    global manual_control
    manual_control = not manual_control
    if manual_control:
        print("Manual control ON")
    else:
        print("Manual control OFF")

def toggle_mode():
    global mapping_mode
    mapping_mode = not mapping_mode
    if mapping_mode:
        print("Switched to Mapping Mode")
    else:
        print("Switched to Phone Finding Mode")

def take_picture():
    timestamp = int(time.time())
    filename = f"pic_{timestamp}.jpg"
    Vilib.take_picture(filename)
    print(f"Picture taken: {filename}")

def main():
    global orientation_angle, speed, manual_control, current_position, mapping_mode
    load_map()
    start_time = time.time()
    while True:
        if not manual_control:
            if mapping_mode:
                # Mapping mode
                distance = sonar.read()
                print(f"Distance: {distance}")
                
                if distance <= alert_distance:
                    crawler.do_action('turn left angle', 3, speed)
                    orientation_angle = (orientation_angle + 90) % 360  # Update orientation
                    time.sleep(0.2)
                else:
                    crawler.do_action('forward', 1, speed)
                    current_position[1] += 1  # Update position
                    update_map(current_position, 1)
                    time.sleep(0.2)
            else:
                # Phone finding mode
                phone_found = find_phone()
                distance = sonar.read()
                print(f"Distance: {distance}, Phone Found: {phone_found}")
                
                if phone_found:
                    # Draw needle pointing towards the phone
                    draw_needle(orientation_angle)
                    
                    if distance < 0:
                        pass
                    elif distance <= alert_distance:
                        try:
                            music.sound_play_threading('./sounds/sign.wav', volume=100)
                        except Exception as e:
                            print(e)
                        crawler.do_action('turn left angle', 3, speed)
                        orientation_angle = (orientation_angle + 90) % 360  # Update orientation
                        time.sleep(0.2)
                    else:
                        crawler.do_action('forward', 1, speed)
                        current_position[1] += 1  # Update position
                        update_map(current_position, 1)
                        time.sleep(0.2)
                else:
                    # Turn left to search for the phone and update orientation
                    crawler.do_action('turn left angle', 3, speed)
                    orientation_angle = (orientation_angle + 90) % 360  # Update orientation
                    draw_needle(orientation_angle)
                    time.sleep(0.2)
            
            # Recalibrate direction periodically
            if time.time() - start_time >= recalibration_interval:
                crawler.do_action('stop', 1, speed)
                time.sleep(1)  # Pause for a moment
                start_time = time.time()  # Reset the timer

        # Keyboard controls
        key = readchar.readkey()
        if key == 'w':
            crawler.do_action('forward', 1, speed)
            current_position[1] += 1  # Update position
            update_map(current_position, 1)
        elif key == 's':
            crawler.do_action('backward', 1, speed)
            current_position[1] -= 1  # Update position
            update_map(current_position, 1)
        elif key == 'a':
            crawler.do_action('turn left', 1, speed)
            current_position[0] -= 1  # Update position
            update_map(current_position, 1)
        elif key == 'd':
            crawler.do_action('turn right', 1, speed)
            current_position[0] += 1  # Update position
            update_map(current_position, 1)
        
        # Speed controls
        if key.isdigit() and 1 <= int(key) <= 10:
            speed = int(key) * 10
            print(f"Speed set to {speed}%")

        # Toggle camera
        if key == 'c':
            toggle_camera()
            time.sleep(0.5)  # Debounce delay

        # Toggle manual control
        if key == 'm':
            toggle_manual_control()
            time.sleep(0.5)  # Debounce delay

        # Toggle mode
        if key == 't':
            toggle_mode()
            time.sleep(0.5)  # Debounce delay

        # Take picture
        if key == 'p':
            take_picture()
            time.sleep(0.5)  # Debounce delay

        save_map()

if __name__ == "__main__":
    main()
