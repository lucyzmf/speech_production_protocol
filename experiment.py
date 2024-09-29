from psychopy import event, visual, core, gui, prefs, sound
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
with open((root_path / "exp_text" /'instruction_message.yaml'), 'r') as file:
    instruction_messages = yaml.safe_load(file)
    
assert type(instruction_messages) == dict

# global variables
# Create a window
WIN = visual.Window(fullscr=full_screen, color=screen_color, units="norm")
FIXATION = visual.TextStim(WIN, text='+', color=(-1, -1, -1), font='Arial', height=fixation_size)
EVENTS = []

# load icons 
imagine_icon = visual.ImageStim(WIN, image=(root_path / "icon" / "imagine.png"), size=(0.2, 0.2), pos=(0, 0.3))
speak_icon = visual.ImageStim(WIN, image=(root_path / "icon" / "speak.png"), size=(0.2, 0.2), pos=(0, 0.3))
listen_icon = visual.ImageStim(WIN, image=(root_path / "icon" / "audio.png"), size=(0.2, 0.2), pos=(0, 0.3))



# helper functions 
# Define other components you'll need, like a clock for timing
def display_message(text: str, other_icons=None):
    message = visual.TextStim(WIN, text=text, color=text_color, wrapWidth=1.5, font='Arial', height=text_size)
    message.draw()
    
    # "Press Enter to continue" prompt at the bottom-right corner
    prompt_text = "Press 'Enter' to continue"
    prompt = visual.TextStim(WIN, text=prompt_text, color=text_color, pos=(0.95, -0.98), height=text_size * 0.7, anchorHoriz='right')
    prompt.draw()
    
    if other_icons:
        for icon in other_icons:
            icon.draw()
    
    WIN.flip()
    event.waitKeys(keyList=['return'])

def display_message_no_interaction(text: str, wait_time=1):
    message = visual.TextStim(WIN, text=text, color=text_color, wrapWidth=1.5, font='Arial', height=text_size)
    message.draw()
    WIN.flip()
    core.wait(wait_time)

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
    

def speech_modes(mode: str, row: pd.Series):
    global EVENTS
    global CLOCK
    
    # draw fixation cross
    FIXATION.draw()
    WIN.flip()
    
    if mode == 'perception':
        listen_icon.draw()
    elif mode == 'imagine':
        imagine_icon.draw()
    elif mode == 'speak':
        speak_icon.draw()
        
    #log
    start_time = CLOCK.getTime()
    mode_start_beep()
    
    # draw green fixation 
    FIXATION.color = (0, 1, 0)
    FIXATION.draw()
    WIN.flip()
    
    if mode == 'perception':
        # play audio 
        audio = sound.Sound(row["audio_path"][3:])
        audio.play()
        core.wait(audio.getDuration() + audio_end_wait)
    else: 
        # wait for response space
        while True:
            keys = event.waitKeys()
            if 'return' in keys:
                break
    
    # log 
    stop_time = CLOCK.getTime()
    
    mode_end_beep()
    
    # draw black fixation cross
    FIXATION.color = (-1, -1, -1)
    FIXATION.draw()
    WIN.flip()
    
    core.wait(mode_end_wait)
    
    # log to EVENTS 
    log = row.to_dict()
    log['mode'] = mode
    log['start_time'] = start_time
    log['stop_time'] = stop_time
    log['duration'] = stop_time - start_time
    log['event_type'] = 'sentence' if 'sentence' in row.keys() else 'word'
    
    EVENTS.append(log)

    
    
def trial_run(df_row):
    # perception 
    # draw perception icon 
    
    speech_modes("perception", df_row)
    # intermode wait
    core.wait(inter_mode_wait)
    
    # internal speech 
    # draw internal speech icon
    speech_modes("imagine", df_row)
    core.wait(inter_mode_wait)
    
    # speech 
    # draw speech icon
    speech_modes("speak", df_row)
    core.wait(inter_mode_wait)
    
    # trial end wait 
    core.wait(trial_end_wait)


def block_run(sent_rows, word_rows, block_num):
    # shuffle the rows
    sent_rows_ = sent_rows.sample(frac=1)
    sent_rows_.reset_index(drop=True, inplace=True)
    sent_rows_['trial_num'] = np.arange(len(sent_rows_))
    sent_rows_['block_num'] = block_num
    
    display_message_no_interaction(f"Block {block_num}")
    display_message_no_interaction("Sentences")
    
    for i, row in sent_rows_.iterrows():
        trial_run(row)
        
    # repeat words 
    display_message_no_interaction("Words")

    word_rows_ = pd.concat([word_rows]*n_word_repeats_per_block, ignore_index=True)
    word_rows_ = word_rows_.sample(frac=1)
    word_rows_.reset_index(drop=True, inplace=True)
    word_rows_['trial_num'] = np.arange(len(word_rows_))
    word_rows_['block_num'] = block_num
    
    for i, row in word_rows_.iterrows():
        trial_run(row)
        

def guided_test_block(rows):
    # Step 1: Explain the task
    display_message("In each trial of the task, you will hear an audio of a sentence or word.")
    display_message("Press 'Enter' to play a sentence.")
    
    # Play the first audio from the dataset as an example
    speech_modes("perception", rows.iloc[0])
    
    # Step 2: Explain the following steps after the audio is played
    display_message("Following the audio, you will have to repeat the sentence you have heard twice: once in your mind and once out loud.")
    
    display_message("First, you will have to repeat the sentence in your mind (icon above).", [imagine_icon])
    
    # Step 3: Explain mental speech
    # You can display a mock icon here if needed, or just the fixation cross.
    # display the icon
    display_message("Then, you will have to say the sentence out loud (icon above).", [speak_icon])

    
    # Step 4: Explain the start of the trial
    display_message("You should start when the fixation cross turns green and you hear the first beep. \n \n After you finish, press enter and you will see the fixation cross turn black, followed by a beep. ")
    speech_modes("imagine", rows.iloc[0])
    core.wait(inter_mode_wait)
    
    # speech 
    # draw speech icon
    speech_modes("speak", rows.iloc[0])
    core.wait(inter_mode_wait)
        
    # Step 5: Practice the task with a couple of sentences
    display_message("Now, let's practice with a couple of sentences.")
    
    for i, row in rows.iloc[:n_practice_trials].iterrows():  # Use the first two rows for practice
        trial_run(row)
    
    # Step 6: Ask if they want to practice more
    display_message("The practice is over!. Let's start the actual test. Press 'Enter' when you're ready.")
    
    

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
if __name__ == "__main__":
    # Create a dialog box to enter the date of the experiment
    dateDlg = gui.Dlg(title="Experiment Date")
    dateDlg.addField('Date:', tip='Enter the date (YYYY-MM-DD)')
    dateDlg.addField('Time:', tip='Enter the time')

    dateInfo = dateDlg.show()  # show dialog and wait for OK or Cancel

    if dateDlg.OK:  # if OK was pressed, proceed
        # experiment_date = dateInfo[0]
        experiment_date = dateInfo[list(dateInfo.keys())[0]]
        exp_time = dateInfo[list(dateInfo.keys())[1]]

    else:
        core.quit()  # User pressed cancel, so exit
        

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
    CLOCK = core.Clock()

    sentences = pd.read_csv(sentence_file)
    sentences = sentences.query("translanted_num_words < @max_words_per_sent")
    words = pd.read_csv(word_file)
    
    if test_mode:
        sentences = sentences.sample(4)
        words = words.sample(4)

    guided_test_block(sentences.iloc[:10])
    for b in np.arange(n_blocks):
        block_run(sent_rows=sentences.iloc[b*n_sent_trials_per_block:(b+1)*n_sent_trials_per_block], word_rows=words, block_num=1)

    #######################################
    # end
    #######################################
    finish_statement = visual.TextStim(WIN, text=instruction_messages['finish_page'], color=text_color, font='Arial')
    finish_statement.draw()
    WIN.flip()
    core.wait(2)  # Adjust the wait time as needed

    # Save the events to a CSV file
    events = pd.DataFrame(EVENTS)
    events.to_csv(save_path_events / f'events-{experiment_date}-{exp_time}_all.csv', index=False)

    # Close the window and quit the experiment
    WIN.close()
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
    

