from psychopy import visual, core, event, gui, prefs, sound
prefs.hardware['audioLib'] = ['PTB']

import pandas as pd 
import numpy as np
from pathlib import Path
import yaml

import sounddevice as sd
import scipy.io.wavfile as wav
from threading import Thread
import atexit
from config import *


# load messages
with open(root_path / "exp_text" /'instruction_message.yaml', 'r') as file:
    instruction_messages = yaml.safe_load(file)
    
assert type(instruction_messages) == dict


# helper functions 
# Define other components you'll need, like a clock for timing
def display_message(text: str):
    message = visual.TextStim(win, text=text, color=(-1, -1, -1), wrapWidth=1.5, font='Arial')
    message.draw()
    win.flip()
    event.waitKeys(keyList=['return'])

def play_trigger(n_triggers: int, wait_time, core):
    for i in range(n_triggers):
        beep = sound.Sound(value='C', volume=1, sampleRate=44100, secs=0.2, stereo=True)
        beep.play()
        core.wait(beep.getDuration() + wait_time)  # Wait for the sound duration and additional wait time
    # sound.stop()
    
def mode_start_beep(sec=mode_start_beep_secs):
    beep = sound.Sound(value='C', volume=1, sampleRate=44100, secs=sec, stereo=True)
    beep.play()
    core.wait(beep.getDuration() + mode_start_beep_wait)  # Wait for the sound duration and additional wait time

def mode_end_beep(sec=mode_end_beep_secs):
    beep = sound.Sound(value='E', volume=1, sampleRate=44100, secs=sec, stereo=True)
    beep.play()
    core.wait(beep.getDuration() + mode_end_beep_wait)  # Wait for the sound duration and additional wait time
    

def speech_modes(is_perception: bool, audio_path=None):
    # draw green fixation cross
    fixation = visual.TextStim(win, text='+', color=(-1, -1, -1), font='Arial')
    fixation.draw()
    win.flip()
    
    mode_start_beep()
    # draw green fixation 
    fixation.color = (0, 1, 0)
    fixation.draw()
    win.flip()
    
    if is_perception:
        # play audio 
        audio = sound.Sound("audio/i-cant-think-of-anything-175801.mp3")
        audio.play()
        core.wait(audio.getDuration() + audio_end_wait)
    else: 
        # wait for response space
        while True:
            keys = event.waitKeys()
            if 'return' in keys:
                break
    
    
    mode_end_beep()
    
    # draw black fixation cross
    fixation.color = (-1, -1, -1)
    fixation.draw()
    win.flip()
    
    core.wait(mode_end_wait)
    
    
    
def trial_run(df_row):
    # perception 
    speech_modes(is_perception=True, audio_path=df_row['audio_path'])
    # intermode wait
    core.wait(inter_mode_wait)
    
    # internal speech 
    speech_modes(is_perception=False)
    core.wait(inter_mode_wait)
    
    # speech 
    speech_modes(is_perception=False)
    core.wait(inter_mode_wait)
    
    # trial end wait 
    core.wait(trial_end_wait)


def block_run(rows):
    for i, row in rows.iterrows():
        trial_run(row)
    

# recording 
# Global variable to hold the recorded audio
# Audio recording setup
fs = 44100  # Sample rate
global_audio_data = np.array([], dtype='float32')  # Use a numpy array for efficiency

def find_device_index_by_name(search_name):
    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        if search_name.lower() in device['name'].lower():
            return idx
    return None

# Example usage
search_name = "BlackHole"  # Replace with the part of the name you're searching for
loopback_device_index = find_device_index_by_name(search_name)

def record_audio():
    """Continuously record audio until the script ends."""
    global global_audio_data
    def callback(indata, frames, time, status):
        """This function is called for each audio block."""
        global global_audio_data
        global_audio_data = np.append(global_audio_data, indata.copy().flatten())  # Flatten and append data

    # Open the stream and start recording
    with sd.InputStream(samplerate=fs, channels=2, dtype='float32', device=loopback_device_index, callback=callback):
        print("Recording started...")
        sd.sleep(10000000)  # Keep recording for a long time (until the script ends)
        

#######################################
# welcome
#######################################

# Create a dialog box to enter the date of the experiment
dateDlg = gui.Dlg(title="Experiment Date")
dateDlg.addField('Enter the date (YYYY-MM-DD):')
dateDlg.addField('Enter the time:')
dateInfo = dateDlg.show()  # show dialog and wait for OK or Cancel
if dateDlg.OK:  # if OK was pressed, proceed
    # experiment_date = dateInfo[0]
    experiment_date = dateInfo[list(dateInfo.keys())[0]]
    exp_time = dateInfo[list(dateInfo.keys())[1]]

else:
    core.quit()  # User pressed cancel, so exit
    
# Create a window
win = visual.Window(fullscr=full_screen, color=(245, 245, 245))
clock = core.Clock()

# Ensure the recording stops properly when the script ends

# Function to save the recorded audio at the end of the experiment
def save_audio_data(save_path, filename):
    global global_audio_data
    if len(global_audio_data) > 0:  # Check if there's data to save
        print("Saving recorded audio...")
        wav.write(str(save_path / filename), fs, global_audio_data.reshape(-1, 2))
        print(f"Audio saved to {filename}")
    else:
        print("No audio data to save.")

# Register the cleanup function with atexit
atexit.register(save_audio_data, save_path_recording, f'exp{experiment_date}-{exp_time}-audio.wav')

# display welcome message and instructions 
display_message(instruction_messages['landing_page'])
display_message(instruction_messages['instruction_1'])
display_message(instruction_messages['instruction_2'])

#######################################
# start 
#######################################
sentences = pd.read_csv(sentence_file)

block_run(sentences.iloc[:10])

#######################################
# end
#######################################
finish_statement = visual.TextStim(win, text=instruction_messages['finish_page'], color=(-1, -1, -1), font='Arial')
finish_statement.draw()
win.flip()
core.wait(2)  # Adjust the wait time as needed

# Save the events to a CSV file
# events = pd.concat(all_events)
# events.to_csv(save_path / f'events-{experiment_date}-{exp_time}_all.csv', index=False)

# Close the window and quit the experiment
win.close()
core.quit()



#######################################
# trial start
#######################################
# display_message(instruction_messages['trial_session_start'])

# core.wait(1)

# # Start recording in a separate thread to not block the main PsychoPy experiment
# audio_thread = Thread(target=record_audio, daemon=True)
# audio_thread.start()

# # Reset the clock to zero at the beginning of the presentation
# clock.reset()
# all_events = []  # List to hold event data

# events_trial = iter_sentences(trial_sentences, win, clock, 'trial', core)

# all_events.extend(events_trial)
# #######################################
# # actual test
# #######################################
# display_message(instruction_messages['trial_session_end'])

# for b in np.arange(1, n_blocks+1):
    
#     # show block number
#     block_no = visual.TextStim(win, text=f'Bloc {b}', color=(-1, -1, -1), font='Arial')
#     block_no.draw()
#     win.flip()
    
#     core.wait(1)
    
#     # get sentences assigned to this block 
#     sentence_block = sentences[block_idx == b]

#     events_test = iter_sentences(sentence_block, win, clock, f'block{b}', core)

#     all_events.extend(events_test)
    
#     # backup save 
#     pd.concat(all_events).to_csv(save_path / f'events-{experiment_date}-{exp_time}block{b}.csv', index=False)
    
#     # check if continue withe the exp
#     between_block = f"Vous avez terminé le bloc{b} ! \n \n Si vous souhaitez continuer, appuyez sur ENTRÉE pour démarrer le bloc suivant. Si vous souhaitez arrêter, appuyez sur n'importe quelle touche pour quitter l'étude."
#     message = visual.TextStim(win, text=between_block, color=(-1, -1, -1), wrapWidth=1.5, font='Arial')
#     message.draw()
#     win.flip()
    
#     key = event.waitKeys()
#     print(key)
    
#     if key[0] == '\r':
#         continue 
#     else: 
#         break 
    

