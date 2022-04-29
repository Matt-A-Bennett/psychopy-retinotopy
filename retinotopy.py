# -*- coding: utf-8 -*-
"""
Retmap Experiment - can do Polar, Ecc and Bars separately or simultaneously.
To make it fill the whole screen, I would increase the size parameter in
visual.ImageStim (around line 450) beyond 2 (2 = 'max screen size' since the
screen coords go from 1 to -1). it would be neccesary to increase the density
of the checkerboards to account for the zoom in...
Created by Matthew A. Bennett (Fri May 24 12:52:37 2019)
Matthew.Bennett@glasgow.ac.uk
"""

#%% =============================================================================
# imports
from psychopy import core, visual, event, gui
import numpy as np
import random
from PIL import Image, ImageDraw
from scipy import ndimage
import os
import pathlib
# import matplotlib.pyplot as plt

# from vipixx_something_or_other import button_thread

#%% =============================================================================
# paths and definitions

flicker_rate = 4 # in Hz of the checkerboard reversals
flicker_rate = 1/flicker_rate
switch = True # switch will oscillate at flicker_rate to determine when to invert

# chance of rotation every N secs
fixation_rotate_rate = 2
# we can alternate between fixation cross orientation as a subject task
fixation_orientations = (0, 45)

# the trigger for the scanner at Brussels is 'z'
scanner_trigger = 'z'

# this will appear just before C keypress and requires button 1 to be pressed move on
insructions_to_subjects = ''' \n\n\nKeep your eyes on the red cross in the center at
all times.

When the red cross rotates, press button 1.

Press 1 to continue.'''

screen_size = 768 # in pix
screen_centre = screen_size/2

wedge_width = 45 # in degrees

# the outer radius of the ecc ring will be the inner radius multiplied by this factor
ring_width = 1.5

bar_width = 100 # in pixels

# spiderweb as background
spiderweb_grid = True
spiderweb_total_rings = 4
web_size = (1.,1.) # prportion of screen

#%% =============================================================================
# setup

dialog_info = gui.Dlg(title="Retmapping")
dialog_info.addField('sub_id:', 'SUB01')
dialog_info.addField('run_polar:', choices=["No", "Yes"])
dialog_info.addField('run_ecc:', choices=["No", "Yes"])
dialog_info.addField('run_bars:', choices=["No", "Yes"])
dialog_info.addField('pa_cycles:', 18)
dialog_info.addField('pa_cycle_duration:', 42.667)
dialog_info.addField('ecc_cycles:', 15)
dialog_info.addField('ecc_cycle_duration:', 51.333)
dialog_info.addField('bar_sweeps:', 16)
dialog_info.addField('bar_sweep_reps:', 1)
dialog_info.addField('bar_sweep_duration:', 20)
dialog_info.addField('baseline_duration:', 12)
dialog_info.addField('save_log:', choices=['No', 'Yes'])
dialog_info.addField('export_masks:', choices=['No', 'Yes'])
dialog_info.addField('export_dir:', 'exported')
dialog_info.addField('export_rate_ms:', 200)

# get the fieldnames use to use as keys in a dictionary
keys = dialog_info.inputFieldNames
# strip away colon
keys = [x[:-1] for x in keys]

# show dialog and wait for OK or Cancel
dialog_info = dialog_info.show()

#dialog_info = ['SUB01', 'Yes', 'No', 'No', '18', '42.667', '15', '51.333', '16', '20', '12', 'No']

# combine the list of keys with the input from dialog_info into a dictionary
setup = dict(zip(keys, dialog_info[:]))

# if we're going to export the stimulus masks (needed for computing prf models)
# the check how many images would be exported at the requested rate and throw
# and error if it is over 10'000
export_im_dir = setup['export_dir']
export_rate = setup['export_rate_ms']
if setup['export_masks'] == 'Yes':
    pa_time, ecc_time, bar_time = 0, 0, 0
    if setup['run_polar'] == 'Yes':
        pa_time += setup['pa_cycles']*setup['pa_cycle_duration']
    if setup['run_ecc'] == 'Yes':
        ecc_time += setup['ecc_cycles']*setup['ecc_cycle_duration']
    if setup['run_bars'] == 'Yes':
        bar_time += setup['bar_sweeps']*setup['bar_sweep_reps']*setup['bar_sweep_duration']

    total_time = max([pa_time, ecc_time, bar_time])
    if (total_time*1000)/export_rate > 9900:
        fastest_rate = round((total_time*1000)/10000) - 1

        print(f'\n\n ERROR: You set the export rate too high - at the requested \
rate, there would be over 10000 images exported. Please \
choose a lower rate (the fastest allowable rate given the \
length of this run is about: {fastest_rate} ms)\n\n')
        logfile.close()
        win.close()
        core.quit()

    if not os.path.exists(export_im_dir):
        pathlib.Path(f"{export_im_dir}").mkdir(parents=True)
        paramsfile = open(f'''{export_im_dir}/settings_used_when_generating_masks''', 'w')
    paramsfile.write(f''' sub_id: {setup['sub_id']}\n run_polar: {setup['run_polar']}\n run_ecc: {setup['run_ecc']}\n run_bars: {setup['run_bars']}\n pa_cycles: {setup['pa_cycles']}\n pa_cycle_duration: {setup['pa_cycle_duration']}\n ecc_cycles: {setup['ecc_cycles']}\n ecc_cycle_duration: {setup['ecc_cycle_duration']}\n bar_sweeps: {setup['bar_sweeps']}\n bar_sweep_reps: {setup['bar_sweep_reps']}\n bar_sweep_duration: {setup['bar_sweep_duration']}\n baseline_duration: {setup['baseline_duration']}\n save_log: {setup['save_log']}\n export_masks: {setup['export_masks']}\n export_dir: {setup['export_dir']}\n export_rate_ms: {setup['export_rate_ms']}''')
    paramsfile.close()

if setup['save_log'] == 'Yes':
    logfile = open(f'''{setup['sub_id']}_PA_{setup['run_polar']}_Ecc_{setup['run_ecc']}_Bars_{setup['run_bars']}_logfile.csv''', 'w')
    logfile.write('Subject ID:, Run Polar:, Run Ecc:, Run Bars:, Polar no. of cycles:, Polar cycle duration:, Eccentricity no. of cycles:, Eccentricity cycle duration:, Bar no. of sweeps:, Bar sweep duration:\n''')
    logfile.write(f'''{setup['sub_id']}, {setup['run_polar']}, {setup['run_ecc']}, {setup['run_bars']}, {setup['pa_cycles']}, {setup['pa_cycle_duration']}, {setup['ecc_cycles']}, {setup['ecc_cycle_duration']}, {setup['bar_sweeps']}, {setup['bar_sweep_duration']}\n''')
    logfile.write(f'''Baseline Duration preceding and following stimualtion: {setup['baseline_duration']} secs\n''')
    logfile.write('Time, pa_cycle_count, time_through_pa_cycle, pa_angle, ecc_cycle_count, time_through_ecc_cycle, ecc_inner_rad, bar_sweep_count, time_through_bar_sweep, bar_drift_position, bar_orientation, fixation_orientation\n''')

#%% =============================================================================
# functions
def screenCorrection(mywin,x):
    resX = mywin.size[0]
    resY = mywin.size[1]
    aspect = float(resX) / float(resY)
    new = x / aspect
    return(new)

def draw_siderweb():
    for i_dim in range(spiderweb_total_rings):
        web_circle.setSize(tuple([x*(i_dim+1) * 1./spiderweb_total_rings for x in web_dimension]))
        web_circle.draw()
    for i_dim in range(4):
        web_line.setOri(i_dim * 45)
        web_line.draw()

def fixation_orientation_task(rotate_timer, fixation_orientation):
    # if time for a possible fixation orientation change,
    if clock.getTime()-rotate_timer > fixation_rotate_rate:
        # randomly choose an orientation
        fixation_orientation = random.choice(fixation_orientations)
        rotate_timer = clock.getTime()

    fixation_cross.setOri(fixation_orientation)
    fixation_cross.draw()
    fixation_cross.setOri(fixation_orientation+90)
    fixation_cross.draw()

    # return updated timer and orientation setting
    return rotate_timer, fixation_orientation

#%% =============================================================================
# create window, on-screen messages and stimuli

# test monitor
#win = visual.Window([screen_size,screen_size],monitor="testMonitor", units="norm", screen=1) #, fullscr=True)
# uni office monitor
#win = visual.Window(monitor="DELL U2415", units="norm", fullscr=True)
# ICE monitor
win = visual.Window(monitor="Dell E2417H", units="norm", fullscr=True)

# make sure the mouse cursor isn't showing once the experiment starts
event.Mouse(visible=False)
# make sure button presses are picked up once the experiment starts
win.winHandle.activate()

# on-screen text
welcome_message = visual.TextStim(win, pos=[0,+0.3], text='Preparing images...')
C_keypress_message = visual.TextStim(win, pos=[0,+0.3], text='Waiting for Experimenter C Key Press...')
trigger_message = visual.TextStim(win, pos=[0,+0.3], text=f'Waiting for Scanner Trigger... ({scanner_trigger}')
insructions_to_subjects = visual.TextStim(win, pos=[0,+0.3], text=insructions_to_subjects)

# spiderweb background
web_dimension = (screenCorrection(win,web_size[0]),web_size[1])
web_circle = visual.Circle(win=win,radius=1,edges=200,units='norm',pos=[0, 0],lineWidth=1,opacity=1,interpolate=True,
                        lineColor=[1.0, 1.0, 1.0],lineColorSpace='rgb',fillColor=None,fillColorSpace='rgb')
web_line = visual.Line(win,name='Line',start=(-1.4, 0),end=(1.4, 0),pos=[0, 0],lineWidth=1,
                       lineColor=[1.0, 1.0, 1.0],lineColorSpace='rgb',opacity=1,interpolate=True)

# fixation cross made up of a line element
fixation_cross = visual.Line(win,name='Line',start=(-0.01, 0),end=(0.01, 0),pos=[0, 0],lineWidth=2,
                       lineColor='red',lineColorSpace='rgb',opacity=1,interpolate=True)

# intial fixation cross orientation is just the first as default
fixation_orientation = fixation_orientations[0]

# create orientation angles for bars
bar_orientations = list(np.arange(0,360,360/setup['bar_sweeps']))*setup['bar_sweep_reps']
# append a zero just so we don't go out of bounds when the frame on the last sweep
bar_orientations = np.append(bar_orientations, 0)

# =============================================================================
# create full checkerboard backgrounds (which will be masked)
# radial stripes

if setup['run_polar'] == 'Yes' or setup['run_ecc'] == 'Yes':
    # create an image (red will allow us to label it as gray background later)
    img = Image.new("L",(screen_size,screen_size), 'red')
    pa_img = ImageDraw.Draw(img)

    # alternating radial stripe colours
    colours = ['black', 'white']*int(np.ceil(360/(360/32))/2)

    # for 32 radial stripes
    for x, ang in enumerate(np.arange(0, 360, 360/32)):
        # draw a radial stripe for every angle
        pa_img.pieslice([0, 0, screen_size, screen_size], ang, ang+360/32, colours[x])

    # turn image into an array object
    pa_img = np.array(img)

    # =============================================================================
    # rings

    # create an image (red will allow us to label it as gray background later)
    img = Image.new("L",(screen_size,screen_size),'red')
    ecc_img = ImageDraw.Draw(img)

    # define logarithmically spaced integers to determine ring widths
    ring_spacings = np.floor(np.logspace(np.log10(1), np.log10((screen_size/2)), num=50))
    ring_spacings = (screen_size/2)-ring_spacings[::-1]
    # we don't want any repeats
    ring_spacings = np.unique(ring_spacings, axis=0)

    # alternating ring colours
    colours = ['black', 'white']*int(np.ceil(len(ring_spacings)/2))

    for x, spacing in enumerate(ring_spacings):
        # draw a circle (starting from the biggest and 'stacking' smaller ones on top to create rings)
        ecc_img.ellipse((spacing,spacing,screen_size-spacing,screen_size-spacing), colours[x])

    # switch the image to an array
    ecc_img = np.array(img)

    # =============================================================================
    # average them
    checkerboard = (pa_img/2) + (ecc_img/2)
    # where the average agreed make black checks
    checkerboard[checkerboard==255]=0
    # where the average disagreed make white checks
    checkerboard[checkerboard==127.5]=255
    # where the average was something else, must be gray background later
    checkerboard[(checkerboard>0) & (checkerboard<255)]=128
    # make inverted version
    checkerboard_inv = 255-checkerboard
    # make into images
    checkerboard_noninv = Image.fromarray(checkerboard)
    checkerboard_inv = Image.fromarray(checkerboard_inv)

else:
    # =============================================================================
    # make regular checkerboards
    check_size = 32
    n_checks = int((screen_size/check_size)/2)

    checkerboard = np.kron([[255, 0] * n_checks, [0, 255] * n_checks] * n_checks, np.ones((check_size, check_size)))

    reg_checkerboards = []
    reg_checkerboards_inv = []
    for sweep, bar_orientation in enumerate(np.flip(bar_orientations)):

        tmp = ndimage.rotate(checkerboard, bar_orientation, reshape=False, axes=(1,0), order=0)

        reg_checkerboards.append(Image.fromarray(tmp))
        reg_checkerboards_inv.append(Image.fromarray(255 - tmp))

    checkerboard_noninv = reg_checkerboards[0]
    checkerboard_inv = reg_checkerboards_inv[0]

# =============================================================================
# make transparency masks

# beyond_stim_circle
y,x = np.ogrid[-(screen_size/2):screen_size-(screen_size/2), -(screen_size/2):screen_size-(screen_size/2)]
ind = x*x + y*y <= screen_centre*screen_centre

beyond_stim_circle = np.ones((screen_size, screen_size), dtype=bool)
beyond_stim_circle[ind] = False

# preallocate for ecc as many pixels along the screen radius
ecc_masks = np.empty([screen_size,screen_size,int(screen_size/2)])

if setup['run_polar'] == 'Yes':
    # create an image and draw a wedge using the pieslice method
    img = Image.new("L",(screen_size,screen_size), 'black')
    pa_img = ImageDraw.Draw(img)
    pa_img.pieslice([0, 0, screen_size, screen_size], 0, wedge_width, 'white')

    # make it into an array
    pa_mask_0 = np.array(img, dtype=int)

else:
    pa_mask_0 = np.empty([screen_size,screen_size])


if setup['run_ecc'] == 'Yes':
    # this takes a while, so just say something so we know the code's working
    welcome_message.draw()
    win.flip()

    for x, inner_rad in enumerate(np.arange(1, (screen_size/2)+1, 1)):
        # create an image and draw a ring using two stacked circles of different colours
        img = Image.new("L",(screen_size,screen_size), 'black')
        ecc_img = ImageDraw.Draw(img)

        # outer (inner radius multiplied by a steadily increasing factor: ring_width)
        ecc_img.ellipse((screen_centre-np.clip(np.ceil(inner_rad*ring_width), 0, screen_size/2),
                         screen_centre-np.clip(np.ceil(inner_rad*ring_width), 0, screen_size/2),
                         screen_centre+np.clip(np.ceil(inner_rad*ring_width), 0, screen_size/2),
                         screen_centre+np.clip(np.ceil(inner_rad*ring_width), 0, screen_size/2)), 'white')
        # inner
        ecc_img.ellipse((screen_centre-inner_rad,
                         screen_centre-inner_rad,
                         screen_centre+inner_rad,
                         screen_centre+inner_rad), 'black')

        # make it into an array
        ecc_mask = np.array(img, dtype=int)

        # add to preallocated array
        ecc_masks[:,:,x] = ecc_mask

    # set between -1=masked and 1=visible
    ecc_masks[ecc_masks==0] = -1
    ecc_masks[ecc_masks==255] = 1

if setup['run_bars'] == 'Yes':
    # create an image with an extra side panel for the bar to go into to leave
    # the stimulus area
    img = Image.new("L",(screen_size+bar_width,screen_size), 'black')
    bar_img = ImageDraw.Draw(img)
    # draw a rectangle orientated vertically with leading edge at the left
    bar_img.rectangle([0, 0, bar_width, screen_size],'white')

    # make it into an array
    bar_mask_0 = np.array(img, dtype=int)
else:
    bar_mask_0 = np.empty([screen_size+bar_width,screen_size+bar_width])

checkerboard_image = visual.ImageStim(win, image=checkerboard_noninv, units='norm', size=(screenCorrection(win,2),2))

#%% =============================================================================
# start experiment

insructions_to_subjects.draw()
win.flip()
while not '1' in event.getKeys():
    core.wait(0.1)

C_keypress_message.draw()
win.flip()
while not 'c' in event.getKeys():
    core.wait(0.1)

# =============================================================================
# start waiting for trigger
 button_thread.start()
 trigger_message.draw()
 win.flip()
 while not scanner_trigger in event.getKeys():
     core.wait(0.1)
# =============================================================================

clock = core.Clock()
clock.reset()

# =============================================================================
# first baseline
baseline_start = clock.getTime()
rotate_timer = clock.getTime()

while clock.getTime() - baseline_start < setup['baseline_duration']:
    draw_siderweb()
    # if time for a possible fixation orientation change, randomly choose an
    # orientation and return updated timer and orientation setting
    rotate_timer, fixation_orientation = fixation_orientation_task(rotate_timer, fixation_orientation)
    win.flip()

# =============================================================================
# main stimulation
pa_start = clock.getTime()
ecc_start = clock.getTime()
bar_start = clock.getTime()
flicker_timer = clock.getTime()
export_timer = clock.getTime()

pa_cycle_count = 0
ecc_cycle_count = 0
bar_sweep_count = 0
export_frame_count = 0
while True: # we'll break out of this loop once we've shown enough
    if spiderweb_grid:
        if setup['export_masks'] == 'No':
            draw_siderweb()

# =============================================================================
# prepare polar mask
    pa_time = (clock.getTime()-pa_start)/setup['pa_cycle_duration']
    pa_ang = int(360*pa_time)

    if pa_ang < 359:
        # rotate pa_mask_0 to proper angle (spline order 0 interpolation)
        pa_mask = ndimage.rotate(pa_mask_0, pa_ang, reshape=False, axes=(1,0), order=0)
    else:
        pa_start = clock.getTime()
        pa_mask = pa_mask_0
        pa_cycle_count += 1

    # set between -1=masked and 1=visible
    pa_mask[pa_mask==0] = -1
    pa_mask[pa_mask==255] = 1

# =============================================================================
# prepare ecc mask
    ecc_time = (clock.getTime()-ecc_start)/setup['ecc_cycle_duration']
    ecc_rad = int((screen_size/2)*ecc_time)

    if ecc_rad < screen_size/2:
        ecc_mask = ecc_masks[:,:,ecc_rad]
    else:
        ecc_start = clock.getTime()
        ecc_mask = ecc_masks[:,:,0]
        ecc_cycle_count += 1

# =============================================================================
# prepare bar mask
    bar_time = (clock.getTime()-bar_start)/setup['bar_sweep_duration']
    # we make an extra side panel for the bar to go into to leave the stimulus area
    bar_drift = int((screen_size+bar_width)*bar_time)

    if bar_drift < screen_size+bar_width:
        # shift bar (according to bar_drift) from the left side panel so that
        # it wraps and begins traversing from the right side
        bar_mask = np.roll(bar_mask_0, -bar_drift)
    else:
        bar_start = clock.getTime()
        bar_mask = bar_mask_0
        bar_sweep_count += 1

    if setup['run_bars'] == 'Yes':

        # if we're only doing bars, use
        if setup['run_polar'] == 'No' and setup['run_ecc'] == 'No':
            checkerboard_noninv = reg_checkerboards[bar_sweep_count]
            checkerboard_inv = reg_checkerboards_inv[bar_sweep_count]

        # remove the extra side panel
        bar_mask = bar_mask[:,bar_width:]

        # rotate bar into specified orientation
        bar_mask = ndimage.rotate(bar_mask, bar_orientations[bar_sweep_count], reshape=False, axes=(1,0), order=0)

        # set between -1=masked and 1=visible
        bar_mask[bar_mask==0] = -1
        bar_mask[bar_mask==255] = 1

# =============================================================================
    # if something is not being done, set mask to transparent
    if setup['run_polar'] == 'No':
        pa_mask = np.zeros([screen_size, screen_size])-1

    if setup['run_ecc'] == 'No':
        ecc_mask = np.zeros([screen_size, screen_size])-1

    if setup['run_bars'] == 'No':
        bar_mask = np.zeros([screen_size, screen_size])-1

    # combine masks
    mask = pa_mask + ecc_mask + bar_mask
    # any pixel that wasn't marked as -1 for all 3 masks should be visible
    mask[mask>-3]=1
    # only pixels marked -1 for all 3 masks should be invisible
    mask[mask==-3]=-1
    # anything outside the stim circle should be invisible
    mask[beyond_stim_circle]=-1
    # set mask
    checkerboard_image.mask = mask

    # decide whether to invert checkerboard or not and set image accordingly
    if clock.getTime()-flicker_timer > flicker_rate:
        switch = not switch # change switch to opposite boolean
        flicker_timer = clock.getTime()

    if switch:
        checkerboard_image.image = checkerboard_inv
    else:
        checkerboard_image.image = checkerboard_noninv

    checkerboard_image.draw()

    # if time for a possible fixation orientation change, randomly choose an
    # orientation and return updated timer and orientation setting

    if setup['export_masks'] == 'No':
        rotate_timer, fixation_orientation = fixation_orientation_task(rotate_timer, fixation_orientation)

    win.flip()

    # export mask
    if setup['export_masks'] == 'Yes':
        # if enough time has elapsed since the last export
        if clock.getTime()-export_timer > export_rate/1000:
            win.getMovieFrame()
            win.saveMovieFrames(f"{export_im_dir}/{export_frame_count:04}_export_rate_{export_rate}ms.png")
            export_frame_count += 1
            export_timer = clock.getTime()

    if setup['save_log'] == 'Yes':
            logfile.write(f'''{np.round(clock.getTime(), 2)}, {pa_cycle_count}, {np.round(clock.getTime()-pa_start, 2)}, {np.round(pa_ang, 2)}, \
                             {ecc_cycle_count}, {np.round(clock.getTime()-ecc_start, 2)}, {np.round(ecc_rad, 2)}, \
                             {bar_sweep_count}, {np.round(clock.getTime()-bar_start, 2)}, {np.round(bar_drift, 2)}, {bar_orientations[bar_sweep_count]}, \
                             {fixation_orientation}\n''')

    # should we stop stimulating and move on to the last baseline?
    if (setup['run_polar'] == 'Yes') and (pa_cycle_count == setup['pa_cycles']):
        break
    if (setup['run_ecc'] == 'Yes') and (ecc_cycle_count == setup['ecc_cycles']):
        break
    if (setup['run_bars'] == 'Yes') and (bar_sweep_count == setup['bar_sweeps']*setup['bar_sweep_reps']):
        break

# =============================================================================
# last baseline
baseline_start = clock.getTime()

while clock.getTime() - baseline_start < setup['baseline_duration']:
    draw_siderweb()
    # if time for a possible fixation orientation change, randomly choose an
    # orientation and return updated timer and orientation setting
    rotate_timer, fixation_orientation = fixation_orientation_task(rotate_timer, fixation_orientation)
    win.flip()

#%% =============================================================================
# cleanup
logfile.close()
win.close()
core.quit()
