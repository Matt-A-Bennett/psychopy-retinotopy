# -*- coding: utf-8 -*-
"""
Created by Matthew A. Bennett (Fri May 24 12:59:19 2019)
Matthew.Bennett@glasgow.ac.uk
"""

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Retinotopic mapping: eccentricity

Author: Michele Svanera
Nov. 2017
"""

################################################################################################################
## Imports

from __future__ import division

from psychopy import visual, event, core, logging
#from psychopy import gui  #fetch default gui handler (qt if available)
from psychopy import prefs as pyschopy_prefs

#from itertools import cycle  # import cycle if you want to flicker stimuli
#from psychopy.misc import pol2cart
import copy
import numpy as np
import os
#import matplotlib.pyplot as plt
from datetime import datetime as dt
from time import gmtime, strftime
import threading


################################################################################################################
## Paths and Constants

EPSILON = 1e-5
serif = ['Times', 'Times New Roman']
sans = ['Gill Sans MT', 'Arial', 'Helvetica', 'Verdana']

# Button box
Initial_code = 16777200
Button_coding = [-1,-2,-3,-4,-5]            #red,yellow,green,blue,white(i.e. trigger)
IsMRI = 0                                   #MRI inverses the bit polarities
scanner_message = "Waiting for the scanner..."

# Experiment details
Fullscreen = True
Dir_save = 'D:/Mucklis_lab/Retinotopic_mapping/out/'
Log_name = 'LogFile.log'
Frames_durations_name = 'frames_durations.npy'
Fps_update_rate = 1                             # sec

# Eccentricity, i.e. circular_crown
Flash_period = 0.2                              # seconds for one B-W cycle (ie 1/Hz)
Mask_positions_number = 10000                   # Define the resolution (smoothness) of the movement
Cycle_duration = 64                             # seconds for one passage
Cycles_number = 8                               # How many cicles
Thickness_circular_crown = 10                   # Pixels
Thickness_multiplication_factor = np.linspace(1.,30.,num=Mask_positions_number)
Eccentricity_size = 1.25                         # x resY

# Fixation
Rotating_cross = False
Color_change_cross = False
Color_change_rate = 2                           # sec
Rotation_cross_rate = 0.05                      # revs per sec

# Spyder network
Spyder_grid = True
Spyder_rings = 4
Web_size = (1.,1.)

# External cover
External_ring_size = Eccentricity_size * 2

Pre_post_stimuli_fixation_time = 12.           # sec.
Total_time = Cycles_number * Cycle_duration


def outRingTimeFuntion(t):
    return 0.12 * t**2 + 0.25 * t + 5

#Inner_ring_size = Outer_ring_size*0.88^4


################################################################################################################
## Function


def screenCorrection(mywin,x):
    resX = mywin.size[0]
    resY = mywin.size[1]
    aspect = float(resX) / float(resY)

    if(Fullscreen == True):
        new = x / aspect
    else:
        new = x
    return(new)


def createOutFolder(path_out):
    if not os.path.exists(path_out):
        try:
            os.makedirs(path_out)
        except Exception as e:
            print('Problem with creating an *out* folder, check permissions: '+e)
    else:
        n_folder_name = 1
        path_out_new = path_out + "_" + str(n_folder_name)
        while(os.path.exists(path_out_new) is True):
            n_folder_name += 1
            path_out_new = path_out + "_" + str(n_folder_name)
        try:
            os.makedirs(path_out_new)
        except Exception as e:
            print('Problem with creating an *out* folder, check permissions: '+e)
        path_out = path_out_new
    path_out += '/'

    return path_out


class buttonBoxThread(threading.Thread):
    def __init__(self, thread_id, name):
        threading.Thread.__init__(self)

        self.stimulus_onset_time = 0
        self.local_status = 0
        self.mask = 0x0000 if IsMRI == 0  else 0x001f

        # Open comunication with Vpixx
        DPxOpen()

        #Select the correct device
        DPxSelectDevice('PROPixxCtrl')
        DPxSetMarker()
        self.stimulus_onset_time = DPxGetMarker()
        DPxEnableDinDebounce()              # Filter out button bounce
        self.local_status = DPxSetDinLog()        # Configure logging with default values
        DPxStartDinLog()
        DPxUpdateRegCache()

        # Thread infos
        self.thread_id = thread_id
        self.name = name

        # Every button has: its value {0,1} and time when it changed (as datetime)
        self.button_state = {'time': np.array([dt.now()]*5), 'state': np.zeros((5,),dtype=np.int8)}
        self.button_state['state'][-1] = 1
        self._stop_event = threading.Event()

    def run(self):
        logging.data("Starting " + self.name)

        initial_values = DPxGetDinValue()
        logging.data('Initial button box digital input states = ' + "{0:016b}".format(initial_values) + " (int=%d)".format(initial_values))

        while(True):
            DPxUpdateRegCache()
            DPxGetDinStatus(self.local_status)

            if self.local_status['newLogFrames'] > 0 :           #Something happened
                data_list = DPxReadDinLog(self.local_status)
                self.button_state = self.updateStateButton(self.button_state,data_list)

            if(self.stopped()):
                break

        logging.data("Exiting " + self.name)

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    # Take in input a state and check what is changed
    def updateStateButton(self,button_state,data_list):

        for j in range(len(data_list)):
            j_value = bin(data_list[j][1] ^ self.mask)

            # Check every button
            for i_button in range(len(button_state['state'])):
                i_button_detected_value = int(j_value[Button_coding[i_button]])
                if(i_button_detected_value != button_state['state'][i_button]):
                    button_state['state'][i_button] = i_button_detected_value
                    button_state['time'][i_button] = dt.now()

        return button_state




################################################################################################################
## Main function

def main(win, globalClock):

    all_changes = []
    size_ecc_pxl = resY * Eccentricity_size

    ################################ Stimuli prepation ################################

    # Make two wedges (in opposite contrast) and alternate them for flashing
    grating_texture = np.tile([[1,-1],[-1,1]], (8,8))#(4,64))
    wedge1 = visual.RadialStim(win, tex=grating_texture, color=1, units='pix', size=size_ecc_pxl,
                               radialCycles=1, angularCycles=2, interpolate=False,
                               autoLog=False)       #, mask=radius)
    wedge2 = copy.copy(wedge1)
    wedge2.color = -1

    position_from_center = np.linspace(0,size_ecc_pxl,Mask_positions_number).reshape((-1,1))


    # fixation cross
    fixation = visual.ShapeStim(win,vertices=((0,-1),(0,1),(0,0),(-1,0),(1,0)),lineWidth=4, units="pix",
        size=(20,20),closeShape=False,lineColor='red',autoDraw=True)

    # Spyder network
    web_circle = visual.Circle(win=win,radius=1,edges=200,units='norm',pos=[0, 0],lineWidth=1,opacity=1,interpolate=True,
                            lineColor=[1.0, 1.0, 1.0],lineColorSpace='rgb',fillColor=None,fillColorSpace='rgb')
    web_dimension = (screenCorrection(win,Web_size[0]),Web_size[1])
    web_line = visual.Line(win,name='Line',start=(-1.4, 0),end=(1.4, 0),pos=[0, 0],lineWidth=1,
                           lineColor=[1.0, 1.0, 1.0],lineColorSpace='rgb',opacity=1,interpolate=True)

    # DEBUG stimuli
    if DEBUG_MODE:
        fps_text = visual.TextStim(win, units='norm', height=0.05,pos=(-0.98, +0.93), text='starting...',
                                  font=sans, alignHoriz='left', alignVert='bottom', color='yellow')
        fps_text.autoDraw = True

        orientation_details_string = visual.TextStim(win, text = u"eccentricity..", units='norm', height=0.05,
                                             pos=(0.95, +0.93), alignHoriz='right', alignVert='bottom',
                                             font=sans, color='yellow')
        orientation_details_string.autoDraw = True

    # External Aperture (black ring)
    external_aperture_size = tuple([screenCorrection(win,External_ring_size),External_ring_size])
    external_aperture = visual.Aperture(win, size=external_aperture_size, shape='circle')
    external_aperture.enabled = False


    ################################ Definitions/Functions ################################

    ## handle Rkey presses each frame
    def escapeCondition():
        for key in event.getKeys():
            if key in ['escape', 'q']:
                return False
        return True


    ################################ Animation starts ################################
    # display instructions and wait
    message1 = visual.TextStim(win, pos=[0,0.5],text='Hit a key when ready.')
    message1.draw()
    fixation.draw()
    win.flip()#to show our newly drawn 'stimuli'
    event.waitKeys()                #pause until there's a keypress

    # Scanner trigger wait
    message3 = visual.TextStim(win,pos=[0,0.25],text=scanner_message,font=serif,alignVert='center',
                               wrapWidth=1.5)
    message3.size = .5
    message3.draw()
    win.flip()

    if BUTTON_BOX:
        button_state = button_thread.button_state
        while 1:
            if(button_state['state'][-1]==0):
                break
    else:
        event.waitKeys()    #pause until there's a keypress


    # Wait Pre_post_stimuli_fixation_time before stimuli
    # Spyder network
    if Spyder_grid:
        for i_dim in range(Spyder_rings):
            web_circle.setSize(tuple([x*(i_dim+1) * 1./Spyder_rings for x in web_dimension]))
            web_circle.draw()
        for i_dim in range(2):
            web_line.setOri(i_dim * 90)
            web_line.draw()
    win.flip()
    core.wait(Pre_post_stimuli_fixation_time)


    t = last_fps_update = i_cycle = new_record = 0
    break_flag = True
    globalClock.reset()
    inizio = globalClock.getTime()
    logging.data('First cycle. Number %d/%d at %f (sec.)' % (i_cycle+1,Cycles_number,inizio))

    while (globalClock.getTime() < Total_time and break_flag==True):
        t = globalClock.getTime()

        # Spyder network
        if Spyder_grid:
            for i_dim in range(Spyder_rings):
                web_circle.setSize(tuple([x*(i_dim+1) * 1./Spyder_rings for x in web_dimension]))
                web_circle.draw()
            for i_dim in range(2):
                web_line.setOri(i_dim * 90)
                web_line.draw()

        # External ring
        external_aperture.enabled = True

        if t % Flash_period < Flash_period / 2.0:  # more accurate to count frames
            stim = wedge1
        else:
            stim = wedge2

        # Prepare moving mask
        if (t >= ((i_cycle+1)*Cycle_duration)):
            logging.data('Change orientation. Number %d/%d at %f (sec.)' % (i_cycle+1,Cycles_number,t))
            new_record = globalClock.getTime() - sum(all_changes)
            all_changes.append(new_record)
        i_cycle = int(t/Cycle_duration)
        crown_pos_indx = int((Mask_positions_number / Cycle_duration/2) * (t % Cycle_duration))
        ## Try to understand when it changes and save it
        mask_begin = int(position_from_center[crown_pos_indx,0])
        mask_end = int(position_from_center[crown_pos_indx,0] + Thickness_multiplication_factor[crown_pos_indx] * Thickness_circular_crown)

        annulus_mask = np.zeros((int(size_ecc_pxl/2),1))
        annulus_mask[mask_begin : mask_end] += 1        #int(mask_end if mask_end <= size_ecc_pxl else size_ecc_pxl)] += 1
        stim.setMask(annulus_mask)
        stim.draw()


        # Fixation
        if Rotating_cross:
            fixation.ori = t * Rotation_cross_rate * 360.0  # set new rotation
        if Color_change_cross:
            if t % Color_change_rate < Color_change_rate / 2.0:  # more accurate to count frames
                fixation.lineColor = 'red'
            else:
                fixation.lineColor = 'green'

        external_aperture.enabled = False

        if DEBUG_MODE:
            if t - last_fps_update > Fps_update_rate:         # update the fps text every second
                fps_text.text = "%.2f fps" % win.fps()
                last_fps_update += 1
            orientation_details_string.text = 'Pass: %d/%d at %.3f (sec.)' % (i_cycle+1,Cycles_number,np.sum(all_changes))

        win.flip()
        break_flag = escapeCondition()
        if break_flag == False: break


    logging.data('Total time spent: %.6f' % (globalClock.getTime() - inizio))
    logging.data('Every frame duration saved in %s' % (path_out+Frames_durations_name))
    logging.data('All durations: ' + str(all_changes))
    logging.data('Mean: ' + str(sum(all_changes)/(len(all_changes)+EPSILON)))

    if DEBUG_MODE:
        orientation_details_string.text = 'Ended at %.3f (sec.)' % (globalClock.getTime())

    win.flip()
    # Wait Pre_post_stimuli_fixation_time after stimuli
    core.wait(Pre_post_stimuli_fixation_time)
    return




if __name__ == "__main__":

    # Experiment variables
    today_date = dt.today().strftime('%Y-%m-%d')        # Date (mm/dd/yy)
    operator = 'MS'                                     # Operator
    DEBUG_MODE = False                                   # Debug mode
    BUTTON_BOX = True                                  # Button box monitoring
    subject_code = 'NIA14'                              # Subject-code
    subject_age = 18                                    # Age
    subject_gender = 'female'                           # Gender

    # Prepare out folder
    path_out = Dir_save + today_date + '_' + subject_code + '_ecc'
    path_out = createOutFolder(path_out)

    if not os.path.exists(Dir_save):
        os.makedirs(Dir_save)
    globalClock = core.Clock()

    # Set the log module to report warnings to the standard output window
    logging.setDefaultClock(globalClock)
    logging.console.setLevel(logging.WARNING)
    lastLog=logging.LogFile(path_out+Log_name,level=logging.DATA,filemode='w',encoding='utf8')
    logging.data("------------- " + strftime("%Y-%m-%d %H:%M:%S", gmtime()) + " -------------")
    logging.data(pyschopy_prefs)
    logging.data("Saving in folder: " + path_out)
    logging.data("Operator: " + operator + "\n")
    logging.data("Subject. Code: " + subject_code + " - Age: " + str(subject_age) + " - Gender: " + subject_gender)
    logging.data('***** Starting *****')

    # Create and start buttonBox thread
    if BUTTON_BOX:
        from pypixxlib._libdpx import DPxOpen, DPxSelectDevice, DPxSetMarker, \
            DPxUpdateRegCache, DPxGetMarker, DPxEnableDinDebounce, DPxGetDinValue, \
            DPxSetDinLog, DPxStartDinLog, DPxGetDinStatus, DPxReadDinLog

        button_thread = buttonBoxThread(1, "button box check")
        button_thread.start()

    # Start window
    win = visual.Window([500,500], monitor="mon", screen=1, units="norm", fullscr=Fullscreen,
                        allowStencil=True) # norm
    resX,resY = win.size
    win.recordFrameIntervals = True

    # Main stimulation
    try:
        main(win, globalClock)
    except Exception as e:
        logging.log(e,level=logging.ERROR)

    # Stop buttonBox thread
    if BUTTON_BOX:
        button_thread.stop()

    logging.data('Overall, %i frames were dropped.' % win.nDroppedFrames)
    np.save(path_out+Frames_durations_name,win.frameIntervals[1:])

    logging.data('***** End *****')

    win.close()
    core.quit()


































