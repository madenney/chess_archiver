import os
import io
import sys
import time
import signal
from datetime import datetime
import pyperclip
import subprocess

import warnings
import asyncio
import pyautogui

import numpy as np
import common as c


import chess
import chess.pgn

from selenium import webdriver
from selenium.webdriver.firefox.service import Service

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PIL import Image, ImageOps, ImageDraw, ImageFont

TIME_PER_MOVE = 0.4
MIN_MOVES = 50
PRE_GAME_PAUSE = 0.5
POST_GAME_PAUSE = 2
SHUFFLE = True

X_0 = -30
Y_0 = 490

GECKODRIVER_PATH = '/home/matt/Projects/chess_archiver/geckodriver'
service = Service(executable_path=GECKODRIVER_PATH)
options = webdriver.FirefoxOptions()
AUDIO_SOURCE = 'alsa_output.usb-Generic_USB_Audio-00.iec958-stereo.monitor'
RECORDING_COORDS = [352,663]
WINDOW_WIDTH = 856
WINDOW_HEIGHT = 876

def set_up_window(game):
    driver = webdriver.Firefox(service=service, options=options)

    # open page and move to top left
    driver.get("https://www.chess.com/analysis?tab=analysis")
    driver.set_window_position(X_0,Y_0)
    driver.maximize_window()
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
    time.sleep(0.25)
    select_dropdown = driver.find_element(By.ID, "settings-analysis-engine-name")
    select_dropdown.click()

    off = select_dropdown.find_element(By.XPATH, f"//*[@value='OFF']")
    off.click()

    backdrop = driver.find_element(By.CLASS_NAME, 'ui_outside-close-icon')
    backdrop.click()

    return driver


def start_recording_process(file_name):
    r = RECORDING_COORDS
    cmd = ['ffmpeg','-thread_queue_size','1024', '-f','x11grab','-s',\
        f'{WINDOW_WIDTH}x{WINDOW_HEIGHT}','-r','60','-i',f':1.0+{r[0]},{r[1]}',\
        '-f','pulse','-ac','2','-i',AUDIO_SOURCE,'-vcodec','libx264', \
        '-crf', '0','-x264-params','keyint=1',file_name]

    #print(" ".join(cmd))
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def play_game(driver, game): 
    actions = ActionChains(driver)
    for move in game.mainline():
        time.sleep(TIME_PER_MOVE)
        actions.send_keys(Keys.ARROW_RIGHT)
        actions.perform()

def read_pgn_file(file_path, counter, limit):
    counter[0] += 1
    print(f"Reading PGN files - [{counter[0]}/{counter[1]}]", end='\r')
    games = []

    file_size = os.path.getsize(file_path)
    print(f"file size: {file_size} bytes")


    if file_size > 1000000:
        print("opening file in pieces")
        count = 0
        with open(file_path) as pgn_file:
            current_game = ""
            for line in pgn_file:
                current_game += line

                # Check if the line marks the end of a game
                if line.strip() == "1-0" or line.strip() == "0-1" or line.strip() == "1/2-1/2" or line.strip() == "*":

                    count += 1
                    if count % 100 == 0:
                        print(f"read count: {count}, found {len(games)} matches", end='\r')

                    game = chess.pgn.read_game(io.StringIO(current_game))
                    if filter_game(game):
                        counter[2] += 1
                        games.append( game )
                        if counter[2] >= limit:
                            print(f"read count: {count}, found {len(games)} matches", end='\r')
                            break
                    current_game = ""
            print("\nDone reading.")
    else:
        with open(file_path) as file:
            while True:
                game = chess.pgn.read_game(file)
                counter[2] += 1 
                if game is None:
                    break  
                games.append(game)
    return games

def read_pgn_files(path, counter, limit):
    games = []
    if os.path.isfile(path):
        games = np.concatenate((games, read_pgn_file(path, counter, limit)))
    elif os.path.isdir(path):
        for filename in os.listdir(path):
            sub_path = os.path.join(path, filename)
            games = np.concatenate(( games, read_pgn_files(sub_path, counter, limit)))
    return games

def filter_game(game):
    info = extract_game_info(game)

    # must have player
    player = "capablanca"
    white = info['white']
    black = info['black']

    if not ( player in black.lower() or player in white.lower() ):
        return False
    
    # if not ( 'ob' in black.lower() or 'ob' in white.lower() ):
    #     return False

    # must have precise date
    # if len(info['date']) < 5:
    #     return False
    # min moves
    move_count = 0
    for move in game.mainline():
        move_count += 1
    if move_count < MIN_MOVES:
        return False

    # only victories
    # result = game.headers["Result"]
    # if result != "1-0":
    #     return False

    # only time stamped games
    # for move in game.mainline():
    #     if not move.comment:
    #         return False
    return True

def filter_games(games):
    return list( filter( filter_game, games))

def add_overlay(index, video_path, info):
    
    image = Image.new("RGBA", (WINDOW_WIDTH, WINDOW_HEIGHT), color=(0,0,0,0))
    draw = ImageDraw.Draw(image)
    
    draw.rectangle([0,WINDOW_HEIGHT-20,WINDOW_WIDTH,WINDOW_HEIGHT],fill=(0,0,0))
    font = ImageFont.truetype("./assets/cour_bold.ttf", 14)
    text_color = (255, 255, 255)  # White
    player_text_position = (20, WINDOW_HEIGHT - 15)
    player_text = f'W - {info["white"]}'
    if info["white_elo"] != "":
        player_text += f'({info["white_elo"]})'
    player_text += "  vs  " 
    player_text += f'B - {info["black"]}'
    if info["black_elo"]:
        player_text += f' ({info["black_elo"]})'
        
    date_text_position = (WINDOW_WIDTH - (len(info["date"]) * 10 ), WINDOW_HEIGHT - 16)
    draw.text(player_text_position, player_text, fill=text_color, font=font)
    draw.text(date_text_position, info["date"], fill=text_color, font=font )

    image_path = os.path.join(os.path.dirname(video_path),f"{str(index)}.png")
    output_path = os.path.join(os.path.dirname(video_path),f"{str(index)}.mkv")
    image.save(image_path)

    overlay_cmd = ['ffmpeg', '-i', video_path, '-i', image_path, '-b:v', '15000k', \
        '-filter_complex', '[0:v][1:v]overlay', output_path ]
    # print(" ".join(overlay_cmd))
    subprocess.run(overlay_cmd,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    os.remove(video_path)
    os.remove(image_path)

def extract_game_info(game):
    info = {}
    info["white"] = game.headers["White"]
    info["black"] = game.headers["Black"]
    try:
        info["white_elo"] = game.headers["WhiteElo"]
        info["black_elo"] = game.headers["BlackElo"]
    except:
        info["white_elo"] = ""
        info["black_elo"] = ""

    date = game.headers["Date"]
    if '??.??' in date:
        info["date"] = date[0:date.find(".")]
    else:
        try:
            date_obj = datetime.strptime(date, '%Y.%m.%d')
            info["date"] = date_obj.strftime('%m/%d/%Y')
        except ValueError:
            info["date"] = date.replace(".","/")

    # info["time_control"] = game.headers["TimeControl"]
    return info
    

async def main():

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
    
    # current pgn file count, pgn file limit, current game count
    counter = [0,0,0]
    if not os.path.isdir(input_path):
        counter[1] = 1
    else:
        for root, dirs, files in os.walk(input_path):
            counter[1] += len(files)
    games = read_pgn_files( input_path, counter, limit )
    print(f"Reading PGN files - [{counter[1]}/{counter[1]}]")
    #print("Total Games: ", len(games))
    
    #games = filter_games(games)
    print("Filtered Games: ", len(games))

    if SHUFFLE:
        np.random.shuffle(games)

    output_dir = c.create_output_dir(output_dir_path)
    print("Output Dir: ", output_dir)
    count = 1
    for game in games:
        if count > int(limit):
            break
        print("Game #", count)
        
        try:
            game_info = extract_game_info(game)

            print("- setting up window")
            driver = set_up_window(game)

            file_name = output_dir + "/" + str(count) + "-pre-overlay.mkv"
            recording_process = start_recording_process(file_name)
            print("- pre game pause")
            await asyncio.sleep(PRE_GAME_PAUSE)
            print("- playing game")
            play_game( driver, game )
            print("- end game pause")
            await asyncio.sleep(POST_GAME_PAUSE)
            #await asyncio.sleep(buffer_time)
            recording_process.send_signal(signal.SIGINT)
            recording_process.kill()
            driver.close()

            add_overlay(count, file_name, game_info)
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
