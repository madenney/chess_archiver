import os
import time
import random
import pyautogui

from selenium import webdriver
from selenium.webdriver.common.by import By


DOWNLOAD_PATH = '/home/matt/Downloads'
PGN_FOLDER_PATH = '/home/matt/Projects/charkiver/pgn'
CURRENT_PLAYER = 'magnus'
STARTING_PAGE = "https://www.chess.com/games/magnus-carlsen"


def click_verification_button():
    print('clicking verification button')
    pyautogui.moveTo(288,1027)
    pyautogui.click()

def get_games_from_page(driver, page):

    print("Download from page " + str(page))
    url = driver.current_url
    try:
        # select all and click download
        check_all_button = driver.find_element(By.ID, 'master-games-check-all')
        driver.execute_script("arguments[0].scrollIntoView();", check_all_button)
        check_all_button.click()
        download_all_button = driver.find_element(By.CLASS_NAME, 'master-games-download-icon')
        driver.execute_script("arguments[0].scrollIntoView();", download_all_button)
        download_all_button.click()

        # wait for download to complete, then move it to PGN folder
        dl_wait = True
        count = 0
        while dl_wait:
            print("wait loop")
            count+=1
            if(count > 5):
                print("waited too long")
                raise Exception('waited too long')
            time.sleep(0.5)
            files = os.listdir(DOWNLOAD_PATH)
            if 'master_games.pgn' in files:
                dl_wait = False
                os.rename(DOWNLOAD_PATH+'/master_games.pgn', PGN_FOLDER_PATH + '/' + CURRENT_PLAYER + '/' + str(page) + '.pgn')
                return driver 

    except Exception as e:
        print("caught exception, failed to download")
        print("Reloading: ", url)
        driver.close()
        print("waiting 10 seconds...")
        time.sleep(10)
        driver = set_up_window(url)
        get_games_from_page(driver, page)
        return driver
        # print(e)
        # while True:
        #     try:
        #         challenge = driver.find_element(By.ID, 'challenge-stage')
        #         if challenge:
        #             print("Challenge.")
        #             input = challenge.find_element(By.CSS_SELECTOR, 'input')
        #             print("Location:", challenge.location)
        #             click_verification_button()
        #             time.sleep(20)
        #             get_games_from_page(driver, page)


        #     except Exception as e:
        #         print("trying to get past human check")
        #         print(e)
        #         time.sleep(1)
                




def goto_next_page(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    next_button = driver.find_element(By.CLASS_NAME, 'chevron-right')
    if not next_button:
        return False
    try:
        next_button.click()
    except Exception:
        return False
    return True





def set_up_window(url):
    print("Setting up window")
    driver = webdriver.Firefox(executable_path='/home/matt/Projects/charkiver/geckodriver')
    # open page and move to top left
    driver.get(url)
    driver.set_window_position(0,0)
    return driver


page = 1
driver = set_up_window(STARTING_PAGE)

while True:
    driver = get_games_from_page(driver, page)
    page += 1
    randint = random.randint(3,7)
    print("waiting " + str(randint) + " seconds...")
    time.sleep(randint)
    if not goto_next_page(driver):
        break

driver.close()













# x = 'ffmpeg -f x11grab -s 1920x1080 -r 30 -i :1.0+0,400 -qscale 0 -vcodec huffyuv -f pulse -ac 2 -i default bigtest.avi'

# cmd = ['ffmpeg','-f','x11grab','-s','1920x1080','-r','30','-i',':1.0+0,400','-f','alsa','-ac','2','-i','hw:0','-qscale','0','-vcodec','huffyuv',fileName]
# cmd = ['ffmpeg','-f','x11grab','-s','728x728','-r','60','-i',':1.0+260,805','-f','alsa','-i','default','-c:v','h264','-b:v','15000k', '-c:a', 'aac', '-b:a', '192k', fileName]
