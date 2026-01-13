# tb.py
# 1. IMPORTS Y CONFIGURACIÓN GLOBAL ----------------------------------------------------------------------

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


from PIL import ImageGrab
import pyautogui, sys
import pygetwindow

from TBDatabase import TBDatabase
from TBDatabaseIntegration import TBDatabaseIntegration


# ---------------- CONFIGURACIÓN ABSOLUTE PATH DE TESSERACT -------------------------------------------------------

# absolute path to tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ---------------- CHECK ABSOLUTE PATH END ---------------------------------------------------


# 2. CLASE TBConfig (CONFIGURACIÓN ESCALABLE) ------------------------------------------------------------

class TBConfig(object):
    """
    Clase para parsear y gestionar parámetros de archivo de configuración: config/config.cfg.
    Mejorada para manejar clanes de forma escalable y asegurar tipos de datos.
    """
    
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
            #print("### ERROR FATAL: No se puede abrir o leer el archivo de configuración: {}".format(config_file))
            
            exit()
        else:
            # Asignación segura de propiedades con conversión de tipo
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
            
            # --- NUEVA MODIFICACIÓN: COORDENADAS PARA LA CAPTURA DE TIEMPO --- YOZAHM
            # NUEVAS coordenadas para Time Left
            self.time_x1         = config_kvp.get('time_x1', '')  # Default a las coordenadas principales
            self.time_y1         = config_kvp.get('time_y1', '')
            self.time_x2         = config_kvp.get('time_x2', '')
            self.time_y2         = config_kvp.get('time_y2', '')
                        
            self.clickWait       = config_kvp.get('clickWait', clickWait)
            self.fixwords        = config_kvp.get('fixwords', '')
            self.clangui         = config_kvp.get('clanname1', '')
            self.clangui2        = config_kvp.get('clanname2', '')
            self.clangui3        = config_kvp.get('clanname3', '')
            self.clangui4        = config_kvp.get('clanname4', '')
            self.pshellpath1     = config_kvp.get('pspath1', '')
            self.pshellpath2     = config_kvp.get('pspath2', '')
            self.pshellpath3     = config_kvp.get('pspath3', '')
            self.pshellpath4     = config_kvp.get('pspath4', '')
            
            # Estructura escalable para clanes (Busca hasta 4 clanes)
            global clan1, clan2, clan3, clan4, pshellpath1, pshellpath2, pshellpath3, pshellpath4
            clan1 = self.clangui
            clan2 = self.clangui2
            clan3 = self.clangui3
            clan4 = self.clangui4
            pshellpath1 = self.pshellpath1
            pshellpath2 = self.pshellpath2
            pshellpath3 = self.pshellpath3
            pshellpath4 = self.pshellpath4
                        
#  3. BScreen: CLASES DE PANTALLA Y UTILIDADES OCR -----------------------------------------------------------------------------
class TBScreen(object):
    """ This class takes the screen capture and runs the OCR processing, and contains image processing functions """
    """Manejo de captura de pantalla, preprocesamiento y OCR."""

    def get_screenshot(self, x, y, dx, dy):
        """Captura screenshot y devuelve PIL Image"""
        image = ImageGrab.grab(bbox=(int(x), int(y), int(dx), int(dy)))
        return image

    def get_grayscale(self, img):
        """Convierte imagen a escala de grises (acepta PIL o numpy)"""
        # Si es PIL Image, convertir a numpy primero
        if hasattr(img, 'mode'):
            img = numpy.array(img)
        return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    def remove_noise(self, img):
        """Elimina ruido de la imagen"""
        return cv2.medianBlur(img, 5)

    def thresholding(self, img):
        """Aplica threshold binario"""
        return cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    def ocr_core(self, img):
        """OCR SIMPLE - básico que funciona"""
        text = pytesseract.image_to_string(img, lang='eng', config='--psm 12 --oem 1')
        return text
    
    def ocr_time_specialized(self, img):
        """OCR SUPER especializado solo para tiempo con preprocesamiento agresivo
        
        Args:
            img: PIL.Image o numpy array
        
        Returns:
            str: Texto OCR extraído
        """
        # CRÍTICO: Convertir PIL Image a numpy array si es necesario
        if hasattr(img, 'mode'):  # Es PIL Image
            img = numpy.array(img)
        
        # Ahora img es definitivamente un numpy array
        
        # Convertir a grayscale si es necesario
        if len(img.shape) == 3:
            img = self.get_grayscale(img)
        
        # Aumentar tamaño 3x para mejor OCR
        scale = 300
        width = int(img.shape[1] * scale / 100)
        height = int(img.shape[0] * scale / 100)
        img = cv2.resize(img, (width, height), interpolation=cv2.INTER_CUBIC)
        
        # Threshold para mejor contraste
        img = self.thresholding(img)
        
        # Guardar para debug
        try:
            cv2.imwrite('../config/DEBUG_time_ocr.png', img)
        except:
            pass
        
        # Configuración MUY restrictiva para tiempo
        # Solo permitir: 0-9, h, m, s, espacio, :
        config = '--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789hms: '
        
        text = pytesseract.image_to_string(img, lang='eng', config=config)
        return text.strip()
    
# 4. TBFixOCR CLASE DE MODELADO DE DATOS Y LIMPIEZA OCR (Placeholders) ------------------------------------------------
# Estas clases se mantienen para modularidad, asumiendo que implementan la lógica de validación
# y carga de archivos CSV de forma robusta.
class TBFixOCR(object):
    """ This class will attempt to fix known 2-line OCR capture issues. 
        The format in the config file should be:
        CorrectValue, IncorrectFirstine, IncorrectSecondLine
    """
    
    def __init__(self, fix_ocr_file):

        self.fixed = {}
        self.fix_ocr = {}

        if fix_ocr_file:
            with open(fix_ocr_file) as fp:
                for cmt, fix_line in enumerate(fp):
                    fix_string = fix_line.strip( " \n")
                    if fix_string == "":
                        continue
                    kvp = fix_string.split(",")

                    self.fixed[kvp[1].lower()] = kvp[0]
                    self.fix_ocr[kvp[1].lower()] = kvp[2]
        else:
            print("### No OCR Fix configration file")

    def fix(self, line1, line2):
        if self.fix_ocr.get(line1.lower()) == None:
            return ""
        elif self.fix_ocr[line1.lower()] == line2:
            return self.fixed.get(line1.lower())
        else:
            return ""

# TBPlayer ------------------------------------------------------------------------------------------------------
class TBPlayer(object):
    """ This class parses PLAYER configuration parameters and validates player names captured by the OCR """

    def __init__(self, player_file, db=None):

        self.player_file = player_file
        self.player_set = set()
        self.player_kvp = {}
        self.player_set_changed = False
        self.db = db  # 🔧 AGREGAR ESTA LÍNEA
        
        if player_file:
            with open(player_file) as pfp:
                for cmt, player_line in enumerate(pfp):
                    kvp_string = player_line.strip()
                    kvp = kvp_string.split(",")

                    self.player_set.add(kvp[0])
                    self.player_kvp[kvp[0].lower()] = kvp[0]

                    for player_alias in kvp[1:]:
                        self.player_kvp[player_alias.lower()] = kvp[0]


    def save(self):

        if self.player_set_changed and self.player_file:

            while True:
                print("----------------- New Player! ------------------")
                print("### Do you want to save him to the player-list ?\n")
                save = input("### <Enter/y> or <n> ? ")
                if len(save) == 0 or save == "y" or save == "n":
                    break

            if len(save) == 0 or save == "y":
                with open( self.player_file,'w') as pfp:

                    sorted_players = sorted(self.player_set)
                    for player in sorted_players:
                        player_line = player

                        for alias in self.player_kvp:
                            if player == self.player_kvp[alias]:
                                player_line += "," + alias

                        player_line += "\n"
                        pfp.writelines(player_line)

                print("New Player has been saved to {}\n".format(self.player_file))

    def validate(self, player, line):
        
        # assume success...
        success = True
        
        # The player string should already be clean (just the player name)
        # from validate_capture() extraction
        player = player.strip()

        if player in self.player_set:
            # Player is already known and correct
            return True, player

        # Player not in known list - try to find a match
        
        # attempt a fuzzy match
        best_score = 0
        best_string = ""

        for tmp_player in self.player_set:
            tmp_score = SM(None, player, tmp_player).ratio()
            if tmp_score > best_score:
                best_string = tmp_player
                best_score = tmp_score

        if best_score > 0.75:
            print("\nFUZZY LOGIC: Player {}".format(player))
            print("MAPPED TO  : Player {}".format(best_string))
            return True, best_string  # Return matched player

        # look in alias map
        tmp_player = self.player_kvp.get(player.lower())

        if tmp_player is not None:
            # Found in alias map
            print("\nFUZZY LOGIC: Player {}".format(player))
            print("MAPPED TO  : Player {}".format(tmp_player))
            return True, tmp_player

        # Unknown player - ask user
        print("\n* ATTENTION: UNKNOWN OR NEW PLAYER")
        print("- Press <Enter> if player '{}' is correct".format(player))
        print("- Or type the correct 'Name/Alias' for the player") 
        print("- Or type '-' to abort the process!\n")
        player_name = input("<Enter> or ['Name/Alias'] or ['-']: ").strip()
            
        if player_name == "-":
            return False, player
        else:
            player_alias = player

            if len(player_name) > 0:
                player = player_name

            # 🔧 CRÍTICO: Guardar estado ANTES de modificar player_set
            is_new_player = player not in self.player_set
            
            if is_new_player:
                self.player_set_changed = True
                self.player_set.add(player)
            
            # 🔧 NUEVO: Insertar en BD inmediatamente si es jugador nuevo
            if is_new_player and self.db:
                try:
                    cursor = self.db.conn.cursor()
                    cursor.execute("""
                        INSERT OR IGNORE INTO players_ocr (name_player)
                        VALUES (?)
                    """, (player,))
                    self.db.conn.commit()
                    
                    # Verificar que se insertó
                    cursor.execute("""
                        SELECT id_player FROM players_ocr WHERE name_player = ?
                    """, (player,))
                    result = cursor.fetchone()
                    
                    if result:
                        print(f"### ✅ Player '{player}' added to database successfully (ID: {result[0]})")
                    else:
                        print(f"### ⚠️ WARNING: Player '{player}' was not inserted")
                        
                except Exception as e:
                    print(f"### ❌ ERROR: Could not add player to database: {e}")
                    import traceback
                    traceback.print_exc()

            if player_alias not in self.player_kvp:
                save_alias = "y"

                if player_alias != player:
                    while True:
                        save_alias = input("Is '{}' a good alias to save for {} (<Enter>/n, '-' to exit) ? ".format(player_alias, player)).strip()
                        if save_alias == "n" or save_alias == "-" or len(save_alias) == 0:
                            break

                if len(save_alias) == 0:
                    self.player_kvp[player_alias.lower()] = player
                    self.player_set_changed = True
                elif save_alias == "-":
                    return False, player

            return True, player

# TBChest ------------------------------------------------------------------------------------------------------
class TBChest(object):
    """ This class parses CHEST configuration parameters and validates chest names captured by the OCR """

    def __init__(self, quality_file):

        self.quality_kvp = {}

        if quality_file:
            with open(quality_file) as qfp:
                for cmt, quality_line in enumerate(qfp):
                    kvp_string = quality_line.rstrip('\n')
                    kvp = kvp_string.split(",")
                    for player_alias in kvp[1:]:
                        self.quality_kvp[player_alias] = kvp[0]


    def validate(self, chest):

        # fix lowercase issue that happens too often
        chest = chest.replace("orc ", "Orc ")
        #remove , which should never be in a chest name
        chest = chest.replace(",", "")
        #remove . which should never be in a chest name
        chest = chest.replace(".", "")
        #remove ; which should never be in a chest name
        chest = chest.replace(";", "")

        # add some processing to fix bad OCR scanning of chest names
        match = False
        for quality_line in self.quality_kvp:
            if chest.find(quality_line) > -1:
                if chest != self.quality_kvp[quality_line]:
                    print("Chest name match: {} =".format(chest))
                    print("{} triggered by {}".format(self.quality_kvp[quality_line],quality_line))
                chest = self.quality_kvp[quality_line]
                match = True
                break

        if not match:
            # More stuff to fix bad OCR captures
            if chest.startswith("lven"):
                chest = "E" + chest
            elif chest.startswith("ven"):
                chest = "El" + chest
            elif chest.startswith("ursed"):
                chest = "C" + chest
            elif chest.startswith("rsed"):
                chest = "Cu" + chest

            if chest.lower().endswith("ch"):
                chest += "est"
            elif chest.lower().endswith("che"):
                chest += "st"
            elif chest.lower().endswith("ches"):
                chest += "t"

            # fix lowercase issue that sometimes happen
            chest = chest.replace("chest", "Chest")

        return chest

# TBSource ------------------------------------------------------------------------------------------------------
class TBSource(object):
    """ This class validates chest SOURCE information captured by the OCR """
    
    def validate(self, source, line):
        """
        Improved validation that recognizes all common chest sources.
        Much more flexible and tolerant of OCR errors.
        """
        success = True
        
        # Normalize: remove "Source:" prefix if present
        source = source.strip()
        if source.lower().startswith("source"):
            source = source.split(":", 1)[-1].strip() if ":" in source else source[6:].strip()
        
        # List of known source types (case-insensitive check)
        source_lower = source.lower()
        
        # Check if it matches any known source category
        is_known_source = any(keyword in source_lower for keyword in [
            "crypt", "raid", "citadel", "bank", "wealth", "monster", 
            "tournament", "workshop", "store", "shop", "dungeon", 
            "arena", "treasure", "gift", "victory", "reward", "battle",
            "clash", "hermes", "jormungandr", "curse", "personal", "ancients", "squad"
        ])
        
        # If it's a known source type, just do minimal OCR corrections
        if is_known_source:
            source = self._fix_ocr_errors(source)
            return True, source
        
        # If it doesn't contain any known keyword, print warning but accept it
        print("\n*** WARNING: Unknown source type at line {}: '{}'".format(line, source))
        print("*** Attempting to process anyway...")
        
        source = self._fix_ocr_errors(source)
        return True, source
    
    # -----------------------------------------------
    def _fix_ocr_errors(self, source):
        """
        Fix common OCR mistakes in source names.
        Handles incomplete words and case issues.
        """
        
        # Fix incomplete "Crypt"
        if source.endswith("Cr"):
            source += "ypt"
        elif source.endswith("Cry"):
            source += "pt"
        elif source.endswith("Cryp"):
            source += "t"
        
        # Fix incomplete "Chest"
        if source.endswith("Ch"):
            source += "est"
        elif source.endswith("Che"):
            source += "st"
        elif source.endswith("Ches"):
            source += "t"
        
        # Fix incomplete "Wealth"
        if source.endswith("wea"):
            source += "lth"
        elif source.endswith("weal"):
            source += "th"
        elif source.endswith("wealt"):
            source += "h"
        
        # Fix incomplete "Monster"
        if source.endswith("Mons"):
            source += "ter"
        elif source.endswith("Monst"):
            source += "er"
        elif source.endswith("Monste"):
            source += "r"
        
        # Fix incomplete "Citadel"
        if source.endswith("Ci"):
            source += "tadel"
        elif source.endswith("Cit"):
            source += "adel"
        elif source.endswith("Cita"):
            source += "del"
        elif source.endswith("Citad"):
            source += "el"
        elif source.endswith("Citade"):
            source += "l"
        
        # Fix incomplete "Tournament"
        if source.endswith("tourna"):
            source += "ment"
        elif source.endswith("tournam"):
            source += "ent"
        elif source.endswith("tourname"):
            source += "nt"
        elif source.endswith("tournamen"):
            source += "t"
        
        # Fix incomplete "Bank"
        if source.endswith("Ba"):
            source += "nk"
        elif source.endswith("Ban"):
            source += "k"
        
        # Fix incomplete "Workshop"
        if source.endswith("Worksho"):
            source += "p"
        
        # Fix incomplete "Raid"
        if source.endswith("Rai"):
            source += "d"
        
        # Capitalize common keywords for consistency
        source = source.replace("crypt", "Crypt")
        source = source.replace("chest", "Chest")
        source = source.replace("citadel", "Citadel")
        source = source.replace("monster", "Monster")
        source = source.replace("bank", "Bank")
        source = source.replace("wealth", "Wealth")
        source = source.replace("tournament", "Tournament")
        source = source.replace("workshop", "Workshop")
        source = source.replace("raid", "Raid")
        
        return source

# ============================================================================
# TBTimeLeft CLASS - Extraction and Validation of "Time left" field
# ============================================================================
class TBTimeLeft:
    """
    Robust extractor + validator for "Time left" OCR strings.
    extract(line) -> (ok, hours, minutes, seconds, raw_text)
    validate(hours, minutes, seconds, line_number, batch_mode=False)
        -> (ok, corrected_hours, corrected_minutes, corrected_seconds, user_corrected_flag)
    """

    TIME_PATTERNS = [
        # 1. Full H M S pattern (e.g., 6h:55m:30s, 6h 55m 30s)
        re.compile(r'(?P<h>\d{1,3})\s*[hH]\s*[:\s]?\s*(?P<m>\d{1,2})\s*[mM]\s*[:\s]?\s*(?P<s>\d{1,2})\s*[sS]?', re.IGNORECASE),

        # 2. H + M (e.g., 6h:55m, 6h55m, 6h 55m)
        re.compile(r'(?P<h>\d{1,3})\s*[hH]\s*[:\s]?\s*(?P<m>\d{1,2})\s*[mM]?', re.IGNORECASE),

        # 3. M + S (e.g., 55m:30s, 55m30s)
        re.compile(r'(?P<m>\d{1,3})\s*[mM]\s*[:\s]?\s*(?P<s>\d{1,2})\s*[sS]?', re.IGNORECASE),

        # 4. Fallback genérico: 2-3 números separados
        re.compile(r'(?P<n1>\d{1,3})\D+(?P<n2>\d{1,2})(?:\D+(?P<n3>\d{1,2}))?'),

        # 5. Single number → asume minutos
        re.compile(r'^(?P<only>\d{1,3})$')
    ]

    def __init__(self, log_dir="working", batch_mode=False):
        self.max_hours = 19
        self.max_minutes = 59
        self.max_seconds = 59
        self.log_dir = log_dir
        self.batch_mode = batch_mode
        os.makedirs(self.log_dir, exist_ok=True)

        self.corrections_log = os.path.join(log_dir, "ocr_corrections.log")
        self.missing_log     = os.path.join(log_dir, "missing_timeleft.log")

    # -------------------------------------------------------
    def _log_correction(self, original, corrected, reason):
        try:
            with open(self.corrections_log, "a", encoding="utf-8") as f:
                f.write(
                    f"{datetime.utcnow().isoformat()} | ORIGINAL={original!r} | "
                    f"CORRECTED={corrected!r} | REASON={reason}\n"
                )
        except:
            pass

    def _log_missing(self, context):
        try:
            with open(self.missing_log, "a", encoding="utf-8") as f:
                f.write(f"{datetime.utcnow().isoformat()} | MISSING={context}\n")
        except:
            pass

    # -------------------------------------------------------
    def extract(self, line):
        """
        Extract hours/minutes/seconds from extremely messy OCR strings.
        ALWAYS RETURNS 5 VALUES → (ok, hours, minutes, seconds, raw_text)
        
        FIXED: Preserva dígitos adyacentes para evitar pérdida de información
        """

        raw_original = (line or "").strip()
        if not raw_original:
            print("*** WARNING: Time-left empty OCR line")
            self._log_missing("empty_time_line")
            return False, 0, 0, 0, "0 h : 0 m : 0 s"

        #print(f"### [DEBUG] Raw time OCR input: '{raw_original}'")
        
        # 1. Limpieza inicial: Remove prefix "Time left:"
        s = re.sub(r'(?i).*time\s*left[:\s]*', '', raw_original).strip()
        
        # 2. Normalizar caracteres Unicode raros
        s = s.replace('\u2212', '-').replace('\u2013', '-').replace('\u00A0', ' ')
        s = re.sub(r'[^\x00-\x7F]', ' ', s)
        
        # 3. CRÍTICO: NO eliminar caracteres entre dígitos todavía
        # Primero normalizar espacios alrededor de h/m/s
        s = re.sub(r'(\d+)\s*([hHmMsS])', r'\1\2 ', s)  # "7h24m" -> "7h 24m "
        
        # 4. Eliminar caracteres problemáticos EXCEPTO dígitos, h/m/s, espacios, dos puntos
        s = re.sub(r'[^0-9hHmMsS:\s]', ' ', s)
        
        # 5. Limpiar espacios múltiples
        s = re.sub(r'\s+', ' ', s).strip()

        #print(f"### [DEBUG] Cleaned time OCR: '{s}'")

        hours = minutes = seconds = 0
        matched = False

        # 6. Aplicar patrones de extracción en orden de especificidad
        for idx, pat in enumerate(self.TIME_PATTERNS):
            m = pat.search(s)
            if not m:
                continue

            matched = True
            groups = m.groupdict()
            #print(f"### [DEBUG] Pattern {idx+1} matched: {groups}")

            # Extracción de H, M, S basados en grupos nombrados
            if groups.get("h"):
                try: 
                    hours = int(re.sub(r'\D', '', groups['h']))
                except: 
                    hours = 0

            if groups.get("m"):
                try: 
                    minutes = int(re.sub(r'\D', '', groups['m']))
                except: 
                    minutes = 0

            if groups.get("s"):
                try: 
                    seconds = int(re.sub(r'\D', '', groups['s']))
                except: 
                    seconds = 0

            # Extracción de valores genéricos (n1, n2, n3)
            if groups.get("n1") and not groups.get("h"):
                vals = [v for v in (groups['n1'], groups['n2'], groups.get('n3')) if v]
                try:
                    if len(vals) == 3:
                        hours = int(vals[0])
                        minutes = int(vals[1])
                        seconds = int(vals[2])
                    elif len(vals) == 2:
                        hours = int(vals[0])
                        minutes = int(vals[1])
                    elif len(vals) == 1:
                        minutes = int(vals[0])
                except:
                    pass

            # Solo un número → asume minutos
            if groups.get("only"):
                try: 
                    minutes = int(groups["only"])
                except: 
                    minutes = 0

            raw_text = f"{hours} h : {minutes} m : {seconds} s"
            #print(f"### [OK] extract() parsed: {raw_text}")
            return True, hours, minutes, seconds, raw_text

        # 7. Fallback final: extraer todos los dígitos y asumir orden H M S o H M
        if not matched:
            digits = re.findall(r'\d+', s)
            print(f"### [DEBUG] Fallback digits found: {digits}")
            
            if len(digits) >= 2:
                hours   = int(digits[0])
                minutes = int(digits[1])
                seconds = int(digits[2]) if len(digits) >= 3 else 0
                print(f"### [FALLBACK] {hours} h : {minutes} m : {seconds} s")
                return True, hours, minutes, seconds, f"{hours} h : {minutes} m : {seconds} s"

            elif len(digits) == 1:
                minutes = int(digits[0])
                print(f"### [FALLBACK] 0 h : {minutes} m")
                return True, 0, minutes, 0, f"0 h : {minutes} m : 0 s"

        print("*** ERROR: Could not extract ANY time value")
        self._log_missing(raw_original)
        return False, 0, 0, 0, "0 h : 0 m : 0 s"

    # -------------------------------------------------------
    def validate(self, hours, minutes, seconds, line_number=0, batch_mode=None):
        """
        Validate & normalize time-left.
        ALWAYS RETURNS 5 VALUES: (ok, hours, minutes, seconds, user_corrected)
        """

        if batch_mode is None:
            batch_mode = self.batch_mode

        user_corrected = False

        # Convertir a enteros de forma segura
        try: h = int(hours)
        except: h = 0
        try: m = int(minutes)
        except: m = 0
        try: s = int(seconds)
        except: s = 0

        #print(f"### VALIDATING: raw = {h} h : {m} m : {s} s (line {line_number})")

        # Redondear segundos
        if s >= 30:
            print(f"*** INFO: seconds {s} >=30 → add 1 minute")
            m += 1
            s = 0

        # Normalizar overflow de minutos
        if m >= 60:
            print(f"*** INFO: normalizing minutes: {m} -> add hours")
            h += m // 60
            m = m % 60

        # Heurística OCR: 80-89 → restar 80
        if 80 <= h <= 89:
            orig = h
            h = h - 80
            print(f"*** INFO: hours {orig} -> {h} (OCR misread fix 80-89)")
            self._log_correction(f"{orig} h", f"{h} h", "80-89 heuristic")

        # Clamp a valores válidos
        if h < 0: h = 0
        if m < 0: m = 0
        if s < 0: s = 0

        # Validar rango de horas sospechoso (>= 20)
        if h >= 20:
            print(f"\n*** WARNING: Suspicious time detected at line {line_number}")
            print(f"*** CAPTURED: {h} h : {m} m")
            print("*** Valid range: 0–19 hours")
            print("*** If correct press [Y], or [N] to reject,")
            print("*** or enter manual correction e.g. '7 24' for 7h24m\n")

            if batch_mode:
                print("*** Batch-mode active → rejecting automatically")
                return False, 0, 0, 0, False

            while True:
                user = input("Confirm [Y/N] or manual (H M): ").strip()
                if user.upper() == "Y":
                    return True, h, m, s, False
                if user.upper() == "N":
                    return False, 0, 0, 0, False

                # Intentar parsear entrada manual
                mm = re.findall(r'\d+', user)
                if len(mm) >= 1:
                    try:
                        nh = int(mm[0])
                        nm = int(mm[1]) if len(mm) > 1 else 0
                        if 0 <= nh <= self.max_hours and 0 <= nm <= self.max_minutes:
                            print(f"*** Manual correction accepted: {nh} h : {nm} m")
                            return True, nh, nm, 0, True
                        else:
                            print(f"*** Manual values out of valid range 0–{self.max_hours}h / 0–{self.max_minutes}m")
                            continue
                    except:
                        print("*** Invalid manual input")
                        continue
                else:
                    print("*** Invalid format. Please enter: H M (e.g., 7 24)")
                    continue

        # Validación final de rangos normales (0-19 hours)
        if 0 <= h <= self.max_hours and 0 <= m <= self.max_minutes:
            #print(f"### VALIDATED OK: {h} h : {m} m : {s} s")
            return True, h, m, s, user_corrected

        # Si llega aquí, está fuera de rango
        print(f"*** ERROR: Time-left out of valid range: {h}h {m}m")
        self._log_correction(f"{h} h : {m} m", "0 h : 0 m", "out_of_range")
        return False, 0, 0, 0, False

# TBScore ------------------------------------------------------------------------------------------------------
class TBScore(object):
    """ This class contains and calculates chest scores """
# ------------------------------------------------------------------------------------------------------    
    def __init__(self, score_file):

        self.convert_chest_to_source = {"bank","ban","ba","clash for the throne tournament"}

        self.score_kvp = {}
        self.no_score = set()

        if score_file:
            with open(score_file) as sfp:
                for cmt, score_line in enumerate(sfp):
                    kvp_string = score_line.strip()
                    kvp = kvp_string.split(",")
                    self.score_kvp[kvp[0].lower()] = kvp[1]
# ------------------------------------------------------------------------------------------------------
    def calculate(self, source, chest, player, line):
        
        if source.lower() in self.convert_chest_to_source:
            switch_chest_and_source = True
            tmp_source = source.lower()
            source = chest
            if tmp_source.find("throne") > -1:
                chest = "Clash for the Throne tournament"
            else:
                chest = 'Bank'

        score = "0"

        if chest == "Cursed Citadel Chest":
            split_source = source.split(" ")
            citadel_level = split_source[1]
            source = "Level " + citadel_level + " cursed Citadel"

        temp_score = self.score_kvp.get(source.lower())
                    
        if temp_score != None:                    
            score = temp_score
        else:
            print("*** Warning at line {}: No score for {}, {}, {}".format( line, player, source, chest ))
            self.no_score.add(source)

        return score
# ------------------------------------------------------------------------------------------------------
    def print_no_scores(self):
        if len(self.no_score) > 0:
            print("\n*** Warning: The following chest types have no score assigned:")
            for chest in self.no_score:
                print(chest)

# TBCalibration ------------------------------------------------------------------------------------------------------
class TBCalibration(object):
    """ This class handles the setup of the parameters needed to capture the correct screen image and where to click the mouse """
# ------------------------------------------------------------------------------------------------------    
    def __init__(self):
        self.screen = TBScreen()

# ------------------------------------------------------------------------------------------------------
    def run(self, config):
        print( "### SCREEN CAPTURE AND MOUSE CLICK CALIBRATION MODE ###")
        print( "\n>> There are 2 Options for the calibration. Option <1>")
        print( ">> to capture 'start text' position x1,y1 and to capture")
        print( ">> 'end text' position x2,y2 // Option <2> to capture the")
        print( ">> position for the OPEN Button.\n")
        print( "++ See the example-image to find text-field-position at: ")
        print( "++ /config/TBCorrect_Screenshot_Example.jpg")
        print( "\n>> If you have the text-field-positions, you must start")
        print( ">> the Option <2> to find the coordinates for the")
        print( ">> [OPEN] Button to collect the chests.\n")
        print( ">> You can also use the program MEAZURE400x64. You can")
        print( ">> find them into the folder _INSTALL => Install and")
        print( ">> install & start the Program. It is really helpful!")
        
        while True:
            
            choice = ""
            while True:                
                print("\n>> Capture-Mode1: Find text-field position <1>")
                print(">> Capture-Mode2: Find OPEN-Button position <2>\n")
                choice = input("** <1> or <2> or <Enter,-,x> to stop calibration) ? ")
                if len(choice) == 0 or choice == "1" or choice == "2" or choice == "-" or choice == "x":
                    break

            if len(choice) == 0 or choice == "-" or choice == "x": # stop
                break
            elif choice == "1":
                
                while True:
                    
                    print( "\n\n#########################################")
                    print( "### CALIBRATE CAPTURE RECTANGLE X1,Y1 ###")
                    print( "#########################################\n")
                    print( ">> Only Position the mouse at the UPPER LEFT corner to")
                    print( ">> capture the first chest-text and than press <Enter>\n")
                    pyautogui.moveTo(int(config.x1), int(config.y1))
                    input("** If you are ready, press <Enter>")
                    lx, uy = pyautogui.position()
                    print(">> Recorded position x:{}, y:{}".format(lx, uy))
                    
                    print( "\n\n#########################################")
                    print( "### CALIBRATE CAPTURE RECTANGLE X2,Y2 ###")
                    print( "#########################################\n")
                    print( ">> Only Position the mouse at the LOWER RIGHT corner to")
                    print( ">> capture the last chest-text and than press <Enter>")
                    print( ">> IMPORTANT! Remember, that there are long texts, so")
                    print( ">> scroll far to the right to capture the text.\n")
                    pyautogui.moveTo(int(config.x2), int(config.y2))
                    input("** If you are ready, press <Enter>")
                    rx, ly = pyautogui.position()
                    print(">> Recorded position x:{}, y:{}".format(rx, ly))

                    x1 = lx
                    y1 = uy
                    x2 = rx
                    y2 = ly

                    image = self.screen.get_screenshot(x1, y1, x2, y2)
                    image.save('../config/TBCalibration_Screenshot.png')
                    image = self.screen.get_grayscale(numpy.array(image))
                    capture = self.screen.ocr_core(image)
                    
                    print("\n\n===============================================")
                    print(">> Check Captured data with your xy-positions:")
        
                    raw_rows = capture.split("\n")
                    rows = list()
                    # remove empty rows
                    for row in raw_rows:
                        if len(row.strip()) == 0:
                            continue
                        rows.append(row)
                    for row in rows:
                        print(">> {}".format(row))
                    
                    print("===============================================")
                    print(">> Go to the folder config/ and Check your   <<")
                    print(">> saved TBCalibration_Screenshot.png with   <<")
                    print(">> the TBCorrect_Screenshot_Example.png      <<")
                    print("===============================================")
                    
                    while True:
                        print("### Are you happy with the result & coordinates?\n")
                        proceed = input("** <Enter> or <n> ? ")
                        if proceed == "n" or len(proceed) == 0:
                            break

                    if proceed != "n":
                        break
                print("\n>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<")
                print(">> Add the coordinates to the configuration file.")
                print(">> Open the file: Chest-Counter/config/config.csv")
                print(">> x1   = {}".format(x1))
                print(">> y1   = {}".format(y1))
                print(">> x2   = {}".format(x2))
                print(">> y2   = {}".format(y2))
                print(">>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<\n")

            elif choice == "2": # mouse position calibration for auto clicks

                while True:

                    print( "\n############################################")
                    print( "### CALIBRATE MOUSE CLICK POSITION MX,MY ###")
                    print( "############################################\n")
                    print( ">> Move the mouse over the OPEN Button and")
                    print( ">> press <Enter> to get the Button-coordinates.\n")
                    pyautogui.moveTo(int(config.mx), int(config.my))
                    input("** If you are ready, press <Enter>")
                    lx, ly = pyautogui.position()
                    print(">> Recorded position mx:{}, my:{}".format(lx, ly))

                    mx = lx
                    my = ly

                    print("\n### Press <Enter> to perform a test click or")
                    print("### type any other character and <Enter> to abort")
                    print("### ATTENTION! The test-click opens the chest!\n")
                    click = input("** <Enter> for test click or <other key> ? ")

                    if len(click) == 0:
                        hwndThis = pygetwindow.getActiveWindow()
                        pyautogui.click(x=int(mx), y=int(my))
                        hwndThis.activate()

                    while True:
                        print("\n##################################")
                        print("### Are you happy with the result?")
                        print("##################################\n")
                        proceed = input("** <Enter> or <n> ? ")
                        if proceed == "n" or len(proceed) == 0:
                            break

                    if proceed != "n":
                        break
                
                print("\n>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<")
                print(">> Add the coordinates to the configuration file.")
                print(">> Open the file: Chest-Counter/config/config.cfg")
                print(">> mx       = {}".format(mx))
                print(">> my       = {}".format(my))
                print(">>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<\n\n\n")

# TBCapture ------------------------------------------------------------------------------------------------------
class TBCapture(object):
    """ main class used for capturing chest information from the TB Gift screen """
# ------------------------------------------------------------------------------------------------------
    def __init__(self, config, args):

        self.processing_datetime    = datetime.now().strftime("%Y-%m-%d %H.%M.%S")
        self.debug_mode             = args.verbose
        self.clickWait              = args.clickWait
        self.config                 = config
        
        self.db = None  # Inicializar variable
        self.db_integration = None  

        #self.player_def             = TBPlayer(config.player_file)
        self.chest_def              = TBChest(config.quality_file)
        self.source_def             = TBSource()
        self.screen                 = TBScreen()
        self.fix_ocr_def            = TBFixOCR(config.fix_ocr_file)
        self.time_left_def          = TBTimeLeft()
        

        
        workfile = config.working_dir + '/TB_Capture_Clean'
        if len(config.clan) > 0:
            workfile += '_' + config.clan
        workfile += '_' + self.processing_datetime
        workfile += '.txt'

        capturefile = config.working_dir + '/TB_Capture_RAW'
        if len(config.clan) > 0:
            capturefile += '_' + config.clan
        capturefile += '_' + self.processing_datetime
        capturefile += '.txt'
        
        # Conectar con base de datos
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_root, "data", "db", "tb_chests.db")
            self.db = TBDatabase(db_path)
            
            # Cargar datos de configuración en la BD
            config_players = os.path.join(project_root, "config", "players.csv")
            config_members = os.path.join(project_root, "config", "clan_members.csv")
            config_scores = os.path.join(project_root, "config", "scores-hlo.csv")
            
            self.db.load_config_data(config_players, config_members, config_scores)
            
            # Inicializar integración
            self.db_integration = TBDatabaseIntegration(
                self.db,
                clan_name=config.clan,
                id_user=None,  # O pasar usuario si está disponible
                verbose=args.verbose
            )
        except Exception as e:
            print(f"[WARNING] No se pudo conectar con la BD: {e}")
            self.db = None
            self.db_integration = None

        # 🔧 NUEVO: Crear TBPlayer DESPUÉS de tener self.db
        self.player_def = TBPlayer(config.player_file, db=self.db)
        
        self.wfile = open(workfile, 'w')
        self.sfile = open(config.datafile,'a')
        self.tfile = open(config.totalfile,'a')
        self.cfile = open(capturefile, 'w')

        self.records = list()
        self.maxClicks   = 0
        self.totalClicks = 0

    # ============================================================================
    # FIXED: validate_capture() and save_records() methods for TBCapture class
    # Issue 1: Now supports seconds in time validation
    # Issue 2: Fixed "No more chests to capture!" appearing prematurely
    # ============================================================================
    def validate_capture(self, capture, count):
        """
        Validate merged capture (main + time region)
        Fully compatible with new TBTimeLeft (hours + minutes + seconds)
        """

        import re

        success = True
        self.records = []

        # Log raw capture
        self.cfile.write(
            "--------------- {} --------------------------\n".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        self.cfile.write(capture + "\n")
        self.cfile.flush()

        print("\n***************** CAPTURED TEXT (merged chest+time): ******************")
        print(capture)
        print("*********************************************************************\n")

        # Normalize input
        # Esto convierte la captura de doble zona (separada por \n) en una lista de líneas.
        lines = [x.strip() for x in capture.split("\n") if x.strip()]
        if not lines:
            print("### No chests found (OCR empty).")
            return False

        chest = None
        player = None
        source = None
        time_left = None

        records_found = 0
        total = len(lines)
        i = 0

        # Cambiamos la lógica del while para asegurar que todos los campos se procesen
        # antes de reiniciar (Finalize chest).
        while i < total and records_found < count:

            text = lines[i]

            # 1) Chest name
            # Debe ser la primera línea que no contenga ninguna palabra clave conocida.
            if (
                chest is None and
                "From" not in text and
                "Source" not in text and
                "Time" not in text
            ):
                chest = text
                # No usamos 'continue'. Simplemente pasamos a la siguiente línea.
                # print(f"[DEBUG] Found Chest: {chest}")

            # 2) From
            elif "From" in text and player is None:
                m = re.search(r"From\s*:?\s*(.+)", text)
                if m:
                    player = m.group(1).strip()
                # print(f"[DEBUG] Found Player: {player}")

            # 3) Source
            elif "Source" in text and source is None:
                m = re.search(r"Source\s*:?\s*(.+)", text)
                if m:
                    source = m.group(1).strip()
                # print(f"[DEBUG] Found Source: {source}")

            # 4) Time (El más complejo, lo dejamos al final de la detección)
            # Se asume que Time left está en la última línea capturada.
            elif time_left is None:
                # Detecta tiempo incluso si NO contiene "Time left:"
                lower = text.lower().strip()
                raw_candidate = None

                # PATRONES que seguro NO son tiempo
                not_time_keywords = ("source", "from", "chest")
                
                # CASO A → Línea contiene "Time left"
                if "time left" in lower:
                    m = re.search(r"time\s*left\s*:?\s*(.+)", text, re.IGNORECASE)
                    raw_candidate = m.group(1).strip() if m else text

                # CASO B → No contiene "Time left", pero la línea PARECE un tiempo válido
                elif not any(k in lower for k in not_time_keywords):
                    # debe contener al menos un dígito
                    if re.search(r"\d", lower):
                        # patrón típico h,m,s en cualquier forma
                        if re.search(r"[hmHsS]", lower) or re.search(r"\d+\s*[:]\s*\d+", lower):
                            raw_candidate = text.strip()

                # Si se detectó un candidato de tiempo, lo procesamos
                if raw_candidate is not None:
                    #print(f"\n### RAW TIME STRING DETECTED: '{raw_candidate}'")
                    #print(f"### [DEBUG] Raw time OCR before cleaning: '{raw_candidate}'")

                    ok_ex, h, mnt, sec, raw_time = self.time_left_def.extract(raw_candidate)

                    #print(f"### [DEBUG] Cleaned time OCR: '{raw_time}'")

                    if not ok_ex:
                        print(f"### [FALLBACK] 0 h : 0 m")
                        time_left = "0 h : 0 m"
                    else:
                        # VALIDACIÓN
                        #print(f"### VALIDATING: raw = {h} h : {mnt} m : {sec} s (line {i})")
                        #ok_v, hcorr, mcorr, usercorr = self.time_left_def.validate(h, mnt, sec, i)
                        ok_v, hcorr, mcorr, scorr, usercorr = self.time_left_def.validate(h, mnt, sec, i)

                        if ok_v:
                            #print(f"### VALIDATED OK: {hcorr} h : {mcorr} m")
                            # El tiempo se almacena en el formato final
                            time_left = f"{hcorr} h : {mcorr} m"
                        else:
                            print(f"### VALIDATION FAILED → using 0 h : 0 m")
                            time_left = "0 h : 0 m"

                    #print(f"### NORMALIZED TIME → '{time_left}'")
                # else: no era tiempo, avanzamos 'i'

            # ============================================================
            # Finalize chest: CHECKPOINT CRÍTICO
            # Solo finaliza el registro si tiene todos los 4 campos y reinicia
            # ============================================================
            if chest and player and source and time_left:

                try:
                    pres = self.player_def.validate(player, i)
                    final_player = player if pres is None else pres[1]
                except:
                    final_player = player

                try:
                    sres = self.source_def.validate(source, i)
                    final_source = source if sres is None else sres[1]
                except:
                    final_source = source

                self.records.append([chest, final_player, time_left, final_source])
                records_found += 1

                # Reiniciar para buscar el siguiente (aunque solo busquemos 1)
                chest = None
                player = None
                source = None
                time_left = None
                
                # Usamos 'continue' aquí para saltar 'i += 1' y seguir con el ciclo
                # En la práctica, con un solo cofre, el 'while' terminará en la siguiente iteración.
                # continue # Descomentar si se buscan multiples cofres y se quiere reiniciar el ciclo sin incrementar 'i'
            
            # Siempre incrementamos 'i' para avanzar a la siguiente línea.
            # Si se usó 'continue' arriba, esta línea se salta, pero como es un solo cofre
            # y solo hay 4 líneas, da igual. Lo importante es que no se salte 'Source' por error.
            i += 1
            
        # Last record (Fallback para asegurar que el último registro incompleto se procese)
        # Ya no es estrictamente necesario debido al 'if' dentro del bucle, pero lo mantenemos.
        if (
            records_found < count and
            chest and player and source and time_left
        ):
            # NOTA: La validación de player/source se realizó arriba, pero la repetimos
            # si la detección ocurrió fuera del finalizador del ciclo.
            try:
                pres = self.player_def.validate(player, i)
                final_player = player if pres is None else pres[1]
            except:
                final_player = player

            try:
                sres = self.source_def.validate(source, i)
                final_source = source if sres is None else sres[1]
            except:
                final_source = source
                
            self.records.append([chest, final_player, time_left, final_source])
            records_found += 1

        # If no records found (el manejo de errores al final es correcto)
        if records_found == 0:
            print("### No chests found!")
            print("\n*** ERROR: The language is English?")
            print("*** ERROR: Check captured text\n")

            while True:
                print(">>> [1] Capture again [2] Save It anyway")
                print(">>> [3] Stop Process  [4] Show Captured text")

                ans = input("\n*** [1] - [2] - [3] or [4] ? ").strip()

                if ans == "4":
                    print("\n\n************ RAW OCR TEXT ************")
                    print(capture)
                    print("****************************************\n")
                    continue

                if ans in ("1","2","3"):
                    self.user_choice = ans
                    break

            if ans == "3":
                return False
            if ans == "2":
                return True
            if ans == "1":
                return False

        return True
        
    def save_records(self):
        """Save records to output files with 4-field format (including seconds in time)"""
        
        index = 0
        rows = list()

        while index < len(self.records):
            chest = self.records[index][0]
            player = "From : " + self.records[index][1]
            time_left = "Time left : " + self.records[index][2]  # Now includes seconds
            source = "Source : " + self.records[index][3]

            print("\n-------------------------------------------------------")
            print("{}".format(chest))
            print("{}".format(player))
            print("{}".format(time_left))  # Will show "X h : Y m : Z s"
            print("{}".format(source))
            print("-------------------------------------------------------")

            rows.append(chest)
            rows.append(player)
            rows.append(time_left)
            rows.append(source)
            index += 1

        for row in rows:
            self.sfile.writelines(row+"\n")
            self.tfile.writelines(row+"\n")
            self.wfile.writelines(row+"\n")

        self.sfile.flush()
        self.tfile.flush()
        self.wfile.flush()
        
        # Sincronizar con base de datos si está disponible
        if self.db_integration and len(self.records) > 0:
            self.db_integration.sync_records(self.records)

        print("Records saved...\n")
    # ---------------------------------------------------------------------------------------------------------------
    def run(self):

        value = ""
        while True:
            
            value = input("\nTotal Chests to collect? ('-' exit): ")
            
            if value.isdigit() or value == "-":
                break

        if value == "-":
            exit(0)

        maxClicks = int(value)

        while True:
            print("\n\n>>>>> OCR processing {}/{}....".format(self.totalClicks+1, maxClicks))
            # CAPTURA 1: Información principal (Chest, From, Source)
            image_main = self.screen.get_screenshot(self.config.x1, self.config.y1, 
                                                    self.config.x2, self.config.y2)
            image_main = self.screen.get_grayscale(numpy.array(image_main))
            capture_main = self.screen.ocr_core(image_main)
            
            # CAPTURA 2: Time Left (área específica)
            image_time = self.screen.get_screenshot(self.config.time_x1, self.config.time_y1,
                                                    self.config.time_x2, self.config.time_y2)
            # ANTES:
            #capture_time = self.screen.ocr_core(image_time)

            # DESPUÉS:
            capture_time = self.screen.ocr_time_specialized(image_time)
            
            # MERGE BOTH CAPTURES
            capture = capture_main + "\n" + capture_time
            
            # print(f"\n### TIME CAPTURE: '{capture_time}'") # Desactivado:
            count = 4 # chests on the screen

            # make sure we don't capture more than the specified number of chests
            if self.totalClicks + count > maxClicks:
                count = maxClicks - self.totalClicks

            success = self.validate_capture(capture, count)
            
            if len(self.records) < count and len(self.records) > 0: # did we capture less than the specified number?
                nofunc = maxClicks +1

            if success and len(self.records) == 0: # success but nothing was captured so stop
                print("\n*** {} from {} Chests saved. Process cancelled.\n".format(self.totalClicks, maxClicks))
                break

            proceed = ""

            if not success:
                while True:
                    print("*** ERROR: The language is English?")
                    print("*** ERROR: Check captured text\n")
                    print(">>> [1] Capture again [2] Save It anyway")
                    print(">>> [3] Stop Process  [4] Show Captured text")
                    
                    proceed = input("\n*** [1] - [2] - [3] or [4] ? ")
            
                    if proceed == "4":
                        print("\n\n************ CAPTURED TEXT ************")
                        print(capture)
                        print("***************************************\n")

                    if proceed in ["1", "2", "3"]:
                        break

            if proceed == "3":
                break
            elif proceed == "1":
                self.cfile.writelines("--- WARNING: The user has asked to redo the capture so watch for duplicates.\n")
                self.cfile.flush()

            if success or proceed == "2":
                self.save_records()

            if success:

                clicks = len(self.records) # dont click more than the number of chests captured by the OCR

                if self.totalClicks + clicks > maxClicks:
                    clicks = maxClicks - self.totalClicks
        
                moveX = [0,3,-6,6,-3,0]
                hwndThis = pygetwindow.getActiveWindow()

    ###          mitigation when using Firefox as the first click does not alway take
    #            pyautogui.click(x=int(self.config.mx)-150, y=int(my)) # a fast first click to set focus on the game screen
    #            time.sleep(int(clickWait) / 2000.0)
    #            pyautogui.moveTo(x=int(self.config.mx), y=int(my))
    #            time.sleep(int(clickWait) / 2000.0)
    ###          mitigation when using Firefox as the first click does not alway take

                for i in range(clicks):
                    pyautogui.click(x=int(self.config.mx)+moveX[i], y=int(self.config.my)) # move the cursor slighty to avoid the game screensaver
                    self.totalClicks += 1
                    time.sleep(int(self.clickWait) / 2000.0)
                hwndThis.activate()
                time.sleep( 2 * int(self.clickWait) / 2000.0 )

            if self.totalClicks >= maxClicks:
                print("\n================================")
                print("{} Chests total collected.".format(self.totalClicks))
                print("================================\n\n\n")
                break

        self.player_def.save()
        # Cerrar conexión con BD
        if self.db:
            self.db.close()
                
        if not success:
            print("\n****************************************")
            print("** THERE ARE ERRORS IN THE PROCESSING **")
            print("****************************************")


# TBProcess ------------------------------------------------------------------------------------------------------
class TBProcess(object):
    """ main class used for generating EOD files and summaries for all chests as well as citadels """
# ------------------------------------------------------------------------------------------------------
    def __init__(self, config, args):

        self.processing_date        = datetime.now().strftime("%Y-%m-%d")
        self.debug_mode             = args.verbose
        self.config                 = config
        self.skip_empty             = False
        self.eod                    = True
        self.summary                = True
        self.citadels               = False
        self.start_date             = ''
        self.end_date               = ''
        self.score_def              = TBScore(config.score_file)
        global odc
        odc = 0

        if args.skip_empty:
            self.skip_empty = args.skip_empty
        if args.date:
            self.processing_date = args.date
        if args.eod:
            self.eod = args.eod
        if args.summary:
            self.summary = args.summary
        if args.citadels:
            self.citadels = args.citadels
        if args.start_date:
            self.start_date = args.start_date
            odc = 1
            print("*** Start-Date! {}".format(odc))
            
        if args.end_date:
            self.end_date = args.end_date
            odc = 1
            print("*** End-Date! {}".format(odc))
            
        self.player_summary = {}
        self.citadel_summary = {}

        if config.player_file:
            with open(config.player_file) as pfp:
            # ---> SE HA AÑADIDO 'encoding='latin-1'' AQUÍ <--- YOZAHM
            #with open(config.player_file, encoding='latin-1') as pfp:
                for cmt, player_line in enumerate(pfp):
                    kvp_string = player_line.strip()
                    kvp = kvp_string.split(",")

                    self.player_summary[kvp[0]] = [0, 0]
                    self.citadel_summary[kvp[0]] = [0, 0, 0, 0, 0, 0, 0, 0]


# ------------------------------------------------------------------------------------------------------
    def process_file(self, inputfile, processing_date):

# ------------------------ Find Epic Chests, which is not in Source, but in Line 1 --------------------------------------------

        datafile  = self.config.datafile
        totalfile = self.config.totalfile

        # Line1 is the epic chestname, but in line 3 is the same name than other normal chests, so find the
        # epic chests in line 1 + normal chests in line 3, if line1+3 = True than rename the normal chest
        # in line 3 to a epic chest, to calculate points.

        word1 = "Jack Reaper Chest"         #line1
        word2 = "Pumpkin"                   #line3
        nword2 = "Epic Jack Reaper Chest"   #new line3

        # Read datafile
        if os.path.exists(datafile):
            with open(datafile, 'r') as f:
                lines = f.readlines()
            i = 0
            while i < len(lines) - 3: 
                if word1 in lines[i] and word2 in lines[i+3]:
                    lines[i+3] = lines[i+3].replace(word2, nword2)
                i += 3
            # Save the datafile back
            with open(datafile, 'w') as f:
                f.writelines(lines)
        else:
            none=True

        # same fix for total-datas!
        if os.path.exists(totalfile):
            with open(totalfile, 'r') as f:
                lines = f.readlines()
            i = 0
            while i < len(lines) - 3: 
                if word1 in lines[i] and word2 in lines[i+3]:
                    lines[i+3] = lines[i+3].replace(word2, nword2)
                i += 3
            # Save the totalfile back
            with open(totalfile, 'w') as f:
                f.writelines(lines)
        else:
            none=True

# ------------------------ Find and Replace Bad Wordphrases ------------------------------------------------

        filepath = self.config.datafile
        fixwords = self.config.fixwords
        checkfile = Path(filepath)

        with open(fixwords, 'r') as f:
            head_a = f.readline()
            count_all = 0
            count = 0
            
            while True:
            
                word1 = f.readline()
                word2 = f.readline()

                # datafile missing or OneDayCapture is active than break
                if not checkfile.is_file() or odc == 1:
                    break

                # Break, if the first Line is empty (End of Datas)
                if not word1:
                    print("\n")
                    print(">>-----------    Find and Replace    --------------<<")
                    print(">> Bad Wordphrases replaced : {} times \n\n".format(count_all))
                    break
            
                # If badword and goodword in the database:
                if word1 and word2:
                    # Activate print to check bad-wordphrase + good wordphrase
                    #print(f"Line 1 Bad : {word1.strip()}")
                    #print(f"Line 2 Good: {word2.strip()}")
                    
                    # Load Captured Datas
                    with open(filepath, 'r') as file:
                        filedata = file.read()
                        # Count wrong word-phrase
                        count = filedata.count(word1)
                        count_all = count_all+count
                        # replace the old word-phrase with the new word-phrase
                        filedata = filedata.replace(word1, word2)
                        # write the modified data back to the file
                        with open(filepath, 'w') as file:
                            file.write(filedata)

                # Break, if the second line is empty, but not the first
                if not word2 and word1:
                    print(">>-----------    Find and Replace    --------------<<")
                    print(">> Line 2 is empty: Bad Database                   <<")
                    print(">>-------------------------------------------------<<\n\n")
                    break
            
                # Prüfen Sie die dritte gelesene Zeile auf Leerheit (die 3. Zeile ist die nächste Zeile nach dem Paar)
                if not word2.strip():
                    break

            success = True
                
# ---------------------- Find and Replace Olympic & Ragna  -------------------------------------------
        while True:    
            filepath = self.config.datafile
            checkfile = Path(filepath)

            # Datafile is present and no OneDayCapture than run this code
            if checkfile.is_file() and odc == 0:
                # Olympus or Ragna y/n
                print("\n----------------------------------------------------")
                print(">>> Olympus and Ragnarok Chests:")
                print(">>> PLAYERS SHOULD PICK UP THE CHESTS AT THE EVENT!")
                print(">>> Olympic & Ragna Chests should count? [Y or Yes]")
                print(">>> Olympic & Ragna Chest no counting? [N or No]\n")
                print(">>> The chests get renamed to Bad Hermes and")
                print(">>> Bad Jormungandr with 0 points with your score.\n")
                print(">>> The changes are only updated to the current")
                print(">>> capture-file into the data-folder!")
                print("----------------------------------------------------\n")
        
                choice = input("### Event Olympus or Ragnarok now running? [y/n]: ")
                if choice.lower() == "n" or choice.lower() == "no":

                    # Find Source old and rename with new
                    old_text1 = "Hermes' Store"
                    new_text1 = "Bad Hermes"
                    old_text2 = "Jormungandr Shop"
                    new_text2 = "Bad Jormungandr"

                    # open the file
                    with open(filepath, 'r') as file:
                        filedata = file.read()

                    # count the old_text
                    count_text1 = filedata.count(old_text1)
                    count_text2 = filedata.count(old_text2)

                    # replace the old text with the new text
                    filedata = filedata.replace(old_text1, new_text1)
                    filedata = filedata.replace(old_text2, new_text2)

                    print("\n")
                    print("================   Find and Replace    ================")
                    print(">>> Original Chest  : {} ".format( old_text1))
                    print(">>> Renamed Chest   : {} ".format( new_text1))
                    print(">>> Found & Renamed : {} times ".format( count_text1))
                    print("-------------------------------------------------------")
                    print(">>> Original Chest  : {} ".format( old_text2))
                    print(">>> Renamed Chest   : {} ".format( new_text2))
                    print(">>> Found & Renamed : {} times ".format( count_text2))
                    print("=======================================================\n")
                    

                    # write the modified data back to the file
                    with open(filepath, 'w') as file:
                        file.write(filedata)
                        break
                elif choice.lower() == "y" or choice.lower() == "Yes":
                    print("\n>> Event Olympus or Ragnarok running!")
                    print(">> All Olympus & Ragna Chests count now! \n")
                    break
                else:
                    print("\n>> Wrong Input, Try again!")
            else:
                break

        succes = True


# ---------------------- Write Summarys -------------------------------------------
        
        with open(inputfile) as fp:

            file_dir = self.config.final_dir

            ofile = file_dir + '/' + processing_date
            ofile += '_TB_Chests'
            ofile += '_' +self.config.clan
            ofile += '_' + "FINAL"
            ofile += '.txt'

            opf = open(ofile, 'w')
            opf.writelines('DATE,PLAYER,SOURCE,CHEST,SCORE,CLAN\n')

            source_line_count = 0
            parsed_line_count = 0

            while True:

                try:
                    chest = player = time_left = source = ""

                    # FIXED: Read chest name (line 1)
                    line = fp.readline()
                    if not line:
                        break
                    chest = line.strip()
                    source_line_count += 1

                    # FIXED: Read player (line 2)
                    line = fp.readline()
                    if not line:
                        break
                    splitter = ":"
                    player = line.strip()
                    split_player = player.split(splitter, 1)
                    player = split_player[1].strip()
                    source_line_count += 1

                    # FIXED: Read time_left (line 3) - NEW LINE!
                    line = fp.readline()
                    if not line:
                        break
                    time_left = line.strip()
                    split_time = time_left.split(splitter, 1)
                    time_left = split_time[1].strip() if len(split_time) > 1 else time_left
                    source_line_count += 1

                    # FIXED: Read source (line 4)
                    line = fp.readline()
                    if not line:
                        break
                    source = line.strip()
                    split_source = source.split(splitter, 1)
                    source = split_source[1].strip()
                    source_line_count += 1

                    if len(chest) > 0 and len(player) > 0 and len(source) > 0:
                        score = self.score_def.calculate( source, chest, player, source_line_count)

                        parsed_line_count += 1

                        if self.debug_mode:
                            print("Processing ({}/{}): {},{},{},{},{},{}".format( 
                                parsed_line_count, source_line_count, 
                                processing_date, player, source, chest, score, self.config.clan))

                        opf.writelines(processing_date+','+player+','+source+','+chest+','+score+','+self.config.clan+'\n')
                    else:
                        print("*** ERROR: Failed to parse chest ({}/{}): {}, From: {}, Source: {}".format( 
                            parsed_line_count, source_line_count, chest, player, source))
                        success = False
                        break
                except:
                        print("*** EXCEPTION: Chest ({}/{}): {}, From: {}, Time: {}, Source: {}".format( 
                            parsed_line_count, source_line_count, chest, player, time_left, source))
                        success = False
                        break
            
            opf.close()

        # FIXED: Now dividing by 4 (was 3 before)
        if parsed_line_count != source_line_count / 4:
            print("*** ERROR Mismatch between processed line count and source line count: {} != {} / 4".format(
                parsed_line_count, source_line_count))
            success = False

        print("\n\n\n")
        print("-------------   Process summary files   ---------------")
        print(">> Processed : {} records".format(parsed_line_count))

        if success:
            # after a successful end of day run, create a copy of the input file and put it in the archive directory unless it was a batch run which will already be reading those files
            if self.start_date == "" or self.end_date == "": # standard eod run

                archive_file = self.config.archive_dir + '/TB_Chests'
                archive_file += '_' + self.config.clan
                archive_file += "_" + processing_date + "_DATA"
                archive_file += ".archive"

                # save input file to archive with datestamp added to file name
                shutil.copyfile(self.config.datafile, archive_file)

                print(">> Saved processed data file:")
                print(">> {}".format(ofile))

            else:
                    print(">> Saved processed data file:")
                    print(">> {}".format(ofile))

        return success
# ------------------------------------------------------------------------------------------------------
    def run_chest_summary(self):
        # generate a player chest summary based on the FINAL files in the /final directory

        date_tag = ""
    
        if self.start_date == "" or self.end_date == "":
            import datetime as dt
            current_date = dt.date.today()
            processing_date = current_date.strftime("%Y-%m-%d")
            file_pattern = self.config.final_dir + "/" + processing_date
            file_pattern += "_TB_Chests_" + self.config.clan + "_FINAL.txt"
            file_list = glob.glob(file_pattern)
        else:
            date_start = datetime.strptime(self.start_date,"%Y-%m-%d")
            date_end   = datetime.strptime(self.end_date,"%Y-%m-%d")
            file_list  = list()

            if date_start == date_end: # just one day
                date_tag = date_start
            else: # multiple days
               date_tag = self.start_date + "_" + self.end_date

            while True:
                processing_date = date_start.strftime("%Y-%m-%d")
                file_pattern = self.config.final_dir + "/" + processing_date
                file_pattern += "_TB_Chests_" + self.config.clan + "_FINAL.txt"

                file_list.append(file_pattern)

                date_start += timedelta(days=1)
                if date_start > date_end:
                    break

        # zero any values in the player summary structure
        for player in self.player_summary:
            self.player_summary[player] = [0, 0]

        for file in file_list:
            with open(file) as sp:

                while True:
                    a = 0
                    line = sp.readline()
                    if not line:
                        break            
                
                    row = line.strip()
                    columns = row.split(",")

                    player = columns[1]
                    score  = columns[4]

                    # Check if the player is in the players-database
                    playerlist = self.config.player_file
                    with open (playerlist,'r',encoding='utf-8') as checkplayer:
                        plist = checkplayer.read()
                        if player in plist:
                            a=1
                        if player == "PLAYER":
                            continue
                        if a == 0:
                            print("\n")
                            print("=======================================")
                            print(">>> Missing Player for summary ")
                            print(">>> : {}".format(player))
                            print(">>> His Points/Score will be added to  ")
                            print(">>> the player 'unknown' - or add the  ")
                            print(">>> playername to your players-list and")
                            print(">>> start the summary process again!   ")
                            print("=======================================")
                            player = 'unknown'
                    
                    self.player_summary[player][0] = self.player_summary[player][0] + int(score) # add the score
                    self.player_summary[player][1] = self.player_summary[player][1] + 1 # increase chest number count by 1
                    a = 0

        file = self.config.final_dir + "/" + processing_date
        file += "_TB_PlayerSummary_" + self.config.clan
        file += "_FINAL.txt"

        opf = open(file, 'w')
        opf.writelines("PLAYER,SCORE,CHEST\n")
    
        # sort by highest score
        player_summary_sorted = dict(sorted(self.player_summary.items(), key=lambda item: item[1], reverse=True))

        for player in player_summary_sorted:
            opf.writelines("{},{},{}\n".format( player, player_summary_sorted[player][0], player_summary_sorted[player][1]))
#            opf2.writelines("{}\n".format(player))

        print(">> Saved Player summary file:")
        print(">> {}".format(file))
        print("-------------------------------------------------------")
        
# ----------------- End of day Summary & process the capture file -------------------------------------------

        while True:
            
            fullfile                = self.config.datafile
            checkfile               = Path(fullfile)
            splitfile               = re.split(r'[/.]+',fullfile)
            var1, var2, var3, var4  = splitfile
            var5                    = self.config.clan
            savefile                = f"../{var2}/{processing_date}_{var3}_{var5}_FINAL.txt"
            
            # Datafile is present and no OneDayCapture than copy the capture-file with process-date:
            if checkfile.is_file() and odc == 0:
                
                print("-------- End of Day - Copy of Capture Summary ---------")
                print(">> Delete this File, to start a new capture-file:  ")
                print(">> {}".format(fullfile))
                print(">> Your new 'End-of-day' Capture File:             ")
                print(">> {}".format(savefile))
                print("-------------------------------------------------------")
                shutil.copy (fullfile, savefile)
                print("\n\n")
                break
                
            else:
                break

        succes = True

# ------------------------------------------------------------------------------------------------------
    def run_citadel_summary(self):
        # generate a player Citadel only summary based on the FINAL files in the /final directory
    
        citadels = ["Level 10 Citadel","Level 15 Citadel","Level 20 Citadel","Level 25 Citadel","Level 30 Citadel"]
        cursed_citadels = ["","","","","","Level 20 Citadel","Level 25 Citadel"]
        date_tag = ""
        
        if self.start_date == "" or self.end_date == "":
            print("### Calculating CITADEL summary data based on ALL files in the /final directory")

            file_pattern = self.config.final_dir + "/TB_Chests"
            file_pattern += "_" + self.config.clan
            file_pattern += "_*_FINAL.txt"
    
            file_list = glob.glob(file_pattern)
        else:
            print("### Calculating CITADEL summary data based on files from {} to {} in the /final directory".format(self.start_date, self.end_date))

            date_start = datetime.strptime(self.start_date,"%Y-%m-%d")
            date_end   = datetime.strptime(self.end_date,"%Y-%m-%d")
            file_list  = list()
            
            if date_start == date_end: # just one day
                date_tag = date_start
            else: # multiple days
               date_tag = self.start_date + "_" + self.end_date

            while True:
                processing_date = date_start.strftime("%Y-%m-%d")

                file_pattern = self.config.final_dir + "/TB_Chests"
                file_pattern += "_" + self.config.clan
                file_pattern += "_" + processing_date + "_FINAL.txt"
    
                file_list.append(file_pattern)

                date_start += timedelta(days=1)
                if date_start > date_end:
                    break

        # zero any values in the player summary structure
        for player in self.citadel_summary:
            self.citadel_summary[player] = [0, 0, 0, 0, 0, 0, 0, 0]

        for file in file_list:
            with open(file) as sp:

                print("Processing {}".format(file))

                while True:

                    line = sp.readline()
                    if not line:
                        break            
                
                    row = line.strip()
                    columns = row.split(",")

                    player = columns[1]
                    level = columns[2]
                    type = columns[3]

                    if player == "PLAYER": # skip the header row
                        continue

                    if level.find("Citadel") == -1 or type.find("Citadel") == -1: # skip non-Citadels
                        continue

                    if type.find("Cursed") > -1:
                        cursed = True
                        index = cursed_citadels.index(level)
                    else:
                        cursed = False
                        index = citadels.index(level)

                    self.citadel_summary[player][index] = self.citadel_summary[player][index] + 1 # increase this citadel count by 1
                    self.citadel_summary[player][7] = self.citadel_summary[player][7] + 1 # increase total citadel count by 1

        file = self.config.final_dir + "/TB_CitadelSummary"
        file += "_" + self.config.clan
        if date_tag != "":
            file += "_" + date_tag
        file += "_FINAL"
        file += ".txt"

        opf = open(file, 'w')
        opf.writelines("PLAYER,ELVEN_10,ELVEN_15,ELVEN_20,ELVEN_25,ELVEN_30,CURSED_20,CURSED_25,TOTAL\n")
    
        # sort by highest count
        citadel_summary_sorted = dict(sorted(self.citadel_summary.items(), key=lambda item: item[1][7], reverse=True))

        for player in citadel_summary_sorted:
            if self.skip_empty and citadel_summary_sorted[player][7] > 0: # skip lines with 0 count
                opf.writelines("{},{},{},{},{},{},{},{},{}\n".format( player, 
                                                                   citadel_summary_sorted[player][0], 
                                                                   citadel_summary_sorted[player][1],
                                                                   citadel_summary_sorted[player][2],
                                                                   citadel_summary_sorted[player][3],
                                                                   citadel_summary_sorted[player][4],
                                                                   citadel_summary_sorted[player][5],
                                                                   citadel_summary_sorted[player][6],
                                                                   citadel_summary_sorted[player][7]))

        print("\n### Citadel summary processing has been completed")
        print("### Destination file: {}\n".format(file))
        

# ------------------------------------------------------------------------------------------------------
    def run(self):
        
        if self.eod:
            
            # standard eod
            if self.start_date == "" or self.end_date == "":
                success = self.process_file(self.config.datafile, self.processing_date)
                
            # re-run EoD for the date range using data files from the /archive directory
            elif self.start_date != "" and self.end_date != "": 
    
                # Batch processing will ignore the input filename and read only form the archive direcotry
                print("\n")

                date_start = datetime.strptime(self.start_date,"%Y-%m-%d")
                date_end   = datetime.strptime(self.end_date,"%Y-%m-%d")

                while True:
                    
                    processing_date = date_start.strftime("%Y-%m-%d")

                    archive_file = self.config.archive_dir + '/TB_Chests'
                    archive_file += "_" + self.config.clan
                    archive_file += "_" + processing_date + "_DATA.archive"

                    success = self.process_file(archive_file, processing_date)
                                        
                    if not success:
                        print("*** ERROR: Batch processing of file {} was unsuccessful! Batch processing will terminate.".format(archive_file))
                        break

                    date_start += timedelta(days=1)
                    if date_start > date_end:
                        break

            self.score_def.print_no_scores()

            if not success:
                print("\n************************************************************************")
                print("***** THERE ARE ERRORS IN THE PROCESSING THAT NEED TO BE ADDRESSED *****")
                print("************************************************************************")

        if self.summary:
            self.run_chest_summary()
            
        if self.citadels:
            self.run_citadel_summary()


# TBChestCounter ----------------------------------------------------------------
parser = argparse.ArgumentParser()

parser.add_argument("--config", help="a separate configuration file that contains relevant processing paramters. these can be overridden by providing arguments", required="True")

parser.add_argument("--verbose", action="store_true", help="turns on more verbose logging to help troubleshoot malforme<d records.")
parser.add_argument("--calibrate", action="store_true", help="enters calibration mode.")
parser.add_argument("--capture", action="store_true", help="runs the chest capture software")
parser.add_argument("--process", action="store_true", help="process captured chest information")

# only used by TBCapture
parser.add_argument("--clickWait", help="time to wait between auto-clicks", default="250")

# only used by TBProcess
parser.add_argument("--date", help="optional processing date, default is current date")
parser.add_argument("--start_date", help="optional processing start date for processing a range of dates")
parser.add_argument("--end_date", help="optional processing end date for processing a range of dates")
parser.add_argument("--eod", action="store_true", help="triggers final or end of day processing of data using the /source, /final, and /archive directories.")
parser.add_argument("--summary", action="store_true", help="only generate a summary from the processed files in the /final directory")
parser.add_argument("--citadels", action="store_true", help="only generate a summary from the processed files in the /final directory")
parser.add_argument("--skip_empty", action="store_true", help="skip players with 0 value in the summary, i.e. don't print a row in the summary file")


args = parser.parse_args()
config = TBConfig(args.config, args.clickWait)

if args.calibrate:
    app1 = TBCalibration()
    app1.run(config)
elif args.capture:
    app2 = TBCapture(config, args)
    app2.run()
elif args.process:
    app3 = TBProcess(config, args)
    app3.run()

# ------------------- START PS GUI -------------------------------------------

while True: 
    print("\n")
    #print(">>> Back to PowerShell GUI?")
    print(">>> What do you want to do next?")
    print(">>> 1 : Clan {}".format(clan1))
    print(">>> 2 : Clan {}".format(clan2))
    print(">>> 3 : Clan {}".format(clan3))
    print(">>> 4 : Clan {}".format(clan4))
    print(">>> 5 : Capture More Chests (SAME CLAN)")
    print(">>> all other keys for Exit \n")
    import subprocess
    choice = input("[1] - [2] - [3] - [4] - [5] or [eXit] ? ")
    # se añade la definición que faltaba para la opción 5 y se corrige su ejecución.
    capture_command_base = r"py .\tb.py --config ..\config\config.cfg --capture" 
    
    if choice.lower() == "1":
            command = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"{pshellpath1}\""
            result = subprocess.run(command)
            break
    elif choice.lower() == "2":
            command = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"{pshellpath2}\""
            result = subprocess.run(command)
            break
    elif choice.lower() == "3":
            command = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"{pshellpath3}\""
            result = subprocess.run(command)
            break
    elif choice.lower() == "4":
            command = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"{pshellpath4}\""
            result = subprocess.run(command)
            break
    elif  choice.lower() == "5": # Lógica para la nueva opción [5]
        # Ejecuta la captura de cofres
        print(">> Launching Chest Capture...")
        
        # El comando es solo la ejecución del script Python, no necesita el wrapper de powershell.exe
        # La ejecución de 'py .\\tb.py...' se realiza directamente a través de shell=True
        command = capture_command_base
        result = subprocess.run(command, shell=True)
        break # Sale del menú y ejecuta la captura
        
        # Llama al comando de captura.
    else:
            print("\nEXIT\n")
            break
