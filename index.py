import os
import sys
import time
import signal
import pyperclip
import subprocess

import warnings
import asyncio
import pyautogui

import numpy as np

from pgn_parser import parser, pgn

import chess
import chess.pgn

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
warnings.filterwarnings("ignore", category=DeprecationWarning)


GECKODRIVER_PATH = '/home/matt/Projects/charkiver/geckodriver'
AUDIO_SOURCE = 'alsa_output.usb-Razer_Razer_BlackShark_V2_Pro-00.analog-stereo.monitor'

def set_up_window(game):
    driver = webdriver.Firefox(executable_path='/home/matt/Projects/charkiver/geckodriver')

    # open page and move to top left
    driver.get("https://www.chess.com/analysis?tab=analysis")
    driver.set_window_position(0,0)

    # copy PGN data
    pgn_text = game.accept(chess.pgn.StringExporter())
    pyperclip.copy(pgn_text)

    # paste PGN data
    dropzone = driver.find_element(By.XPATH, f"//*[@data-cy='pgn-textarea']" )
    actions = ActionChains(driver)
    actions.move_to_element(dropzone)
    actions.key_down(Keys.LEFT_CONTROL)
    actions.send_keys('v')
    actions.key_up(Keys.LEFT_CONTROL)
    actions.perform() 

    # load game
    xpath_expression = f"//*[@data-cy='add-games-btn']"
    load_game_button = driver.find_element(By.XPATH, xpath_expression)
    load_game_button.click()

    # change game replay settings
    settings_button = driver.find_element(By.ID, 'board-controls-settings')
    settings_button.click()

    select_dropdown = driver.find_element(By.ID, "settings-analysis-engine-name")
    select_dropdown.click()

    off = select_dropdown.find_element(By.XPATH, f"//*[@value='OFF']")
    off.click()

    backdrop = driver.find_element(By.CLASS_NAME, 'ui_outside-close-icon')
    backdrop.click()

    return driver


def start_recording_process(file_name):
    cmd = ['ffmpeg','-f','x11grab','-s','728x728','-r','30','-i',':1.0+260,805','-f','pulse','-i',AUDIO_SOURCE,'-c:v','h264', file_name]
    #cmd = ['ffmpeg','-video_size','728x728','-framerate','30','-f','x11grab','-i',':1.0+260,805','-f','pulse','-ac','2','-i',AUDIO_SOURCE,file_name]
    cmd = ['ffmpeg','-thread_queue_size','1024', '-f','x11grab','-s','728x728','-r','60','-i',':1.0+260,805','-f','pulse','-ac','2','-i',AUDIO_SOURCE,'-vcodec','libx264', '-crf', '0','-x264-params','keyint=1',file_name]
#     s = 'ffmpeg -f x11grab -s 728x728 -r 60 -i :1.0+260,805 -f alsa -i hw:0,1,2,3 -c:v h264 -b:v 15000k -c:a aac -b:a 192k output.mp4'
# #     cmd = ['ffmpeg','-f','alsa','-ac','2','-i','pulse','-f','x11grab','-r','25','-s','1366x768','-i',':0.0','\
# # -vcodec','libx264','-pix_fmt','yuv420p','-preset','ultrafast','-crf','0','-threads','0','\
# # -acodec','pcm_s16le','-y', file_name]
    print(" ".join(cmd))
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def play_game(driver, game):
    # pyautogui.moveTo(1235,1510)
    # for move in game.mainline():
    #     time.sleep(0.2)
    #     pyautogui.click()
    
    actions = ActionChains(driver)
    for move in game.mainline():
        time.sleep(0.05)
        actions.send_keys(Keys.ARROW_RIGHT)
        actions.perform()




def read_pgn_file(path, counter):
    counter[0] += 1
    print(f"Reading PGN files - [{counter[0]}/{counter[1]}]", end='\r')
    games = []
    with open(path) as file:
        while True:
            game = chess.pgn.read_game(file)
            if game is None:
                break  
            games.append(game)
    return games

def read_pgn_files(path, counter):
    games = []
    if os.path.isfile(path):
        games = np.concatenate((games, read_pgn_file(path, counter)))
    elif os.path.isdir(path):
        for filename in os.listdir(path):
            sub_path = os.path.join(path, filename)
            games = np.concatenate(( games, read_pgn_files(sub_path, counter)))
    return games

def filter_game(game):

    # min moves
    move_count = 0
    for move in game.mainline():
        move_count += 1
    if move_count < 3:
        return False

    # only victories
    result = game.headers["Result"]
    if result != "1-0":
        return False

    # only time stamped games
    # for move in game.mainline():
    #     if not move.comment:
    #         return False
    return True

def filter_games(games):
    return list( filter( filter_game, games))

def create_output_dir(output_dir):
    dir_name = 'output'
    count = 0
    while(dir_name in os.listdir(output_dir)):
        count += 1
        dir_name = 'output' + str(count)

    final_path = output_dir + "/" + dir_name
    os.mkdir(final_path)
    return final_path

def float_to_hhmmssms(seconds):
    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}.{milliseconds:03d}"

def get_length(filename):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    return float(result.stdout)

def trim_file(file_name, new_file_name, desired_video_length):
    print("desired video length: ", desired_video_length)
    trim_time = float_to_hhmmssms( desired_video_length )
    print('trim -> ', trim_time)
    cmd = ['ffmpeg', '-i', file_name, '-ss', '0', '-t', trim_time, '-c', 'copy', new_file_name]
    subprocess.run(cmd,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

async def main():

    pre_game_pause = 0.3
    post_game_pause = 1
    buffer_time = 5
    shuffle = True

    if len(sys.argv) < 3:
        print("Usage: python3 index.py <file_or_directory> <output_dir> <?limit>")
        return

    input_path = sys.argv[1]
    output_dir_path = sys.argv[2]
    if len(sys.argv) > 3:
        try:
            limit = int(sys.argv[3])
        except ValueError:
            print("Usage: python3 index.py <file_or_directory> <output_dir> <?limit>")
            print("limit must be integer")
            return
    else:
        limit = 1
    
    counter = [0,0]
    if not os.path.isdir(input_path):
        counter[1] = 1
    else:
        for root, dirs, files in os.walk(input_path):
            counter[1] += len(files)
    games = read_pgn_files( input_path, counter )
    print(f"Reading PGN files - [{counter[1]}/{counter[1]}]")
    print("Total Games: ", len(games))
    
    games = filter_games(games)
    print("Filtered Games: ", len(games))

    if shuffle:
        np.random.shuffle(games)

    output_dir = create_output_dir(output_dir_path)
    print("Output Dir: ", output_dir)
    count = 1
    for game in games:
        if count > int(limit):
            break
        print("Game #", count)
        
        try:
            print("- setting up window")
            driver = set_up_window(game)

            file_name = output_dir + "/" + str(count) + ".mkv"
            recording_process = start_recording_process(file_name)
            start_time = time.time()
            print("- pre game pause")
            await asyncio.sleep(pre_game_pause)
            print("- playing game")
            play_game( driver, game )
            print("- end game pause")
            await asyncio.sleep(post_game_pause)
            #await asyncio.sleep(buffer_time)
            recording_process.send_signal(signal.SIGINT)
            recording_process.kill()
            new_file_name = output_dir + "/" + str(count) + ".mkv"
            #print("- trimming file")
            #trim_file(file_name, new_file_name, time.time() - start_time)
            #os.remove(file_name)
            driver.close()
            count += 1
        except Exception as e:
            print("Exception: ", e)
            try:
                recording_process.kill()
            except Exception:
                print("Tried and failed to kill recording process")
            try:
                driver.close()
            except Exception:
                print("Tried and failed to close webdriver")



if __name__ == "__main__":
    asyncio.run(main())









# x = 'ffmpeg -f x11grab -s 1920x1080 -r 30 -i :1.0+0,400 -qscale 0 -vcodec huffyuv -f pulse -ac 2 -i default bigtest.avi'

# cmd = ['ffmpeg','-f','x11grab','-s','1920x1080','-r','30','-i',':1.0+0,400','-f','alsa','-ac','2','-i','hw:0','-qscale','0','-vcodec','huffyuv',fileName]
# cmd = ['ffmpeg','-f','x11grab','-s','728x728','-r','60','-i',':1.0+260,805','-f','alsa','-i','default','-c:v','h264','-b:v','15000k', '-c:a', 'aac', '-b:a', '192k', fileName]
