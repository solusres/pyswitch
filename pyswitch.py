#!/usr/bin/python
# -*- coding: utf-8 -*-

from pygame import pypm
import array
import time
from collections import deque
import sys
import phue
import threading

#
# BEGIN UTILS PULLED FROM VMeter.net Python Demos
# http://vmeter.net/controlling-individual-vmeter-leds-via-midi-binary-clock-game-of-life-demos/
#

INPUT=0
OUTPUT=1

def print_devices(InOrOut):
    for loop in range(pypm.CountDevices()):
        interf,name,inp,outp,opened = pypm.GetDeviceInfo(loop)
        if ((InOrOut == INPUT) & (inp == 1) |
            (InOrOut == OUTPUT) & (outp ==1)):
            print loop, name," ",
            if (inp == 1): print "(input) ",
            else: print "(output) ",
            if (opened == 1): print "(opened)"
            else: print "(unopened)"
    print

def send_array(array, MidiOut):
    # assuming 38 length array
    # need to split array into (6) 7bit chunks
    # Individual LED control is sent to the aftertouch MIDI command and channels 14, 15 and 16.
    # Each of the data bytes transmit 7 LED states.
    bytes = [0,0,0,0,0,0]
    bytes[0] = array[0] | array[1]<<1 | array[2]<<2 | array[3]<<3 | array[4]<<4 | array[5]<<5 | array[6]<<6
    bytes[1] = array[7] | array[8]<<1 | array[9]<<2 | array[10]<<3 | array[11]<<4 | array[12]<<5 | array[13]<<6
    bytes[2] = array[14] | array[15]<<1 | array[16]<<2 | array[17]<<3 | array[18]<<4 | array[19]<<5 | array[20]<<6
    bytes[3] = array[21] | array[22]<<1 | array[23]<<2 | array[24]<<3 | array[25]<<4 | array[26]<<5 | array[27]<<6
    bytes[4] = array[28] | array[29]<<1 | array[30]<<2 | array[31]<<3 | array[32]<<4 | array[33]<<5 | array[34]<<6
    bytes[5] = array[35] | array[36]<<1 | array[37]<<2
    MidiOut.WriteShort(0xAD,bytes[0],bytes[1])
    MidiOut.WriteShort(0xAE,bytes[2],bytes[3])
    MidiOut.WriteShort(0xAF,bytes[4],bytes[5])
    
def set_LEDs_ignore_touch(MidiOut):
    # this causes the LEDs to no respond to touch, only MIDI input.
    MidiOut.WriteShort(0xB0,119,107) 

def enable_on_off_output(MidiOut):
    # now the VMeter will send 127 via ctrl #17 when touched,
    # and 0 when released. 119 disables.
    MidiOut.WriteShort(0xB0,119,120)

def send_column(MidiOut,height):
    # send a column of height from 0 to 127
    MidiOut.WriteShort(0xB0,20,height)

def enable_pressure_output(MidiOut):
    MidiOut.WriteShort(0xB0,119,122)

    
def draw_bar(MidiOut,height,size):
    # draws a bar centered at height position with a given size.
    # clear the deque - set all LEDs to off
    for i in range(38):
        led_array_deque[i] = 0
    cursor_pos = int(float(height) / 127.0 * 37.0)
    lower_limit = cursor_pos - size / 2
    if lower_limit < 0:
        lower_limit = 0
    upper_limit = cursor_pos + size / 2
    if upper_limit > 37:
        upper_limit = 37
    i = lower_limit
    while i <= upper_limit:
        led_array_deque[i] = 1
        i = i + 1
    send_array(led_array_deque, MidiOut)

#
# END UTILS
#

# command constants
CONTROL = 0xB0

# output controller constants--used when reading output from VMeter
TOUCH_POS = 20
ON_OFF = 17
PRESSURE = 18

# input constants--used when sending input to VMeter


# global LED deque
led_array = [1,0,1,0,1,0,1,0,1,0,
             1,0,1,0,1,0,1,0,1,0,
             1,0,1,0,1,0,1,0,1,0,
             1,0,1,0,1,0,1,0]
led_array_deque = deque(led_array)

CURSOR_SIZE = 2

REQUEST_DELAY = 0.1 # in seconds

BRIDGE_IP = "192.168.1.112"


def connect_midi():
    # connect MIDI input and output streams
    output_device = None
    input_device = None
    
    if len(sys.argv) > 2:
        output_device = int(sys.argv[1])
        input_device = int(sys.argv[2])
    else:
        print_devices(OUTPUT)
        output_device = int(raw_input("Type output number: "))

        print_devices(INPUT)
        input_device = int(raw_input("Type input number: "))

    out, in_ = (pypm.Output(output_device, 0), pypm.Input(input_device))

    print
    print "MIDI Connected."
    print

    return (out, in_)

def translate_midi(midi_data):
    pass # maybe turn the data into something human-readable someday

def read_touch_input(midi_in):    
    if midi_in.Poll():
        midi_data = midi_in.Read(1)[0][0]
        if midi_data[0] == CONTROL:
            if midi_data[1] == TOUCH_POS:
                return int(midi_data[2])

    return None

#def set_all(property_, value):
    #for i in range(1,6):
     #   b.set_light(i, property_, 
    
class MidiReader(threading.Thread):
    def __init__(self, control, interval):
        threading.Thread.__init__(self)
        self.name = "thread-MidiReader"
        self.setDaemon(True)
        self.killed = False
        self.control = control
        self.interval = interval

    def run(self):
        while not self.killed:
            time.sleep(self.interval)
            self.control.read()

    def stop(self):
        self.killed = True


class HueUpdater(threading.Thread):
    def __init__(self, control, interval):
        threading.Thread.__init__(self)
        self.name = "thread-HueUpdater"
        self.setDaemon(True)
        self.killed = False
        self.control = control
        self.interval = interval

    def run(self):
        while not self.killed:
            time.sleep(self.interval)
            self.control.update()

    def stop(self):
        self.killed = True

#  **                  **  #
## ** CONTROLLER CLASS ** ##
#  **                  **  #

class Switch:

    def read(self):
        input_pos = read_touch_input(self.midi_in)
        if input_pos is not None:
            draw_bar(self.midi_out, input_pos, CURSOR_SIZE)
            self.brightness = input_pos*2
            #print "Read   : %s" % self.brightness
            self.dirty = True

    def update(self):
        if self.dirty:
            bri = self.brightness
            self.dirty = False
            #print "Update : Sending request, bri = %s" % bri
            
            if bri == 0:
                self.lights.on = False
            else:
                # transitionTime is in deciseconds!!
                command = {'bri' : bri, 'on' : True}
                self.b.set_group(0, command, transitiontime=5)


    def __init__(self):
        # always call this first, or OS may crash when you try to open a stream
        pypm.Initialize()
    
        # wireup input/output
        # TODO : pull MIDI control into separate class
        self.midi_out, self.midi_in = connect_midi()
        
        # turn off internal LED finger tracking and enable pressure
        set_LEDs_ignore_touch(self.midi_out)
        enable_pressure_output(self.midi_out)
        
        # TODO : use upnp to get the bridge IP
        #      : phue attempts to do this, but fails in httplib...
        self.b = phue.Bridge(BRIDGE_IP)
        
        # initialize "all" group
        self.lights = phue.AllLights(bridge=self.b)

        # initialize internal state
        self.brightness = self.lights.brightness
        self.dirty = False

        self.reader = MidiReader(self, interval=.001)
        self.reader.start()

        self.updater = HueUpdater(self, interval=.1)
        self.updater.start()

        for i in range(38):
            led_array_deque[i] = 0

        send_array(led_array_deque, self.midi_out)

        for i in range(19,38):
            led_array_deque[i] = 1
            led_array_deque[38-1-i] = 1
            send_array(led_array_deque, self.midi_out)
            time.sleep(.05)
        
        draw_bar(self.midi_out, self.brightness/2, CURSOR_SIZE)

# CONTROLLER CLASS END #        
             



#  **      **  #
## ** MAIN ** ##
#  **      **  #

if  __name__ =='__main__':
    Switch()
    while True:
        time.sleep(10000)
