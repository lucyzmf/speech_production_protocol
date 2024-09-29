from pathlib import Path

root_path = Path('/Users/lucy/Documents/PhD stuff/research/speech_production_protocol')

# paths 
sentence_file = root_path / "text" / "selected_with_translation_audiopath.csv"
word_file = root_path / "text" / "selected_words_final_audiopath.csv"
save_path_recording = root_path / "recordings"
save_path_events = root_path / "output_events"


# exp parameters
test_mode = True
max_words_per_sent = 9

full_screen = False

if test_mode:
    n_blocks = 1
    n_sent_trials_per_block = 2
    n_practice_trials = 1
    n_word_repeats_per_subblock = 2
    n_subblocks = 1
else:
    n_blocks = 4
    n_sent_trials_per_block = 16
    n_practice_trials = 4
    n_word_repeats_per_subblock = 2
    n_subblocks = 4
    
    

n_trial_runs = 4

# block parameters
n_beeps_on_block_start = 3
 # one repeat of sent and words


# trial parameters 
mode_start_beep_secs = 0.2
mode_start_beep_wait = 0.2

mode_end_beep_secs = 0.2
mode_end_beep_wait = 0.2

mode_end_wait = 0.5

inter_mode_wait = 0.5
trial_end_wait = 1

audio_end_wait = 0.5




# asthetics
fixation_size = 0.1
text_size = 0.1
text_color = (1, 1, 1)
screen_color = (-0.6875, -0.6875, -0.66406)