import os
import sys
import time
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


def start_recording_process(fileName):
    cmd = ['ffmpeg','-f','x11grab','-s','728x728','-r','60','-i',':1.0+260,805','-f','alsa','-i','default','-c:v','h264','-b:v','15000k', '-c:a', 'aac', '-b:a', '192k', fileName]
    cmd = ['ffmpeg','-f','alsa','-ac','2','-i','pulse','-f','x11grab','-r','25','-s','1366x768','-i',':0.0','\
-vcodec','libx264','-pix_fmt','yuv420p','-preset','ultrafast','-crf','0','-threads','0','\
-acodec','pcm_s16le','-y', fileName]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,)


def play_game(driver, game):
    pyautogui.moveTo(1235,1510)
    for move in game.mainline():
        pyautogui.click()


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
    for move in game.mainline():
        if not move.comment:
            return False
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



async def main():

    post_game_pause = 3

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

    output_dir = create_output_dir(output_dir_path)
    print("Output Dir: ", output_dir)
    count = 1
    for game in games:
        if count > int(limit):
            break
        print("Game #", count)
        count += 1
        
        print("- setting up window")
        driver = set_up_window(game)
        fileName = output_dir + "/" + str(count) + ".mkv"
        recording_process = start_recording_process(fileName)
        print("- playing game")
        play_game( driver, game )
        print("- end game pause")
        await asyncio.sleep(post_game_pause)
        recording_process.kill()
        driver.close()


if __name__ == "__main__":
    asyncio.run(main())









# x = 'ffmpeg -f x11grab -s 1920x1080 -r 30 -i :1.0+0,400 -qscale 0 -vcodec huffyuv -f pulse -ac 2 -i default bigtest.avi'

# cmd = ['ffmpeg','-f','x11grab','-s','1920x1080','-r','30','-i',':1.0+0,400','-f','alsa','-ac','2','-i','hw:0','-qscale','0','-vcodec','huffyuv',fileName]
# cmd = ['ffmpeg','-f','x11grab','-s','728x728','-r','60','-i',':1.0+260,805','-f','alsa','-i','default','-c:v','h264','-b:v','15000k', '-c:a', 'aac', '-b:a', '192k', fileName]
