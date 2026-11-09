import sys
from types import ModuleType

# 1. Create a fake 'machine' module structure
mock_machine = ModuleType("machine")

class MockADC:
    def __init__(self, pin): self.pin = pin
    def read_u16(self): return 31130  # Simulates a raw reading (~22 degrees Celsius)

class MockPin:
    OUT = 1
    IN = 0
    def __init__(self, pin, mode=None): pass
    def value(self, val=None): return val

mock_machine.ADC = MockADC
mock_machine.Pin = MockPin

sys.modules["machine"] = mock_machine
sys.modules["task"] = ModuleType("task")
sys.modules["webserver"] = ModuleType("webserver")

import machine
import time
import json
import webserver
import task
import os

from datetime import datetime, date

# Dynamically locate the script's absolute folder path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(BASE_DIR, 'config.json')
run_loop = False
booted = False

class Setup:
    def __init__(self, LED_PIN):
        self.data = os.path.join(BASE_DIR, "data")
        self.telemetry = os.path.join(BASE_DIR, "logs")
        self.LED_PIN = LED_PIN
        self.board_led = OnBoardLEDSystem(self.LED_PIN, 3)
        self.date = datetime.now()
        self.is_booted = False  # Track boot success internally
        self.temp = TemperatureSystem(2)
        self.fan = FanSystem(3, 5)


    def BootSequence(self):
        self.board_led.blink()
        self.board_led.LED_On()
        self.temp.GetTemperature()
        self.fan.FanPeriod()
        self.VerificationOfInstall()
        self.LogoDisplay()
        self.is_booted = True  # Set status flag to true
        return True

    def CreateUser(self):
        username = input(f"Username: ")
        password = input(f"Password: ")
        with open(config_file, "r") as file:
            data = json.load(file)
            
        if "USER" not in data:
            data["USER"] = {}
            
        data["USER"]["USER_NAME"] = str(username)
        data["USER"]["USER_PASSWORD"] = str(password)
        
        with open(config_file, "w") as file:
            json.dump(data, file, indent=4)
            
        print(f"User saved: {data['USER']}")

    def UserVerification(self):
        username = input(f"Username: ")
        password = input(f"Password: ")
        with open(config_file, "r") as file:
            data = json.load(file)
            
        if "USER" not in data:
            data["USER"] = {}
            
        if str(username) == data["USER"]["USER_NAME"]:
            if str(password) == data["USER"]["USER_PASSWORD"]:
                print(f"User Verified")
                print(f"Hello {data["USER"]["USER_NAME"]}")
    def CreateDirectory(self):
        for directory in [self.data, self.telemetry]:
            try:
                os.mkdir(directory)
                print(f"directory Created: {directory}")
            except OSError:
                print(f"directory already exists: {directory}")

    def VerificationOfInstall(self):
        with open(config_file, "r") as file:
            data = json.load(file)

        # Defaults to False (boolean) if missing
        initialised_status = data.get("initialised", False)

        if initialised_status is False:
            data['initialised'] = True  # Set to boolean True
            with open(config_file, "w") as file:
                json.dump(data, file, indent=4)
            self.CreateDirectory()
            print(f"Setting Up Device")
            self.log = Log((f"Created: {self.date}\n"), self.telemetry, "Device-Log")
            self.log.CreateFiel()
            self.CreateUser()
        if initialised_status is True:
            print(f"Booting Device")
            self.log = Log((f"Booted: {self.date}\n"), self.telemetry, "Device-Log")
            self.log.EditFiel()
            self.UserVerification()


    def VerificationOfBoot(self):
        if self.is_booted:
            print(f"Boot Successful")
            
            # FIX: Load config here so EnvironmentLoop receives the latest file updates
            with open(config_file, "r") as file:
                current_config = json.load(file)
                
            # FIX: Pass both 'running' status AND the config dictionary object
            self.environment = EnvironmentLoop(running=True, config=current_config)
            self.environment.Loop()
        else:
            print(f"Boot Failed")
            print(f"Shutting down Device")

    def LogoDisplay(self):
        print(
"""
                       XXXXXXX   
                     XX       XX 
                    X   ────┬┐  X
       XXXXXXXXXXXXXXXXXXXX┌┼┘  X
       X  X         X     X└┘   X
       X   XX   \.   XX   X   XX 
       X     X  '\'    XXXXXXX   
       X      XX '\`.     X      
       X `\     X '\ \.   X      
       X   `.    XX''''   X      
      XXX   '\     X      X      
     X X X  '\_     XX    X      
    X  X  X   ''- .   X   X      
   X│  X   X      `.      X      
  X └┐ XXXXXXXXXXXXXXXXXXXX      
 X   └─      X                   
XXXXXXXXXXXXXXX                  
""")

class DignosticLEDSystem:
    def __init__(self, pin, LED_NUM):
        self.pin = pin
        self.LED_NUM = LED_NUM

class OLED_DISPLAY:
    def __init__(self):
        pass

class Log:
    def __init__(self, data, location, file_name):
        self.data = data
        self.location = location
        self.file_name = file_name

    def CreateFiel(self):
        self.file_path = os.path.join(self.location, f"{self.file_name}.txt")
        with open(self.file_path, "w") as f:
            f.write(str(self.data))

    def EditFiel(self):
        self.file_path = os.path.join(self.location, f"{self.file_name}.txt")
        with open(self.file_path, "a") as f:
            f.write(str(self.data))  

class FanSystem:
    def __init__(self, pin, delay):
        self.pin = pin
        self.delay = delay
        self.FAN = machine.Pin(self.pin, machine.Pin.OUT)
    def FanHigh(self):
        self.FAN.value(1)
    def FanLow(self):
        self.FAN.value(0)
    def FanPeriod(self):
        self.FAN.value(1)
        time.sleep(self.delay)
        self.FAN.value(0)

class TemperatureSystem:
    def __init__(self, pin):
        self.pin = pin
        self.sensor = machine.ADC(self.pin)
        self.conversion = 3.3 / 65535

    def GetTemperature(self):
        # Changed while loop to handle single queries safely
        self.raw_value = self.sensor.read_u16()
        self.voltage = self.raw_value * self.conversion
        self.temperature = 27 - (self.voltage - 0.706) / 0.001721
        print(f"Temperature: {self.temperature:.2f} ℃")
        time.sleep(1)

    def GetTemperatureLoop(self, running):
            self.running = running
            # Changed while loop to handle single queries safely
            while True:
                self.raw_value = self.sensor.read_u16()
                self.voltage = self.raw_value * self.conversion
                self.temperature = 27 - (self.voltage - 0.706) / 0.001721
                print(f"Temperature: {self.temperature:.2f} ℃")
                if not self.running:
                    break
                time.sleep(1)

class OnBoardLEDSystem:
    def __init__(self, pin, delay):
        self.pin = pin
        self.delay = delay
        self.LED = machine.Pin(self.pin, machine.Pin.OUT)
    
    def LED_On(self):
        print(f"OnBoardLED: {self.LED.value}")
        self.LED.value(1)

    def LED_Off(self):
        print(f"OnBoardLED: {self.LED.value}")
        self.LED.value(0)

    def blink(self):
        self.LED.value(1)
        print(f"OnBoardLED: blink")
        print(f"OnBoardLED: {self.LED.value}")
        time.sleep(self.delay)
        self.LED.value(0)
        print(f"OnBoardLED: {self.LED.value}")

class EnvironmentLoop:
    def __init__(self, running, config):
        self.running = running
        self.config = config
        self.temp_pin = self.config["Temperature_Sensor"]["sensor_pin"]
        self.temp_system = TemperatureSystem(self.temp_pin)

    def Loop(self):
        print(f"Initialising Environment")
        print(f"Loop Status: {self.running}")
        print("Type 'help' to see available terminal diagnostic commands.\n")
        
        while self.running:
            user_input = input(f":-> ").strip().lower()
            
            if user_input == "help":
                print("Available commands: 'temp', 'info', 'exit'")
                
            elif user_input == "temp":
                self.temp_system.GetTemperature(running=False)
                
            elif user_input == "info":
                print(f"Active User: {self.config['USER']['USER_NAME']}")
                print(f"OLED Configuration: SDA Pin {self.config['OLED_LCD']['SDA']}, SCL Pin {self.config['OLED_LCD']['SCL']}")
                
            elif user_input == "exit":
                print("Exiting runtime environment loop.")
                self.running = False
                
            elif user_input == "":
                continue
            else:
                print(f"Unknown command: '{user_input}'. Type 'help' for options.")


setup = Setup(1)
log = Log("Hello world", "data", "hello.md")
setup.BootSequence()
setup.VerificationOfBoot()
