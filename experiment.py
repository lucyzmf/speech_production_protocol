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
# imagine_icon = visual.ImageStim(WIN, image=(root_path / "icon" / "imagine.png"), size=(0.2, 0.2), pos=(0, 0.3))
speak_icon = visual.ImageStim(WIN, image=(root_path / "icon" / "speak.png"), size=(0.2, 0.2), pos=(0, 0.3))
listen_icon = visual.ImageStim(WIN, image=(root_path / "icon" / "audio.png"), size=(0.2, 0.2), pos=(0, 0.3))



# helper functions 
# Define other components you'll need, like a clock for timing
def display_message(text: str, other_icons=None):
    message = visual.TextStim(WIN, text=text, color=text_color, wrapWidth=1.5, font='Arial', height=text_size)
    message.draw()
    
    # "Press Enter to continue" prompt at the bottom-right corner
    prompt_text = "Appuyez sur ENTRÉE pour continuer"
    prompt = visual.TextStim(WIN, text=prompt_text, color=text_color, pos=(0.95, -0.95), height=text_size * 0.7, anchorHoriz='right')
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
    # elif mode == 'imagine':
    #     imagine_icon.draw()
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
    # speech_modes("imagine", df_row)
    # core.wait(inter_mode_wait)
    
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
    sent_rows_['block_num'] = block_num
    
    word_rows_ = pd.concat([word_rows]*n_word_repeats_per_block, ignore_index=True)
    word_rows_.reset_index(drop=True, inplace=True)
    word_rows_['block_num'] = block_num
    
    all_rows = pd.concat([sent_rows_, word_rows_], ignore_index=True)
    shuffle_idx = np.random.permutation(len(all_rows))
    all_rows = all_rows.iloc[shuffle_idx]
    all_rows['trial_num'] = np.arange(len(all_rows))
    all_rows.reset_index(drop=True, inplace=True)

    display_message_no_interaction(f"Block {block_num}")
    
    trials_per_subblock = len(all_rows) // n_subblocks
    print(f"Trials per subblock: {trials_per_subblock}")
    
    for i, row in all_rows.iterrows():
        trial_run(row)
        
        if i % trials_per_subblock == 0 and i != 0:
            # repeat words 
            display_message_no_interaction("petite pause 10sec", wait_time=10)
            

def guided_test_block(rows):
    # Étape 1 : Expliquer la tâche
    display_message("Dans chaque essai de la tâche, vous entendrez un enregistrement audio d'une phrase ou d'un mot. Appuyez sur 'Entrée' pour jouer une phrase.")
    
    # Jouer le premier audio du dataset comme exemple
    speech_modes("perception", rows.iloc[0])
    
    # Étape 2 : Expliquer les étapes suivantes après que l'audio ait été joué
    display_message("Après l'audio, vous devrez répéter à voix haute la phrase ou le mot que vous avez entendu (icône ci-dessus).", [speak_icon])
    
    # Étape 4 : Expliquer le début de l'essai
    display_message("Vous devez commencer lorsque la croix de fixation devient verte et que vous entendez le premier bip. \n \n Après avoir terminé, appuyez sur Entrée et vous verrez la croix de fixation devenir noire, suivie d'un bip.")
    # speech_modes("imagine", rows.iloc[0])
    # core.wait(inter_mode_wait)
    
    # Parler
    # Dessiner l'icône de la parole
    speech_modes("speak", rows.iloc[0])
    core.wait(inter_mode_wait)
        
    # Étape 5 : S'exercer à la tâche avec quelques phrases
    display_message("Maintenant, pratiquons avec quelques phrases.")
    
    for i, row in rows.iloc[:n_practice_trials].iterrows():  # Utiliser les deux premières lignes pour l'exercice
        trial_run(row)
    
    # Étape 6 : Demander s'ils veulent s'exercer davantage
    display_message("L'exercice est terminé ! Commençons le test réel. Appuyez sur 'Entrée' lorsque vous êtes prêt.")


# recording 
# Global variable to hold the recorded audio
# Audio recording setup
fs = 44100  # Sample rate
global_audio_data = np.array([], dtype='float32')  # Use a numpy array for efficiency
mic_audio_data = np.array([], dtype='float32')  # Use a numpy array for efficiency


def find_device_index_by_name(search_name):
    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        if search_name.lower() in device['name'].lower():
            return idx
    return None

# Example usage
search_name = "BlackHole"  # Replace with the part of the name you're searching for
loopback_device_index = find_device_index_by_name(search_name)
mic_device_index = find_device_index_by_name(mic_device_name)

def callback_system(indata_system, framse, time, status):
    global global_audio_data
    
    if status:
        print(status)
    
    #combine audio streams 
    global_audio_data = np.append(global_audio_data, indata_system.flatten())

def callback_mic(indata_system, framse, time, status):
    global mic_audio_data
    
    if status:
        print(status)
    
    #combine audio streams 
    mic_audio_data = np.append(mic_audio_data, indata_system.flatten())

def record_audio_combined():
    """Continuously record audio until the script ends."""
    global global_audio_data
    
    # Open the stream and start recording
    # with sd.InputStream(samplerate=fs, channels=2, dtype='float32', device=loopback_device_index, callback=callback_system) as system_stream, \
    #      sd.InputStream(samplerate=fs, channels=1, dtype='float32', device=mic_device_index, callback=callback_mic) as mic_stream:
             
    with sd.InputStream(samplerate=fs, channels=1, dtype='float32', device=mic_device_index, callback=callback_mic) as mic_stream:
        print("Recording started...")
        
        # system_stream.start()
        mic_stream.start()
        
        sd.sleep(10000000)  # Keep recording for a long time (until the script ends)
        

#######################################
# welcome
#######################################
if __name__ == "__main__":
    # Temporarily set the window to non-fullscreen mode to show the dialog
    WIN.winHandle.set_fullscreen(False)
    WIN.flip()

    # Create a dialog box to enter the date of the experiment
    dateDlg = gui.Dlg(title="Experiment Date")
    dateDlg.addField('Date:', tip='Enter the date (YYYY-MM-DD)')
    dateDlg.addField('Time:', tip='Enter the time')

    dateInfo = dateDlg.show()  # Show dialog and wait for OK or Cancel

    if dateDlg.OK:  # if OK was pressed, proceed
        # experiment_date = dateInfo[0]
        experiment_date = dateInfo[list(dateInfo.keys())[0]]
        exp_time = dateInfo[list(dateInfo.keys())[1]]

    else:
        core.quit()  # User pressed cancel, so exit

    # Restore the window to full screen mode after dialog interaction
    WIN.winHandle.set_fullscreen(full_screen)
    WIN.flip()

    # Ensure the recording stops properly when the script ends

    # Function to save the recorded audio at the end of the experiment
    def save_block_audio_data(save_path, block_num, experiment_date, exp_time, is_mic=False):
        global global_audio_data
        global mic_audio_data
        
        audio_data = mic_audio_data if is_mic else global_audio_data
        if len(audio_data) > 0:
            print(f"Saving recorded audio for block {block_num}...")
            filename = f'exp{experiment_date}-{exp_time}-block{block_num}-mic_in.wav' if is_mic else f'exp{experiment_date}-{exp_time}-block{block_num}-audio_out.wav'
            if is_mic:
                wav.write(str(save_path / filename), fs, audio_data)
            else:
                wav.write(str(save_path / filename), fs, audio_data.reshape(-1, 2))
            print(f"Audio for block {block_num} saved to {filename}")
        else:
            print(f"No audio data to save for block {block_num}.")
        
        # Reset audio data for the next block
        if is_mic:
            mic_audio_data = np.array([], dtype='float32')
        else:
            global_audio_data = np.array([], dtype='float32')
            
            
    def check_exit_or_continue():
        between_block = "Vous avez terminé le bloc. N'hésitez pas à vous reposer un peu. Lorsque vous êtes prêt, appuyez sur ENTRÉE pour passer au bloc suivant."
        message = visual.TextStim(WIN, text=between_block, color=text_color, wrapWidth=1.5, font='Arial')
        message.draw()
        WIN.flip()

        keys = event.waitKeys(keyList=['return', 'escape'])
        if 'escape' in keys:
            # Save all data before exiting
            events = pd.DataFrame(EVENTS)
            events.to_csv(save_path_events / f'events-{experiment_date}-{exp_time}_all.csv', index=False)
            WIN.close()
            core.quit()


    # display welcome message and instructions 
    display_message(instruction_messages['landing_page'])
    display_message(instruction_messages['instruction_1'])
    display_message(instruction_messages['instruction_2'])
    
    # start audio thread
    audio_thread = Thread(target=record_audio_combined, daemon=True)
    audio_thread.start()

    #######################################
    # start 
    #######################################
    CLOCK = core.Clock()

    sentences = pd.read_csv(sentence_file)
    # sentences = sentences.query("translanted_num_words < @max_words_per_sent")
    words = pd.read_csv(word_file)
    
    if test_mode:
        sentences = sentences.sample(20)
        words = words.sample(20)

    guided_test_block(sentences.iloc[:n_practice_trials])
    block_idx = np.linspace(0, len(sentences), n_blocks+1).astype(int)
    block_idx_w = np.linspace(0, len(words), n_blocks+1).astype(int)
    for b in range(n_blocks):
        print(f"Block {b+1}")
        print(f"sentences {block_idx[b]}:{block_idx[b+1]}")
        print(f"words {block_idx_w[b]}:{block_idx_w[b+1]}")
        block_run(sent_rows=sentences.iloc[block_idx[b]:block_idx[b+1]], word_rows=words.iloc[block_idx_w[b]:block_idx_w[b+1]], block_num=b+1)
        
        # save audio data 
        save_block_audio_data(save_path_recording, b+1, experiment_date, exp_time, is_mic=False)

        check_exit_or_continue()

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


