from logging import captureWarnings
from pickle import NEWFALSE
from posixpath import splitext
from statistics import variance
from pathlib import Path
import sys
import os
import re
import argparse
import shutil
import glob
import clipboard
from datetime import datetime
from datetime import timedelta
from difflib import SequenceMatcher as SM
import time
import cv2
import numpy
import pytesseract

# ---------------- CHECK ABSOLUTE PATH -------------------------------------------------------

# absolute path to tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ---------------- CHECK ABSOLUTE PATH END ---------------------------------------------------

from PIL import ImageGrab
import pyautogui, sys
import pygetwindow

# TBConfig ------------------------------------------------------------------------------------------------------
class TBConfig(object):
    """ This class parses configuration parameters from the configuration file """
# ------------------------------------------------------------------------------------------------------
    def __init__(self, config_file, clickWait):
        config_kvp = {}

        try:

            with open(config_file) as cfp:
                for cl, config_line in enumerate(cfp):
                    
                    kvp_string = config_line.strip()
                    if len(kvp_string) == 0 or kvp_string.find("#") > -1: # ignore empty lines and comments in config file
                        continue
                
                    kvp = kvp_string.split("=")
                    config_kvp[kvp[0].strip()] = kvp[1].strip()
        except:
            print("### FATAL ERROR: Unable to open or read the configuration file: {}").format(config_file)
            exit()
        else:
            self.datafile        = config_kvp.get('data','')
            self.totalfile       = config_kvp.get('total','')
            self.working_dir     = config_kvp.get("working", '')
            self.archive_dir     = config_kvp.get("archive", '')
            self.final_dir       = config_kvp.get("final", '')
            self.player_file     = config_kvp.get('players', '')
            self.clan            = config_kvp.get('clan', '')
            self.quality_file    = config_kvp.get('quality', '')
            self.score_file      = config_kvp.get('score', '')
            self.fix_ocr_file    = config_kvp.get('fix_ocr', '')
            self.x1              = config_kvp.get('x1', '')
            self.y1              = config_kvp.get('y1', '')
            self.x2              = config_kvp.get('x2', '')
            self.y2              = config_kvp.get('y2', '')
            self.mx              = config_kvp.get('mx', '')
            self.my              = config_kvp.get('my', '')
            self.clickWait       = config_kvp.get('clickWait', clickWait)
            self.fixwords        = config_kvp.get('fixwords', '')
            
            # Simplified variables for single clan
            self.clangui         = config_kvp.get('clanname', '') # Uses 'clanname' from config.txt
            self.pshellpath      = config_kvp.get('pspath', '')   # Uses 'pspath' from config.txt
            
            # Global variables for the GUI loop
            global clan_name_gui, pshellpath_gui
            clan_name_gui = self.clangui
            pshellpath_gui = self.pshellpath
                        
# TBScreen ------------------------------------------------------------------------------------------------------
class TBScreen(object):
    """ This class takes the screen capture and runs the OCR processing, and contains image processing functions """
# ------------------------------------------------------------------------------------------------------
#   def init__(self):
 
# ------------------------------------------------------------------------------------------------------
    def get_screenshot(self, x, y, dx, dy):
        image = ImageGrab.grab(bbox=(int(x), int(y), int(dx), int(dy)))
        return image
# ------------------------------------------------------------------------------------------------------
    def get_grayscale(self,img):
        return cv2.cvtColor( img, cv2.COLOR_RGB2GRAY)
# ------------------------------------------------------------------------------------------------------
    def remove_noise(self,img):
        return cv2.medianBlur(img, 5)
# ------------------------------------------------------------------------------------------------------
    def thresholding(self,img):
        return cv2.threshold( img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
# ------------------------------------------------------------------------------------------------------
    def ocr_core(self,img):
        text = pytesseract.image_to_string(img, lang='eng', config='--psm 12 --oem 1')
        return text


# TBFixOCR ------------------------------------------------------------------------------------------------------
class TBFixOCR(object):
    """ This class will attempt to fix known 2-line OCR capture issues. 
        The format in the config file should be:
        CorrectValue, IncorrectFirstine, IncorrectSecondLine
    """
# ------------------------------------------------------------------------------------------------------
    def __init__(self, fix_ocr_file):

        self.fixed = {}
        self.fix_ocr = {}

        if fix_ocr_file:
            with open(fix_ocr_file) as fp:
                for cmt, fix_line in enumerate(fp):
        
                    fix_string = fix_line.strip( " \n")
                    if len(fix_string) == 0 or fix_string.find("#") > -1: # ignore empty lines and comments in config file
                        continue
                    
                    fix_kvp = fix_string.split(",")
                    
                    if len(fix_kvp) != 3:
                        print("\n*** ERROR in Fix OCR file: " + fix_ocr_file + ", line " + str(cmt+1) + " (must be 3 comma separated values)")
                        exit()
                    
                    
                    # CorrectValue, IncorrectFirstine, IncorrectSecondLine
                    # fixed[IncorrectFirstline + IncorrectSecondLine] = CorrectValue
                    # This must be done with lowercase characters
                    fix_kvp[0] = fix_kvp[0].strip()
                    fix_kvp[1] = fix_kvp[1].strip()
                    fix_kvp[2] = fix_kvp[2].strip()
                    self.fixed[fix_kvp[1].lower() + fix_kvp[2].lower()] = fix_kvp[0]


    # ------------------------------------------------------------------------------------------------------
    def fix(self, line1, line2):
        
        fixed_line = self.fixed.get(line1.strip().lower() + line2.strip().lower())

        if fixed_line:
            return fixed_line
        else:
            return None


# TBPlayers ------------------------------------------------------------------------------------------------------
class TBPlayers(object):
    """ This class parses PLAYER configuration parameters and validates player names 
        The format in the config file should be:
        CorrectValue, IncorrectValue1, IncorrectValue2, ...
        (The IncorrectValue will be used with the fuzzy logic from the OCR capture)
    """
# ------------------------------------------------------------------------------------------------------
    def __init__(self, player_file):

        self.alias = {}
        self.alias_fuzzy = {}

        if player_file:
            with open(player_file) as fp:
                for cmt, player_line in enumerate(fp):
        
                    player_string = player_line.strip( " \n")
                    if len(player_string) == 0 or player_string.find("#") > -1: # ignore empty lines and comments in config file
                        continue
                    
                    player_kvp = player_string.split(",")
                    
                    if len(player_kvp) == 0:
                        print("\n*** ERROR in Player file: " + player_file + ", line " + str(cmt+1) + " (must have at least 1 value)")
                        exit()
                    
                    
                    # Alias = Player Name
                    alias = player_kvp[0].strip()
                    self.alias[alias.lower()] = alias

                    # Possible misspellings (aliases)
                    for alias_f in player_kvp:
                        alias_f = alias_f.strip()
                        self.alias_fuzzy[alias_f.lower()] = alias


    # ------------------------------------------------------------------------------------------------------
    def find_player_fuzzy(self, player_name):
        player_name = player_name.strip()
        
        player_lower = player_name.lower()
        
        # Exact match
        player = self.alias_fuzzy.get(player_lower)
        if player:
            return player, 1.0
        
        # Fuzzy match
        max_ratio = 0.0
        best_match = None
        
        for p_alias, p_player in self.alias_fuzzy.items():
            ratio = SM(None, p_alias, player_lower).ratio()
            if ratio > max_ratio:
                max_ratio = ratio
                best_match = p_player
        
        return best_match, max_ratio


    # ------------------------------------------------------------------------------------------------------
    def find_player_simple(self, player_name):
        player_name = player_name.strip()
        player = self.alias.get(player_name.lower())
        
        if player:
            return player
        else:
            return player_name


    # ------------------------------------------------------------------------------------------------------
    def validate(self, player, validate_line_count):

        player = player.strip()
        success = True
        
        if player.find("From") > -1:
            player = player.replace("From", "").strip()

        splitter = ""
        
        if player.find(":") > -1:
            splitter = ":"
        elif player.find(";") > -1:
            splitter = ";"
        elif player.find(".") > -1:
            splitter = "."
        elif player.find(",") > -1:
            splitter = ","

        if splitter == "": # none of the above chars were found in the string
            if player.find(" ") > -1: # split on the first space found
                splitter = " "
                
        if splitter:
            player_list = player.split(splitter)
            if len(player_list) > 1:
                player = player_list[1].strip()
            
            
        player_match, match_ratio = self.find_player_fuzzy(player)

        if match_ratio < 0.8:
            print("\n*** ERROR on line {}: Invalid player name: {}".format( validate_line_count, player))
            print("FUZZY LOGIC: Best match: {}".format(player_match))
            
            # save_alias = input(">>> Please type the correct player-name or type '-' to ignore: ")
            save_alias = player_match # Automatic correction based on best match, set 1.0 to accept all
            
            if not save_alias:
                success = False
            elif save_alias == "-":
                success = False
            else:
                print("\nFUZZY LOGIC: Player {}".format(player))
                print("MAPPED TO : Player {}".format(player_match))
                player = player_match # set player to the correct string
                
        return success, player

# TBChest ------------------------------------------------------------------------------------------------------
class TBChest(object):
    """ This class parses CHEST configuration parameters and validates chest names 
        The format in the config file should be:
        CorrectValue, IncorrectValue1, IncorrectValue2, ...
        (The IncorrectValue will be used with the fuzzy logic from the OCR capture)
    """
# ------------------------------------------------------------------------------------------------------
    def __init__(self, quality_file):

        self.alias = {}
        
        if quality_file:
            with open(quality_file) as fp:
                for cmt, chest_line in enumerate(fp):
        
                    chest_string = chest_line.strip( " \n")
                    if len(chest_string) == 0 or chest_string.find("#") > -1: # ignore empty lines and comments in config file
                        continue
                    
                    chest_kvp = chest_string.split(",")
                    
                    if len(chest_kvp) == 0:
                        print("\n*** ERROR in Chest-Quality file: " + quality_file + ", line " + str(cmt+1) + " (must have at least 1 value)")
                        exit()
                    
                    
                    # Alias = Chest Name
                    alias = chest_kvp[0].strip()
                    self.alias[alias.lower()] = alias

                    # Possible misspellings (aliases)
                    for alias_f in chest_kvp:
                        alias_f = alias_f.strip()
                        self.alias[alias_f.lower()] = alias


    # ------------------------------------------------------------------------------------------------------
    def validate(self, chest, source):
        
        chest = chest.strip()
        success = True
        
        chest_match = self.alias.get(chest.lower())

        if not chest_match:
            
            # The Great Hunt chests have no player attached - special handling
            if chest.find("eat ") > -1 and chest.find("unt") > -1:
                chest_match = "The Great Hunt Chest"
            else:
                print("\n*** ERROR: Invalid chest name: {}".format( chest))
                
                # save_alias = input(">>> Please type the correct chest-name or type '-' to ignore: ")
                save_alias = None # Manual entry is disabled
                
                if not save_alias:
                    success = False
                elif save_alias == "-":
                    success = False
                else:
                    chest = save_alias # set chest to the correct string
        else:
            chest = chest_match # set chest to the correct string
                
        return success, chest

# TBScore ------------------------------------------------------------------------------------------------------
class TBScore(object):
    """ This class parses SCORE configuration parameters """
# ------------------------------------------------------------------------------------------------------
    def __init__(self, score_file):

        self.score_kvp = {}
        self.no_score = set()
        
        if score_file:
            with open(score_file) as fp:
                for cmt, score_line in enumerate(fp):
        
                    score_string = score_line.strip( " \n")
                    if len(score_string) == 0 or score_string.find("#") > -1: # ignore empty lines and comments in config file
                        continue
                    
                    score_kvp = score_string.split(",")
                    
                    if len(score_kvp) != 2:
                        print("\n*** ERROR in Score file: " + score_file + ", line " + str(cmt+1) + " (must be 2 comma separated values)")
                        exit()
                    
                    
                    # Source, Score
                    source = score_kvp[0].strip()
                    score = score_kvp[1].strip()
                    
                    self.score_kvp[source.lower()] = score


    # ------------------------------------------------------------------------------------------------------
    def get_score(self, player, source, chest, line):
        
        score = 0
        
        if source.find("Source") > -1:
            source = source.replace("Source", "").strip()

        splitter = ""
        
        if source.find(":") > -1:
            splitter = ":"
        elif source.find(";") > -1:
            splitter = ";"
        elif source.find(".") > -1:
            splitter = "."
        elif source.find(",") > -1:
            splitter = ","
        else: # extra checks to work around kinks in the OCR software and allow automated processing
            if source.find("Source ") or source.find("ource "):
                source = source.replace("Source ", "").replace("ource ", "").strip()
        
        if splitter:
            source_list = source.split(splitter)
            if len(source_list) > 1:
                source = source_list[1].strip()
        
        # Special handling for Citadel chests
        if source.find("Citadel") > -1:
            # check if citadel level is in the source. If not, it could be in the chest
            citadel_level = ""
            if source.find("Level ") > -1:
                source_list = source.split("Level ")
                if len(source_list) > 1:
                    if source_list[1].find(" ") > -1:
                        citadel_level = source_list[1].split(" ")[0].strip()
                    else:
                        citadel_level = source_list[1].strip()
                        
            if not citadel_level: # Not in source, check chest
                if chest.find("Level ") > -1:
                    chest_list = chest.split("Level ")
                    if len(chest_list) > 1:
                        if chest_list[1].find(" ") > -1:
                            citadel_level = chest_list[1].split(" ")[0].strip()
                        else:
                            citadel_level = chest_list[1].strip()
            
            if citadel_level:
                source = "Level " + citadel_level + " " + source.replace("Level " + citadel_level, "").strip()
                if source.find("cursed Citadel") > -1:
                    source = "Level " + citadel_level + " cursed Citadel"
        
        temp_score = self.score_kvp.get(source.lower())
        
        if temp_score != None:
            score = temp_score
        else:
            print("*** Warning at line {}: No score for {}, {}, {}".format( line, player, source, chest ))
            self.no_score.add(source)
            
        return score
    
    # ------------------------------------------------------------------------------------------------------
    def check_score(self):
        
        if len(self.no_score) > 0:
            print("\n*** Warning: The following sources do not have an assigned score in the score file:")
            for s in self.no_score:
                print(">>> {}".format(s))
            print("Please check your score file for missing values.")


# TBCalibration ------------------------------------------------------------------------------------------------------
class TBCalibration(object):
    """ This class runs the screen calibration (only for the coordinate-values) """
# ------------------------------------------------------------------------------------------------------
    def run(self, config):
        
        mx = config.x1
        my = config.y1
        
        
        while True:
            # move to upper left corner
            print("\n\n>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<")
            print( "#########################################")
            print( ">> CALIBRATION STEP 1: Upper Left Corner")
            print( "#########################################\n")
            print( ">> Only Position the mouse at the UPPER LEFT corner to")
            print( ">> capture the first chest-text and than press <Enter>")
            input(">> Press <Enter> after positioning the mouse...")
            
            mx = pyautogui.position().x
            my = pyautogui.position().y
            
            config.x1 = mx
            config.y1 = my
            
            
            # move to lower right corner
            print("\n\n>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<")
            print( "#########################################")
            print( ">> CALIBRATION STEP 2: Lower Right Corner")
            print( "#########################################\n")
            print( ">> Only Position the mouse at the LOWER RIGHT corner to")
            print( ">> capture the last chest-text and than press <Enter>")
            print( ">> IMPORTANT! Remember, that there are long texts, so")
            print( ">> scroll far to the right to capture the text.\n")
            pyautogui.moveTo(int(config.x2), int(config.y2))
            input(">> Press <Enter> after positioning the mouse...")
            
            mx = pyautogui.position().x
            my = pyautogui.position().y
            
            config.x2 = mx
            config.y2 = my
            
            print("\n\n>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<")
            print(">> You can now save your new coordinates (x1, y1, x2, y2)")
            print(">> to the configuration file.")
            print(">> Open the file: ChestCountHLO/config/config.cfg")
            print(">> x1 = {}".format(config.x1))
            print(">> y1 = {}".format(config.y1))
            print(">> x2 = {}".format(config.x2))
            print(">> y2 = {}".format(config.y2))
            print(">>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<\n\n\n")

            input(">>> Press <Enter> to restart calibration or [eXit] to exit: ")
            
            if choice.lower() == "exit" or choice.lower() == "x":
                break


# TBCapture ------------------------------------------------------------------------------------------------------
class TBCapture(object):
    """ This class runs the screen capture (OCR) and saves the captured data """
# ------------------------------------------------------------------------------------------------------
    def __init__(self, config, args):
        self.config = config
        self.args = args
        self.tb_screen = TBScreen()
        self.fix_ocr = TBFixOCR(config.fix_ocr_file)
        self.player_def = TBPlayers(config.player_file)
        self.chest_def = TBChest(config.quality_file)
        
        
    # ------------------------------------------------------------------------------------------------------
    def run(self):
        
        while True:
            
            # move to upper left corner
            print("\n\n>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<")
            print( "#########################################")
            print( ">> Capture Chest-Data for Clan {}".format(self.config.clangui))
            print( "#########################################\n")
            
            # open new output file
            working_file = self.config.working_dir + "/TB_Capture_RAW_{}_{}.txt".format(self.config.clan, datetime.now().strftime("%Y-%m-%d %H.%M.%S"))
            
            clean_file = self.config.working_dir + "/TB_Capture_Clean_{}_{}.txt".format(self.config.clan, datetime.now().strftime("%Y-%m-%d %H.%M.%S"))
            
            raw_data = ""
            clean_data = ""
            
            print("\n\n>>> Position the mouse at the first chest in the gift-list and press <Enter> (You have 3s!)")
            input(">>> Press <Enter> to start the capture (Press <Ctrl+C> to stop the loop): ")
            time.sleep(3)
            
            while True:
                try:
                    
                    # Capture screen
                    image = self.tb_screen.get_screenshot(self.config.x1, self.config.y1, self.config.x2, self.config.y2)
                    
                    # Image preprocessing (optional)
                    # gray = self.tb_screen.get_grayscale(numpy.array(image))
                    # noise = self.tb_screen.remove_noise(gray)
                    # thresh = self.tb_screen.thresholding(noise)

                    # Tesseract OCR
                    text = self.tb_screen.ocr_core(image)
                    
                    # Clean up the text
                    # Filter out unnecessary lines and fix known OCR issues
                    rows = text.split("\n")
                    fixed = False
                    
                    # Clean up list of lines
                    rows = [row for row in rows if row.strip() != '']
                    
                    # Remove timestamps and empty lines
                    cleaned_rows = []
                    for row in rows:
                        row = row.strip()
                        if re.match(r"^\d{2}:\d{2}:\d{2}", row) or re.match(r"^\d{2}-\d{2}-\d{2}", row) or re.match(r"^\d{4}-\d{2}-\d{2}", row):
                            continue
                        cleaned_rows.append(row)
                    
                    
                    # Fix known 2-line OCR issues
                    fixed_rows = []
                    index = 0
                    while index < len(cleaned_rows):
                        row = cleaned_rows[index]
                        
                        # Fix for known 2-line errors (e.g., 'An' + 'cient Chest')
                        if index + 1 < len(cleaned_rows):
                            fixed_line = self.fix_ocr.fix(row, cleaned_rows[index+1])
                            if fixed_line:
                                fixed_rows.append(fixed_line)
                                index += 2
                                fixed = True
                                continue
                        
                        fixed_rows.append(row)
                        index += 1

                    
                    # Extract Chest and Source
                    capture = ""
                    clean_capture = ""
                    
                    rows = fixed_rows
                    
                    validate_line_count = 1
                    
                    while len(rows) > 0:
                        
                        line = rows.pop(0)
                        chest = line.strip()
                        success, chest = self.chest_def.validate(chest, rows[0] if len(rows) > 0 else "")
                        validate_line_count += 1
                        
                        if not success:
                            # print("\n*** ERROR: Invalid chest name or missing chest name in capture. Skipping this block.")
                            break # Skip the rest of the block if chest validation fails

                        
                        line = rows.pop(0)
                        player = line.strip()
                        # The Great Hunt chests have no player attached
                        if chest.find("eat ") > -1 and chest.find("unt") > -1:
                            success = True
                            player = "The Great Hunt"
                        else:
                            success, player = self.player_def.validate(player, validate_line_count)
                        validate_line_count += 1
                        
                        if not success:
                            # print("\n*** ERROR: Invalid player name or missing 'From' line in capture. Skipping this block.")
                            break # Skip the rest of the block if player validation fails

                        
                        line = rows.pop(0)
                        source = line.strip()
                        
                        clean_capture += chest + "\n"
                        clean_capture += "From : " + player + "\n"
                        clean_capture += source + "\n"
                        
                        raw_data += text
                        
                        raw_data += "--------------- {} --------------------------\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        
                        
                    # Save to working file
                    with open(working_file, "a", encoding="utf-8") as f:
                        f.write(raw_data)
                    raw_data = "" # Clear buffer
                    
                    with open(clean_file, "a", encoding="utf-8") as f:
                        f.write(clean_capture)
                    clean_data = "" # Clear buffer
                    
                    print("\n" + clean_capture.strip())
                    print("----------------------------------------------------------------")
                    
                    
                    # Scroll down
                    pyautogui.scroll(-20)
                    time.sleep(float(self.config.clickWait))
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"\n\n*** ERROR: An error occurred during capture. Check the raw file. Error: {e}")
                    time.sleep(2)
                    break
                    
            
            # Ask for next action
            choice = input("\n\n>>> [Enter] to continue capture or [eXit] to exit: ")
            if choice.lower() == "exit" or choice.lower() == "x":
                break
                
        
        print("\n\n>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<")
        print(">> Capture finished. Raw data saved to: {}".format(working_file))
        print(">> Clean data saved to: {}".format(clean_file))
        print(">>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<\n\n\n")


# TBProcess ------------------------------------------------------------------------------------------------------
class TBProcess(object):
    """ This class processes the captured data and generates the summary files """
# ------------------------------------------------------------------------------------------------------
    def __init__(self, config, args):
        self.config = config
        self.args = args
        self.player_def = TBPlayers(config.player_file)
        self.chest_def = TBChest(config.quality_file)
        self.score_def = TBScore(config.score_file)
        self.fixwords = TBFixOCR(config.fixwords) # fixwords uses the same structure as fix_ocr
        
        self.clan_summary = {} # ClanName: [TotalScore, TotalChests, TotalCitadels, TotalCrypts, TotalRunicRaids, TotalVaults, TotalHeroicMonsters]
        
    # ------------------------------------------------------------------------------------------------------
    def process_file(self, inputfile, processing_date):
        
        datafile = self.config.datafile
        totalfile = self.config.totalfile
        player_summary = {} # PlayerName: [Score, ChestCount]
        
        clan_name = self.config.clan
        
        with open(inputfile, "r", encoding="utf-8") as fp:
            data = fp.read()
        
        lines = data.strip().split("\n")
        
        if len(lines) % 3 != 0:
            print(f"\n*** ERROR: El archivo de entrada '{inputfile}' tiene un número de líneas incorrecto. Debe ser un múltiplo de 3 (Chest, Player, Source).")
            return False, player_summary

        
        # ------------------------ Find Epic Chests, which is not in Source, but in Line 1 --------------------------------------------
        # No se necesita una reescritura de archivos para la detección de Epic Chests si se valida en TBScore
        
        
        # ------------------------ Process captured data ----------------------------------------------------------------------------
        
        output_data = "DATE,PLAYER,SOURCE,CHEST,SCORE,CLAN\n"
        
        for i in range(0, len(lines), 3):
            chest = lines[i].strip()
            player_line = lines[i+1].strip()
            source_line = lines[i+2].strip()
            
            # --- Fix common OCR word errors in Source line ---
            fixed_source = self.fixwords.fix(source_line, "")
            if fixed_source:
                source_line = "Source : " + fixed_source

            # -------------------- Validate and get player/chest --------------------
            # Chest validation (Uses the logic from TBCapture, but simplified since we have 3 lines now)
            success_c, chest_name = self.chest_def.validate(chest, source_line)
            
            # Player validation
            success_p, player_name = self.player_def.validate(player_line, i+2)
            
            if not success_c or not success_p:
                print(f"*** Warning: Skipping entry starting at line {i+1} due to validation error.")
                continue

            # -------------------- Get Score --------------------
            score = self.score_def.get_score(player_name, source_line, chest_name, i+3)
            
            # -------------------- Update Player Summary --------------------
            if player_name not in player_summary:
                player_summary[player_name] = [0, 0] # [Score, ChestCount]
                
            player_summary[player_name][0] += int(score)
            player_summary[player_name][1] += 1
            
            # -------------------- Update Clan Summary (Simple Chest/Score count) --------------------
            if clan_name not in self.clan_summary:
                # [TotalScore, TotalChests] - simplified
                self.clan_summary[clan_name] = [0, 0]
            
            self.clan_summary[clan_name][0] += int(score)
            self.clan_summary[clan_name][1] += 1
            
            # -------------------- Write Final Line --------------------
            output_data += f"{processing_date},{player_name},{source_line.replace('Source : ', '').strip()},{chest_name},{score},{clan_name}\n"

        # ---------------------- Write Final Output File -------------------------------------------
        file_dir = os.path.dirname(os.path.abspath(inputfile))
        ofile = file_dir + '/' + processing_date + '_TB_Chests_' + self.config.clan + '_FINAL.txt'
        
        with open(ofile, "w", encoding="utf-8") as opf:
            opf.write(output_data)

        # ---------------------- Write Player Summary File -------------------------------------------
        p_summary_file = file_dir + '/' + processing_date + '_TB_PlayerSummary_' + self.config.clan + '_FINAL.txt'
        
        p_output_data = "PLAYER,SCORE,CHEST\n"
        
        # Sort by score (descending)
        player_summary_sorted = dict(sorted(player_summary.items(), key=lambda item: item[1][0], reverse=True))

        for player, data in player_summary_sorted.items():
            p_output_data += f"{player},{data[0]},{data[1]}\n"
        
        with open(p_summary_file, "w", encoding="utf-8") as opf:
            opf.write(p_output_data)
        
        print("\n\n>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<")
        print(">> Process finished. Final data saved to: {}".format(ofile))
        print(">> Player Summary saved to: {}".format(p_summary_file))
        print(">>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<\n\n\n")

        self.score_def.check_score()

        return True, player_summary

    # ------------------------------------------------------------------------------------------------------
    def run(self):
        
        # ------------------------ Find Input File ----------------------------------------------------------
        clan_name = self.config.clan
        inputfile = self.config.working_dir + "/TB_Capture_Clean_{}_*.txt".format(clan_name)
        file_list = glob.glob(inputfile)
        
        if not file_list:
            print("\n*** ERROR: No clean capture files found for Clan {} in {}.".format(clan_name, self.config.working_dir))
            return
        
        # Use the most recent file
        inputfile = max(file_list, key=os.path.getctime)
        
        print("\n\n>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<")
        print(">> Processing file: {}".format(inputfile))
        print(">>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<\n\n\n")
        
        # ------------------------ Run Processing ------------------------------------------------------------
        current_date = datetime.now().strftime("%Y-%m-%d")
        success, player_summary = self.process_file(inputfile, current_date)
        
        if success:
            # ------------------------ Move file to Archive --------------------------------------------------
            archive_file = self.config.archive_dir + "/" + os.path.basename(inputfile)
            shutil.move(inputfile, archive_file)
            print(">> File moved to archive: {}".format(archive_file))


# ------------------- START ------------------------------------------------------------------------------

parser = argparse.ArgumentParser()
parser.add_argument('--calibrate', action='store_true', help='Calibrate screen coordinates')
parser.add_argument('--capture', action='store_true', help='Capture screen data')
parser.add_argument('--process', action='store_true', help='Process captured data')
parser.add_argument('--clan', type=str, default='HALO', help='Clan name for capture/process (e.g., HALO)')
parser.add_argument('--clanID', type=int, default=1, help='Clan ID (1-4) for configuration')
args = parser.parse_args()

# default config.cfg location
config_file = "../config/config.cfg"

# default clickWait
clickWait = 1.0

# Initialize config
config = TBConfig(config_file, clickWait)


if args.calibrate:
    app1 = TBCalibration()
    app1.run(config)
elif args.capture:
    app2 = TBCapture(config, args)
    app2.run()
elif args.process:
    app3 = TBProcess(config, args)
    app3.run()

# ------------------- START PS GUI ------------------------------------------

while True: 
    print("\n")
    print(">>> Back to PowerShell GUI?")
    # Usa la variable global simplificada
    print(">>> 1 : Clan {}".format(clan_name_gui))
    print(">>> all other keys for Exit \n")
    import subprocess
    
    # El prompt solo pide [1] o [eXit]
    choice = input("[1] or [eXit] ? ")
    
    if choice.lower() == "1":
            # Usa la variable global simplificada
            command = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"{pshellpath_gui}\""
            result = subprocess.run(command)
            break
    else:
            break