from pygame import pypm
import array
import time
from collections import deque
import sys
from phue import Bridge

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

            
                    
#  **      **  #
## ** MAIN ** ##
#  **      **  #

if  __name__ =='__main__':
    # always call this first, or OS may crash when you try to open a stream
    pypm.Initialize()

    # wireup input/output
    midi_out, midi_in = connect_midi()

    # turn off internal LED finger tracking and enable pressure
    set_LEDs_ignore_touch(midi_out)
    enable_pressure_output(midi_out)

    b = Bridge("10.0.77.15")
    
    lastTime = None
    curTime = None
    

    while True:
        input_pos = read_touch_input(midi_in)
        if input_pos is not None:
            draw_bar(midi_out, input_pos, CURSOR_SIZE);

            curTime = time.time()
            if lastTime is None or curTime - lastTime > 0.25:
                print "Sending request, bri = %s" % (input_pos*2)
                b.set_group('all', 'bri', input_pos*2, transitiontime=1)
                lastTime = curTime
