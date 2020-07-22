# -*- coding: utf-8 -*-
"""
Auditory and Imagery Experiment.

Created by Matthew A. Bennett (Wed May 22 12:47:23 2019)
Matthew.Bennett@glasgow.ac.uk
"""

#%% =============================================================================
# imports
from my_functions import designs

from psychopy import core, visual, sound, event, gui

# HOW DO I STOP THE TRIGGER ('z') FROM OVERWRITING THE RESPONSE...?
# from vipixx_something_or_other import button_thread

#%% =============================================================================
# setup
sub_id = 'SUB01'

dialog_info = gui.Dlg(title="Auditory/Imagery Experiment")
dialog_info.addField('Subject ID:', sub_id)
dialog_info.addField('Run:')
dialog_info.addField('Run Type:', choices=["Auditory", "Imagery"])
dialog_info = dialog_info.show()  # show dialog and wait for OK or Cancel

#dialog_info = ['SUB01', '1', 'Auditory']

subject_id = dialog_info[0]
run = int(dialog_info[1])
run_type = dialog_info[2]

#%% =============================================================================
# paths and definitions

stim_path = (r'Z:\0_7T Aud_Img Presentation Code - Matt put this here\Stimuli\\')

stimuli_names = [['Forest_12sec_Mono.wav', 'Cue_forest.wav'],
                 ['Indians_12sec_Mono.wav', 'Cue_people.wav'],
                 ['Traffic_12sec_41Hz.wav', 'Cue_traffic.wav']]

imagery_stop_beep = sound.Sound(stim_path + 'Cue_beep.wav')

# in seconds
if run_type == 'Auditory':
    baseline = 12
    trial_duration = 12
elif run_type == 'Imagery':
    baseline = 12
    trial_duration = 14

condition_reps = 6

insructions_to_subjects = '''Do the experiment right.
Press 1 to continue'''

# shuffle the block order leaving no consecutive repeats
blocks = [0, 1, 2]*condition_reps
block_order = designs.shuffle_no_repeats(blocks)

#%% =============================================================================
# functions

def esc():
    if 'escape' in last_response:
        logfile.close()
        win.close()
        core.quit

#%% =============================================================================
# log data

# make a text file to save data with 'comma-separated-values'
logfile = open(f'{subject_id}_run{run}_logfile.csv', 'w')
logfile.write(f'Run: {run} - {run_type}\n')
if run_type == 'Auditory':
    logfile.write('Trial, Stimulus, StimCode, StimOnset, Response, Response_Time\n')
elif run_type == 'Imagery':
    logfile.write('Trial, Stimulus, StimCode, ImgCueOnset, ImgOnset, StopImgCueOnset, Response, Response_Time\n')

#%% =============================================================================
# create stimuli

# test monitor
win = visual.Window([800,800],monitor="testMonitor", units="deg", screen=1) #, fullscr=True)
# uni office monitor
#win = visual.Window(monitor="DELL U2415", units="pix", fullscr=True)
# ICE monitor
#win = visual.Window(monitor="Dell E2417H", units="norm", fullscr=True)

pix_converter = 1

# make sure the mouse cursor isn't showing once the experiment starts
event.Mouse(visible=False)

# make sure button presses are picked up once the experiment starts
win.winHandle.activate()


# create a list of image objects t obe shown in the expt
stimuli = []
stimuli_cues = []
for name in stimuli_names:

#    stimuli.append(visual.ImageStim(win, image = stim_path + name))
    stimuli.append(sound.Sound(stim_path + name[0]))
    stimuli_cues.append(sound.Sound(stim_path + name[1]))

fixation = visual.Rect(win, width=0.2*pix_converter, height=0.2*pix_converter, fillColor='white', autoDraw=True)

experimenter_message1 = visual.TextStim(win, pos=[0,+3*pix_converter], text='Experiment Running...')
experimenter_message2 = visual.TextStim(win, pos=[0,+3*pix_converter], text='Waiting for Experimenter C Key Press...')
trigger_message = visual.TextStim(win, pos=[0,+3*pix_converter], text='Waiting for Scanner Trigger...')

insructions_to_subjects = visual.TextStim(win, pos=[0,+3*pix_converter], text=insructions_to_subjects)

#%% =============================================================================
# start experiment

insructions_to_subjects.draw()
win.flip()
while not '1' in event.getKeys():
    core.wait(0.1)

experimenter_message2.draw()
win.flip()
while not 'c' in event.getKeys():
    core.wait(0.1)

# =============================================================================
# start waiting for trigger (coded as z)
# button_thread.start()
# trigger_message.draw()
# win.flip()
# while not 'z' in event.getKeys():
#     core.wait(0.1)
# HOW DO I STOP THE TRIGGER ('z') FROM OVERWRITING THE RESPONSE...?
# =============================================================================

# start stopwatch clock
clock = core.Clock()
clock.reset()

# we want this up all the time once the scanning begins
experimenter_message1.autoDraw=True
win.flip()

# clear any previous presses/escapes
last_response = ''; response_time = ''

for idx, trial in enumerate(block_order):

# =============================================================================
    # how much time has passes since we began the expt?
    expt_time_elapsed = clock.getTime()

    # calculate any drift (should be only a few ms) in the stimulus timings (we'll offset it during the next baseline)
    error_adjust = (baseline + trial_duration)*idx - expt_time_elapsed

# =============================================================================
    # show baseline
    core.wait(baseline + error_adjust)

    if run_type == 'Auditory':
        logfile.write(f'{idx+1}, Baseline, 0, {expt_time_elapsed}, NA, NA\n')
    elif run_type == 'Imagery':
        logfile.write(f'{idx+1}, Baseline, 0, {expt_time_elapsed}, NA, NA, NA, NA\n')

# =============================================================================
    esc() # in case we need to shut down the expt

# =============================================================================
    # show next trial
    trial_onset_time = clock.getTime()
    logfile.write(f'{idx+1}, {stimuli_names[block_order[idx]][1]}, {block_order[idx]+1}, {trial_onset_time},')

    # play sound
    if run_type == 'Auditory':
        stimuli[trial].play()
        core.wait(trial_duration)
    elif run_type == 'Imagery':
        stimuli_cues[trial].play()
        core.wait(1)
        logfile.write(f'{clock.getTime()},')
        core.wait(12)
        logfile.write(f'{clock.getTime()},')
        imagery_stop_beep.play()
        core.wait(1)

# =============================================================================
    # get response and it's associated timestamp as a list of tuples: (keypress, time)


    response = event.getKeys(timeStamped=clock)

    if not response:
        response = [('No_Response', -1)]

    last_response = response[-1][0] # most recent response, first in tuple
    response_time = response[-1][1] # most recent response, second in tuple

    logfile.write(f'{last_response}, {response_time}\n')

# =============================================================================
    esc() # in case we need to shut down the expt

#%% =============================================================================
# cleanup
logfile.close()
win.close()
core.quit()
