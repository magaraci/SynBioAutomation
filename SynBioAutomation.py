"""  This script automates image acquisition from the Raspberry Pi-based
transilluminator by coordinating taking a photo with turning on the LEDs It
requires the Google Drive library to be installed and activated. To run the
script, open up a terminal and navigate to the folder in which the script is
saved. Then, run it from the command line using the following synatx:

Initialization:

    sudo python SynBioAutomation.py Initialize FolderName

        This command initializes the camera with certain settings, saves these
        settings to the disk so they can be reloaded every time the script is
        run, and creates the sub-directory in which images will be saved
        (FolderName). Running this command will take a picture called
        Initial.png, save it to FolderName, and push this file to Google Drive.

Running the TimeCourse

    sudo python SynBioAutomation.py TimeCourse

    This command loads camera settings from the disk and then takes a picture
    using these settings. The photo is saved as
    "Year_Month_Day_HourMinuteSecond.png" and is saved to the sub-directory
    FolderName specified in the Initialization. It also initializes a CRON job
    to run the script with the initialized settings every hour.

Taking a Single Phoot

    sudo python SynBioAutomation.py

    This command takes a single photo using the initialized settings and saves
    the photo as "Year_Month_Day_HourMinuteSecond.png" in the FolderName sub-
    directory. It does not adjust the CRON job.

Ending the Time Course

    sudo python SynBioAutomation.py End

    This command ends the time course by clearing the CRON job.
    
"""


import picamera # Module for the Camera
import time # Module to get current time
import cPickle as pickle # Module for object sharing
from crontab import CronTab # Module to schedule cron jobs to run in certain intervals
import os, sys # Modules that provide numerous tools to deal with filenames, paths, directories
import RPi.GPIO as GPIO # Module to access the IO ports of the Pi
import shutil # Module for high-level file operations

def begin_CRON():
    """Set an hourly CRON job to run SynBioAutomation.py"""
    minute_time = time.strftime('%M') # get the current minute value
    cron = CronTab() #Start a new cron
    job  = cron.new(command='cd ' + os.getcwd() + ' && sudo /usr/bin/python ' + os.path.realpath(sys.argv[0])) #start new job
    job.minute.on(minute_time) # Set cron job to run the script every hour on the minute that it initially ran
    job.minute.every(CronTimeSetting)
    job.enable()
    cron.write()
    return None

def init_GPIO():
    """ 
    Initialize Raspberry Pi GPIO pins.

    Sets Pin 12 (using BOARD numbering) as output and initializes to low.

    """
    GPIO.setmode(GPIO.BCM) 
    GPIO.setwarnings(False) 
    GPIO.setup(12, GPIO.OUT, initial=GPIO.LOW) 
    return None


def initialize_camera():
    """
    Fix Raspberry Pi Camera settings and initialize the Google Drive folder.

    Initializes the camera with certain settings, saves these settings to the
    disk so they can be reloaded every time the script is run, and creates the
    directory in which images will be saved. Takes a picture called Initial.png
    and pushes this file to Google Drive.
    
    """ 

    currentDirectory = os.getcwd() + '/';
    with picamera.PiCamera() as camera:
        camera.resolution = (2592, 1944)
        camera.framerate = 1
        camera.iso=100
        camera.shutter_speed = 1000000
        picamera.exposure_mode='backlight'
        #Wait for Analog Gain to settle at a value greater than 1 in order to be able to adjust the AWB Gain and to make sure the exposure settings are right
        while camera.analog_gain != 1 or camera.digital_gain != 1:
            time.sleep(0.1)
        camera.exposure_mode = 'off' 
        #To fix the exposure speed to the value of shutter speed
        g = camera.awb_gains
        camera.awb_mode = 'off'
        camera.awb_gains = (1.5, 1.5)
        camera.capture('Initial.png')
        path = pickle.load(open(currentDirectory+'path.p','rb'))
        shutil.move(currentDirectory+'Initial.png',path+'Initial.png')
        os.system('sudo -u pi /home/pi/gopath/bin/drive push -quiet -no-clobber '+path)
        
        #Pickle-dumping the values to maintain constant settings
        pickle.dump(camera.iso,open('iso.p','wb'))
        pickle.dump(camera.shutter_speed,open('shutter_speed.p','wb'))
        pickle.dump(camera.awb_gains,open('awb_gain.p','wb'))
        pickle.dump(camera.analog_gain,open('analog_gain.p','wb'))
        pickle.dump(camera.digital_gain,open('digital_gain.p','wb'))
        
    return None

def continuous_capture():

    """
    Take a picture using initialized settings and push to Google Drive.

    Loads the camera.shutter_speed, camera.iso, and camera.awb_gains values from
    pickle files dumped to the disk. Takes a picture using these settings, saves
    the file photo as a png with the name" Year_Month_Day_HourMinuteSecond" and
    saves it to the FolderName specified in the Initialization.

    """ 

    currentDirectory = os.getcwd() + '/';
    with picamera.PiCamera() as camera:
        camera.resolution = (2592, 1944)
        camera.framerate = 1
        camera.iso = pickle.load(open(currentDirectory + 'iso.p','rb'))
        camera.shutter_speed = pickle.load(open(currentDirectory+'shutter_speed.p','rb'))
        picamera.exposure_mode='backlight'
        #Waiting for Analog Gain to settle on a value greater than 1
        while camera.analog_gain != 1 or camera.digital_gain != 1:
            time.sleep(0.1)
        camera.exposure_mode = 'off'
        g=pickle.load(open(currentDirectory+'awb_gain.p','rb'))
        camera.awb_mode = 'off'
        camera.awb_gains = g
        filename = currentDirectory + time.strftime('%Y_%m_%d_%H%M%S') + '.png'
        path = pickle.load(open(currentDirectory+'path.p','rb'))
        destination = path + time.strftime('%Y_%m_%d_%H%M%S') + '.png'
        
        camera.capture(filename)
        shutil.move(filename,destination)
        os.system('sudo -u pi /home/pi/gopath/bin/drive push -quiet -no-clobber ' + path)
    return None
    
def LED_ON():
    """ Turn on the LEDs in the transilluminator. """
    GPIO.output(12, GPIO.HIGH) # Sets Pin 12 High to signal the LED on
    return None

def LED_OFF():
    """ Turn off the LEDs in the transilluminator. """
    GPIO.output(12, GPIO.LOW) # Sets Pin 12 Low to signal the LED off
    return None

if __name__=='__main__':
    init_GPIO()
    if len(sys.argv) == 3:
        if sys.argv[1] == 'Initialize':
            print('Initializing...')
            LED_ON()
            path = os.getcwd() + '/' + sys.argv[2]
            if not os.path.exists(path):
                os.makedirs(path)
            path = path + '/'
            pickle.dump(path,open('path.p','wb'))
            print('Taking Photo')
            initialize_camera()
            LED_OFF()
            print('Initialized')
        if sys.argv[1] == 'TimeCourse':
            print('Scheduling CRON Job')
            CronTimeSetting=sys.argv[2]
            begin_CRON()
            print('Taking Photo')
            LED_ON()
            continuous_capture()
            LED_OFF()
            print('Time Course Active')
    elif len(sys.argv) == 2:
        if sys.argv[1] == 'End':
            print('Ending Time Course')
            CronTab().remove_all()
            CronTab().write()
            print('Done')
    else:
        print('Taking Photo')
        LED_ON()
        continuous_capture()
        LED_OFF()
    GPIO.cleanup()
