import RPi.GPIO as GPIO # import RPi.GPIO module 
import dht11 # import dht11 module for temperature and humidity sensor
import time # import time module
import datetime # import datetime module
import telepot # import telepot module for telegram communication
from telepot.loop import MessageLoop # import telepot.loop module for telegram communication 
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton # import InlineKeyboard to use the InlineKeyboard interface
import threading # import threading module for overwriting 
import requests # import requests module

# Setup GPIO
GPIO.setmode(GPIO.BCM)  # Set the GPIO mode to BCM numbering
GPIO.setwarnings(False)  # Disable warnings
GPIO.setup(23, GPIO.OUT)  # Set GPIO pin 23 as an output (for DC motor)
GPIO.setup(26, GPIO.OUT)  # Set GPIO pin 26 as an output (for servo motor)
PWM = GPIO.PWM(26, 50)  # Initialize PWM on GPIO pin 26 at 50Hz

# Moisture sensor setup
moisture_pin = 4  # Set the GPIO pin for the moisture sensor
GPIO.setup(moisture_pin, GPIO.IN)  # Set GPIO pin 4 as an input

# Initialize DHT11 sensor instance
instance = dht11.DHT11(pin=21)  # Using GPIO pin 21 for DHT11 sensor

# Feeder usage counter
feeder_usage = 0 # Feeder usage counter initialized to zero 
last_reset = datetime.datetime.now() # reset time for feeder usage counter 
last_moisture_check = datetime.datetime.now() - datetime.timedelta(hours=3) # reset time for moisture check 3 hours 

# Global flag for motor control
motor_running = False # global flag for motor running
stop_motor = False # global flag to stop motor 

# Motor control functions
def motor_control(duration): 
    global motor_running, stop_motor # call the global variables created outside of function
    motor_running = True # this calls that we want the motor to run
    stop_motor = False # this calls for the stop_motor to continue runnign
    GPIO.output(23, 1)  # Start motor
    for _ in range(duration): # for loop 
        if stop_motor: # if loop 
            break
        time.sleep(1) # sleep for 1 second
    GPIO.output(23, 0)  # Stop motor
    motor_running = False # motor running off

def motor_10_seconds():
    motor_control(10) # duration for 10 seconds call by function

def motor_one_hour():
    motor_control(3600) # duration for 1 hour call by function

def motor_forward(chat_id): # using telegram chat ID to call the motor duration options
    keyboard = InlineKeyboardMarkup(inline_keyboard=[ # inline keyboard feature
        [InlineKeyboardButton(text='10 seconds', callback_data='motor_10_seconds')], # Inline option : 10 seconds
        [InlineKeyboardButton(text='1 hour', callback_data='motor_one_hour')], # Inline optino : 1 hour
    ])
    bot.sendMessage(chat_id, 'Select the duration to run the motor:', reply_markup=keyboard) # send message on channel to select duration

def motor_stop(): # function to stop the motor
    global stop_motor # call global variable to stop the motor
    stop_motor = True  # Signal to stop the motor immediately

def feeder_On(): # function to feed the fishes using servo motor
    global feeder_usage # call the global variable feeder_usuage which is was 0 
    PWM.start(3)  # Start PWM with a duty cycle that corresponds to the initial position
    time.sleep(1)  # Give the servo time to move
    PWM.ChangeDutyCycle(12)  # Move servo to the "feed" position
    time.sleep(1)  # Wait for the servo to reach the position
    PWM.ChangeDutyCycle(3)  # Move servo back to the initial position
    time.sleep(1)  # Wait for the servo to return
    PWM.ChangeDutyCycle(0)  # Set duty cycle to 0 to stop signal
    feeder_usage += 1 # increment the feeder_usage counter by 1 after every feeding process

# Function to get temperature and humidity data
def get_temperature_humidity(): # Get temperature
    result = instance.read() 
    if result.is_valid():
        print("Last valid input: " + str(datetime.datetime.now()))
        print("Temperature: %-3.1f C" % result.temperature)
        print("Humidity: %-3.1f %%" % result.humidity)
        time.sleep(0.5)  # short delay between reads
        return result.temperature, result.humidity
    else:
        return None, None

# Function to post temperature to ThingSpeak
def post_to_thingspeak(temperature): 
    API_KEY = 'FXWM32HNBBOHQ6YK' # API Key for thingspeak
    url = f'https://api.thingspeak.com/update?api_key={API_KEY}&field1={temperature}' # put temperature reading into thingspeak graph 
    requests.get(url)

def check_moisture(): # function to check moisture
    global last_moisture_check # call global variable last_moisture_check
    if GPIO.input(moisture_pin) == 0: # if no moisture detected 
        current_time = datetime.datetime.now()
        if (current_time - last_moisture_check).seconds >= 600: # check if there is moisture every 10 minute
            bot.sendMessage(CHAT_ID, "No moisture detected. Please refill the fish tank.")
            last_moisture_check = current_time
    if GPIO.input(moisture_pin) == 1: # if moisture detected
        bot.sendMessage(CHAT_ID, "waterlevel is good")

TOKEN = "7208472672:AAH11P-jVwK0QtSG4gCNFiov2e0hoeI7dtA" # telegram channel token
CHAT_ID = "1432292156" # telegram channel ID
bot = telepot.Bot(TOKEN) # to use the telegram bot 
AUTHORIZED_USERS = [1493171902, 1432292156] # only authorized users only two people 

def send_menu(chat_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Fan On', callback_data='fanon')], # inline keyboard to call the function fanon
        [InlineKeyboardButton(text='Fan Off', callback_data='fanoff')], # inline keyboard to call the function fanoff
        [InlineKeyboardButton(text='Feed', callback_data='feed')],# inline keyboard to call the function feeder 
        [InlineKeyboardButton(text='Feeder Usage', callback_data='usage')],# inline keyboard to call the function feeder usage
        [InlineKeyboardButton(text='Recent Temperature', callback_data='recent_temp')],# inline keyboard to call the function find recent temperature
    ])
    bot.sendMessage(chat_id, 'Please choose an action:', reply_markup=keyboard)

def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    
    if chat_id not in AUTHORIZED_USERS:
        bot.sendMessage(chat_id, "Unauthorized access.") # if unauthorized users use telegram bot will not be able to and will send messages to the bot that is not authorized
        return
    
    if content_type == 'text': 
        command = msg['text'].lower() # all commands change to lowercase
        print(f"Received command: {command}") # print out that command is recieved

        if command == '/start': # call /start to use the inline keyboard and its features
            send_menu(chat_id)
        else:
            bot.sendMessage(chat_id, "Invalid command. Use the menu to choose an action")

def on_callback_query(msg):
    global stop_motor
    query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')

    if chat_id not in AUTHORIZED_USERS:
        bot.sendMessage(chat_id, "Unauthorized access.")
        return
    
    print(f"Received callback query: {query_data}")

    if query_data == 'fanon':
        motor_forward(chat_id)
    elif query_data == 'fanoff':
        motor_stop()
        bot.sendMessage(chat_id, "Motor stopped immediately")
    elif query_data == 'motor_10_seconds':
        if motor_running:
            motor_stop()
        threading.Thread(target=motor_10_seconds).start()
        bot.sendMessage(chat_id, "Motor running for 10 seconds")
    elif query_data == 'motor_one_hour':
        if motor_running:
            motor_stop()
        threading.Thread(target=motor_one_hour).start()
        bot.sendMessage(chat_id, "Motor running for 1 hour")
    elif query_data == 'feed':
        bot.sendMessage(chat_id, "Feeding...")
        feeder_On()
        bot.sendMessage(chat_id, "Done Feeding...")
    elif query_data == 'usage':
        now = datetime.datetime.now()
        last_reset = now
        if (now - last_reset).days >= 1:
            global feeder_usage
            feeder_usage = 0
        bot.sendMessage(chat_id, f"Feeder has been used {feeder_usage} times today.")
    elif query_data == 'recent_temp':
        temperature, humidity = get_temperature_humidity()
        if temperature is not None:
            post_to_thingspeak(temperature)
            bot.sendMessage(chat_id, f"Temperature: {temperature:.1f}°C")
        else:
            bot.sendMessage(chat_id, "Failed to read temperature. Try again later.")
    else:
        bot.sendMessage(chat_id, "Invalid command. Use the menu to choose an action by using /start")

MessageLoop(bot, {'chat': handle, 'callback_query': on_callback_query}).run_as_thread()
print('Bot is listening...')

# Automatically read temperature and humidity every 30 seconds and post to ThingSpeak
while True:
    temperature, humidity = get_temperature_humidity()
    if temperature is not None:
        post_to_thingspeak(temperature)
    check_moisture()  # Check the moisture level
    time.sleep(30)  # Wait for 30 seconds before the next reading
