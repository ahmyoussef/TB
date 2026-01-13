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

# AL PRINCIPIO DEL ARCHIVO tb.py (después de los imports)
import sys
import io

# Forzar UTF-8 en Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
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
            # ELIMINADOS: datafile, totalfile, working_dir, archive_dir, final_dir 
            # (Registros gestionados por DB)
            
            #self.datafile        = config_kvp.get('data','')
            #self.totalfile       = config_kvp.get('total','')
            #self.working_dir     = config_kvp.get("working", '')
            #self.archive_dir     = config_kvp.get("archive", '')
            #self.final_dir       = config_kvp.get("final", '')
            
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
        """
        Save player list and aliases to CSV file.
        Syncs both new players and new aliases from database to CSV.
        """
        
        if not self.player_set_changed:
            return
        
        if not self.player_file:
            print("[WARNING] No player file configured - changes not saved to CSV")
            return

        print("\n----------------- Player Changes Detected ------------------")
        print("### New players or aliases were added during this session")
        print("### Do you want to save them to the player CSV file?")
        
        while True:
            save = input("### Save to CSV? [Y/n]: ").strip().lower()
            if save in ("", "y", "n"):
                break

        if save == "n":
            print("### Changes NOT saved to CSV (only in database)")
            return

        try:
            # Rebuild CSV from database (source of truth)
            if self.db:
                print("[INFO] Syncing players.csv from database...")
                
                cursor = self.db.conn.cursor()
                cursor.execute("""
                    SELECT name_player, alias1_OCR, alias2_OCR, alias3_OCR, alias4_OCR,
                        alias5_OCR, alias6_OCR, alias7_OCR, alias8_OCR
                    FROM players_ocr
                    WHERE status = 'active'
                    ORDER BY name_player
                """)
                
                with open(self.player_file, 'w', encoding='utf-8') as pfp:
                    for row in cursor.fetchall():
                        player_name = row[0]
                        aliases = [row[i] for i in range(1, 9) if row[i]]
                        
                        # Format: PlayerName,alias1,alias2,...
                        line = player_name
                        if aliases:
                            line += "," + ",".join(aliases)
                        line += "\n"
                        
                        pfp.write(line)
                
                print(f"[INFO] Players and aliases saved to {self.player_file}")
                self.player_set_changed = False
                
            else:
                # Fallback: save from memory (old logic)
                print("[WARNING] No database connection - using in-memory data")
                
                with open(self.player_file, 'w', encoding='utf-8') as pfp:
                    sorted_players = sorted(self.player_set)
                    
                    for player in sorted_players:
                        player_line = player

                        # Add aliases from kvp map
                        for alias in self.player_kvp:
                            if player == self.player_kvp[alias] and alias != player.lower():
                                player_line += "," + alias

                        player_line += "\n"
                        pfp.write(player_line)
                
                print(f"[INFO] Players saved to {self.player_file}")
                self.player_set_changed = False
                
        except Exception as e:
            print(f"[ERROR] Failed to save players to CSV: {e}")
            import traceback
            traceback.print_exc()

    def validate(self, player, line):
        """
        Validate player name against database with fuzzy matching.
        Returns: (success, canonical_name) or (False, player) if aborted
        """        
        # Assume success
        success = True
        
        # Clean player string
        player = player.strip()
        
        # 1. BÚSQUEDA EXACTA EN LA BD (nombres canónicos y aliases)
        if self.db:
            player_id = self.db.resolve_player_id(player)
            
            if player_id is not None:
                # Jugador o alias encontrado - obtener nombre canónico
                try:
                    cursor = self.db.conn.cursor()
                    cursor.execute("SELECT name_player FROM players_ocr WHERE id_player = ?", (player_id,))
                    canonical_name = cursor.fetchone()
                    if canonical_name:
                        return True, canonical_name[0]
                except Exception as e:
                    print(f"### WARNING: Failed to retrieve canonical name for ID {player_id}: {e}")
                    return True, player
        
        # 2. FUZZY MATCHING - Buscar jugador más similar
        print(f"\n### Player '{player}' not found in database")
        print("### Searching for similar players (fuzzy matching)...")
        
        best_score = 0
        best_match = ""
        
        # Get all active players from DB
        if self.db:
            all_players = self.db.get_all_players()
        else:
            all_players = list(self.player_set)
        
        for candidate in all_players:
            score = SM(None, player.lower(), candidate.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = candidate
        
        # If fuzzy match is good enough (>75% similarity), suggest it
        if best_score > 0.75:
            print(f"\n*** FUZZY MATCH FOUND ***")
            print(f"*** OCR captured : '{player}'")
            print(f"*** Best match   : '{best_match}' (similarity: {best_score:.1%})")
            print(f"*** Is this correct?")
            
            while True:
                ans = input("\n*** [Y]es / [N]o / [-] abort: ").strip().upper()
                if ans in ("Y", "N", "-"):
                    break
            
            if ans == "-":
                return False, player  # Abort
            
            if ans == "Y":
                # Use the matched player
                canonical_name = best_match
                
                # If OCR input is different, add as alias
                if player.lower() != canonical_name.lower():
                    # Get player ID for the matched name
                    matched_id = self.db.resolve_player_id(canonical_name)
                    if matched_id:
                        try:
                            # Add OCR input as alias
                            if self.db.add_alias(matched_id, player):
                                print(f"### Alias '{player}' added to player '{canonical_name}'")
                                
                                # Sync to CSV
                                self.player_kvp[player.lower()] = canonical_name
                                self.player_set_changed = True
                            
                        except Exception as e:
                            print(f"### ERROR: Could not add alias: {e}")
                
                return True, canonical_name
            
            # If user said NO to fuzzy match, continue to manual input
        
        # 3. JUGADOR DESCONOCIDO - PREGUNTAR AL USUARIO
        print("\n* ATTENTION: UNKNOWN OR NEW PLAYER")
        print(f"- OCR captured: '{player}'")
        print("- Press <Enter> if correct (will be added as new player)")
        print("- Or type the correct 'Name/Alias' for the player") 
        print("- Or type '-' to abort the process!\n")
        
        player_name = input("<Enter> or ['Name/Alias'] or ['-']: ").strip()
            
        if player_name == "-":
            return False, player  # Abort
        
        # 4. PROCESAR LA RESPUESTA DEL USUARIO
        
        # Si el usuario ingresó un texto, ese es el nombre canónico/corregido
        if len(player_name) > 0:
            canonical_name = player_name
        # Si el usuario pulsó Enter, el nombre OCR es el nombre canónico
        else:
            canonical_name = player
            
        # 5. OPERACIÓN EN LA BASE DE DATOS
        
        # Buscamos si el 'canonical_name' ya existe
        canonical_id = self.db.resolve_player_id(canonical_name)
        print(f"\n### Adding NEW PLAYER ID: '{canonical_id}'")
        print(f"\n### Adding NEW PLAYER NAME: '{canonical_name}'")
        if canonical_id is None:
            # Caso A: JUGADOR NUEVO (El nombre no existe en la BD)
            print(f"\n### Adding NEW PLAYER NAME: '{canonical_name}'")
            try:
                # 5.1. Añadir el nombre canónico como nuevo jugador
                new_id = self.db.add_player(canonical_name)
                print(f"### New Player '{canonical_name}' added to database (ID: {new_id}).")
                
                # 5.2. SINCRONIZACIÓN con CSV
                if canonical_name not in self.player_set:
                    self.player_set.add(canonical_name)
                    self.player_set_changed = True
                
                # 5.3. Si el OCR es diferente al nombre canónico, añadir OCR como alias
                if canonical_name.lower() != player.lower():
                    if self.db.add_alias(new_id, player):
                        print(f"### OCR value '{player}' saved as alias for '{canonical_name}'.")
                        
                        # 5.4. SINCRONIZACIÓN de Alias con CSV
                        self.player_kvp[player.lower()] = canonical_name
                        self.player_set_changed = True
                    else:
                        print(f"### WARNING: add_alias returned False")

            except Exception as e:
                print(f"### ERROR: Could not add player/alias to database: {e}")
                import traceback
                traceback.print_exc()
                return False, player

        elif canonical_id is not None and canonical_name.lower() != player.lower():
            # Caso B: NUEVO ALIAS (El nombre canónico EXISTE, pero el input OCR es diferente)
            try:
                # 5.5. Añadir player como nuevo alias para el ID existente
                if self.db.add_alias(canonical_id, player):
                    print(f"### OCR value '{player}' saved as new alias for existing player '{canonical_name}'.")

                    # 5.6. SINCRONIZACIÓN de Alias con CSV
                    self.player_kvp[player.lower()] = canonical_name
                    self.player_set_changed = True

            except Exception as e:
                print(f"### ERROR: Could not add alias to database: {e}")
                import traceback
                traceback.print_exc()
                return False, player
        
        # Retorna True y el nombre canónico final
        return True, canonical_name
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
        # Variables de clase
    score_file = ''
    
    def __init__(self, score_file=None, db=None):  # ✅ CORREGIDO
        """
        Initialize TBSource with optional database and score file.
        
        Args:
            score_file (str): Path to scores CSV file
            db (TBDatabase): Database instance
        """
        self.score_file = score_file  # ✅ CORREGIDO
        self.db = db  # ✅ CORREGIDO
        self.sources_changed = False  # ✅ CORREGIDO
    
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
            
        # Remove ; , . ! ? etc. but keep : (for "Level 5: Something")
        while source and source[0] in (';', ',', '.', '!', '?', '"', "'", '`'):
            source = source[1:].strip()
            #print(f"### Cleaned punctuation from source start: '{source}'")
            
        # Get all known sources from database
        known_sources = []
        if self.db:
            try:
                cursor = self.db.conn.cursor()
                cursor.execute("SELECT chest_source FROM chest_scores ORDER BY chest_source")
                known_sources = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                print(f"[WARNING] Could not load sources from DB: {e}")
        
        # List of known source types: Check if source exists (case-insensitive exact match)
        source_lower = source.lower()
        for known in known_sources:
            if known.lower() == source_lower:
                return True, known  # Return the canonical case from DB
        
        #FUZZY MATCHING for unknown sources
        print(f"\n### Source '{source}' not found in database")
        print("### Searching for similar sources (fuzzy matching)...")
        
        best_score = 0
        best_match = ""
        
        for candidate in known_sources:
            score = SM(None, source_lower, candidate.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = candidate
        
        # If fuzzy match is good enough (>80% similarity), suggest it
        if best_score > 0.80:
            print(f"\n*** FUZZY MATCH FOUND ***")
            print(f"*** OCR captured : '{source}'")
            print(f"*** Best match   : '{best_match}' (similarity: {best_score:.1%})")
            print(f"*** Is this correct?")
            
            while True:
                ans = input("\n*** [Y]es / [N]o / [-] abort: ").strip().upper()
                if ans in ("Y", "N", "-"):
                    break
            
            if ans == "-":
                return False, source  # Abort
            
            if ans == "Y":
                return True, best_match  # Use matched source
            
            # If user said NO to fuzzy match, continue to manual input
        
        # Source not found and no good fuzzy match - ask user
        print(f"\n*** UNKNOWN SOURCE: '{source}'")
        print("*** This source is not in the database")
        print("*** Options:")
        print("***   - Press <Enter> to add it as new source")
        print("***   - Type the correct source name")
        print("***   - Type '-' to abort\n")
        
        user_input = input("<Enter> or ['Correct Source'] or ['-']: ").strip()
        
        if user_input == "-":
            print("### Process aborted by user")
            return False, source
        
        # Determine canonical source name
        if len(user_input) > 0:
            canonical_source = user_input
            print(f"### User entered: '{canonical_source}'")
        else:
            canonical_source = source
            print(f"### User pressed Enter: Using '{canonical_source}' as new source")
        
        # Check if canonical_source already exists
        canonical_lower = canonical_source.lower()
        for known in known_sources:
            if known.lower() == canonical_lower:
                print(f"### Source '{known}' already exists")
                return True, known
        
        # Add new source to database
        print(f"\n### Adding NEW SOURCE: '{canonical_source}'")
        print("### Enter score/points for this source")
        
        while True:
            score_input = input(f"Score (default: 0): ").strip()
            if score_input == "":
                score_value = 0
                break
            try:
                score_value = int(score_input)
                if score_value < 0:
                    print("### Score must be >= 0")
                    continue
                break
            except ValueError:
                print("### Invalid input, enter a number")
        
        # Add to database
        if self.db:
            try:
                cursor = self.db.conn.cursor()
                cursor.execute("""
                    INSERT INTO chest_scores (chest_source, point_value)
                    VALUES (?, ?)
                """, (canonical_source, score_value))
                self.db.conn.commit()
                print(f"### ✅ Source '{canonical_source}' added to database (score: {score_value})")
                
                # CRITICAL: Save to CSV immediately with debug
                print(f"### Attempting to save to CSV...")
                print(f"### score_file = '{self.score_file}'")
                print(f"### db = {self.db}")
                
                if not self.score_file:
                    print(f"[ERROR] score_file is empty or None!")
                elif not self.db:
                    print(f"[ERROR] db is None!")
                else:
                    self._save_to_csv()
                
            except Exception as e:
                print(f"### ERROR: Could not add source to database: {e}")
                import traceback
                traceback.print_exc()
                return False, source
        else:
            print(f"[ERROR] No database connection available")
            return False, source

        #source = self._fix_ocr_errors(source)
        
        return True, canonical_source
    
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
    # -------------------------------------------------------
    def _save_to_csv(self):
        """
        Save all sources from database to CSV file immediately.
        No user prompt - automatic sync.
        """
        if not self.score_file:
            print("[WARNING] No score file configured")
            return
        
        if not self.db:
            print("[WARNING] No database connection")
            return
        
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT chest_source, point_value 
                FROM chest_scores 
                ORDER BY chest_source
            """)
            
            with open(self.score_file, 'w', encoding='utf-8') as f:
                # Write header
                f.write("source,points\n")
                
                # Write all sources
                for row in cursor.fetchall():
                    f.write(f"{row[0]},{row[1]}\n")
            
            print(f"### ✅ Saved sources to {self.score_file}")
            self.sources_changed = False
            
        except Exception as e:
            print(f"[ERROR] Failed to save sources to CSV: {e}")
            import traceback
            traceback.print_exc()

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

    def __init__(self, log_dir="working", batch_mode=False):
        self.max_hours = 19
        self.max_minutes = 59
        self.max_seconds = 59
        self.log_dir = log_dir
        self.batch_mode = batch_mode
        os.makedirs(self.log_dir, exist_ok=True)

        self.corrections_log = os.path.join(log_dir, "ocr_corrections.log")
        self.missing_log     = os.path.join(log_dir, "missing_timeleft.log")
        
        # ✅ CRITICAL: Pre-compile regex patterns
        self.TIME_PATTERNS = [
            re.compile(r'(?P<h>\d{1,3})\s*[hH]\s*[:\s]?\s*(?P<m>\d{1,2})\s*[mM]\s*[:\s]?\s*(?P<s>\d{1,2})\s*[sS]?', re.IGNORECASE),
            re.compile(r'(?P<h>\d{1,3})\s*[hH]\s*[:\s]?\s*(?P<m>\d{1,2})\s*[mM]?', re.IGNORECASE),
            re.compile(r'(?P<m>\d{1,3})\s*[mM]\s*[:\s]?\s*(?P<s>\d{1,2})\s*[sS]?', re.IGNORECASE),
            re.compile(r'(?P<n1>\d{1,3})\D+(?P<n2>\d{1,2})(?:\D+(?P<n3>\d{1,2}))?'),
            re.compile(r'^(?P<only>\d{1,3})$')
        ]
        
        # ✅ Context tracking
        self.previous_time = None
        
        # ✅ Auto-corrections for known OCR patterns
        self.auto_corrections = {
            144: 14, 155: 15, 166: 16, 177: 17, 188: 18, 199: 19
        }

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
            #print("*** WARNING: Time-left empty OCR line")
            self._log_missing("empty_time_line")
            return False, 0, 0, 0, "0 h : 0 m : 0 s"

        #print(f"### [DEBUG] Raw time OCR input: '{raw_original}'")
        
        # 1. Limpieza inicial: Remove prefix "Time left:"
        s = re.sub(r'(?i).*time\s*left[:\s]*', '', raw_original).strip()
        
        # 2. Normalizar caracteres Unicode raros
        s = s.replace('\u2212', '-').replace('\u2013', '-').replace('\u00A0', ' ')
        s = re.sub(r'[^\x00-\x7F]', ' ', s)
        
        # ✅ Corregir "12hm" → "12h 0m"
        s = re.sub(r'(\d+)hm\b', r'\1h 0m', s, flags=re.IGNORECASE)
        
        # ✅ "lh" → "1h" y "Oh" → "0h"
        s = re.sub(r'\blh\b', '1h', s, flags=re.IGNORECASE)
        s = re.sub(r'\bOh\b', '0h', s, flags=re.IGNORECASE)
        
        # 3. normalizar espacios alrededor de h/m/s
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

        # Round seconds
        if s >= 30:
            print(f"*** INFO: seconds {s} >=30 → add 1 minute")
            m += 1
            s = 0

        # Normalize overflow minuts
        if m >= 60:
            print(f"*** INFO: normalizing minutes: {m} -> add hours")
            h += m // 60
            m = m % 60
        
        # ✅ FIX X2: Auto-correct 144h, 155h, etc. (repeated digit pattern)
        original_h = h
        if h in self.auto_corrections:
            h = self.auto_corrections[h]
            print(f"[AUTO-FIX] {original_h}h → {h}h (OCR repeated digit)")
            self._log_correction(f"{original_h} h", f"{h} h", "repeated_digit_pattern")
        
        elif h >= 100:
            h_str = str(h)
            if len(h_str) == 3 and h_str[0] == h_str[1]:
                corrected = int(h_str[1:])
                if 10 <= corrected <= 19:
                    print(f"[AUTO-FIX] {h}h → {corrected}h (detected pattern)")
                    h = corrected
                    self._log_correction(f"{original_h} h", f"{h} h", "auto_pattern_10_19")
                    
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
        
        # ✅ OPTIMIZATION: Context-aware validation
        if self.previous_time and 0 <= h <= 19:
            prev_h, prev_m = self.previous_time
            prev_total = prev_h * 60 + prev_m
            curr_total = h * 60 + m
            
            # Los cofres se capturan en orden, el tiempo debe DISMINUIR
            time_diff = prev_total - curr_total
            
            # Si el tiempo aumenta más de 5 min, es sospechoso
            if time_diff < -5:
                print(f"\n[WARNING] Time increased from {prev_h}h:{prev_m}m to {h}h:{m}m")
                print(f"[INFO] This is unusual (should decrease)")
                
        # Validar rango de horas sospechoso (>= 20)
        if h >= 20:
            print(f"\n*** WARNING: Suspicious time detected at line {line_number}")
            print(f"*** CAPTURED: {h} h : {m} m")
            
            if self.previous_time:
                prev_h, prev_m = self.previous_time
                print(f"*** Previous chest: {prev_h}h:{prev_m}m (for reference)")
            
            print("*** Valid range: 0–19 hours")
            print("*** If correct press [Y], or [N] to reject,")
            print("*** or enter manual correction e.g. '14 58' for 14h58m\n")

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
        
        # --- Special case: Dark Omens ranking chest (reward 1st place) gives 0 score ---
        if chest.lower() == "dark omens ranking chest" and source.lower() == "dark omens event":
            return "0"
        
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
        self.config = config
        
        # Usar clan de args si está disponible, sino de config
        self.clan_name = args.clan if hasattr(args, 'clan') and args.clan else config.clan
        
        self.db = None  # Inicializar variable
        self.db_integration = None  

        #self.player_def             = TBPlayer(config.player_file)
        self.chest_def              = TBChest(config.quality_file)
        self.source_def             = TBSource()
        self.screen                 = TBScreen()
        self.fix_ocr_def            = TBFixOCR(config.fix_ocr_file)
        self.time_left_def          = TBTimeLeft()

        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # GENERAR RUTA ESPECÍFICA POR CLAN
            db_filename = f"tb_chests_{self.clan_name.lower().replace(' ', '_')}.db"
            db_path = os.path.join(project_root, "data", db_filename)
            print(f"[INFO] Clan: {self.clan_name}")
            print(f"[INFO] Database: {db_path}")
            
            self.db = TBDatabase(db_path=db_path, clan_name=self.clan_name)

            # Cargar configuración CSV (players, clan_members, scores) en la BD en memoria
            config_players = os.path.join(project_root, "config", "players.csv")
            config_members = os.path.join(project_root, "config", "clan_members.csv")
            config_scores  = os.path.join(project_root, "config", "scores-hlo.csv")

            self.db.load_config_data(config_players, config_members, config_scores)

            # Inicializar integración opcional (si tienes clase TBDatabaseIntegration)
            try:
                self.db_integration = TBDatabaseIntegration(
                    self.db,
                    clan_name=config.clan,
                    id_user=None,
                    verbose=args.verbose
                )
            except Exception:
                self.db_integration = None

            print("[INFO] DB ready. TXT intermediate files disabled.")
        except Exception as e:
            print(f"[WARNING] No se pudo conectar con la BD: {e}")
            self.db = None
            self.db_integration = None

        # NO abrimos ni sfile, wfile ni tfile en el nuevo flujo.
        # Solo mantenemos el capture RAW file *opcional* si debug verbose:
        
        self.cfile = None
        if args.verbose:
            capturefile = config.working_dir + '/TB_Capture_RAW'
            if len(config.clan) > 0:
                capturefile += '_' + config.clan
            capturefile += '_' + self.processing_datetime
            capturefile += '.txt'
            try:
                self.cfile = open(capturefile, 'w', encoding='utf-8')
            except Exception as e:
                print(f"[WARNING] No se pudo abrir capturefile: {e}")
                self.cfile = None

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
        
        """
        # Log raw capture
        self.cfile.write(
            "--------------- {} --------------------------\n".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        self.cfile.write(capture + "\n")
        self.cfile.flush()
        """
        
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
                
                # ============================================================
                # VALIDACIÓN DE JUGADOR CON INTERACCIÓN SI NO EXISTE EN LA BD
                # ============================================================

                try:
                    pres = self.player_def.validate(player, i)
                    if pres is None:
                        # El jugador NO existe en base de datos
                        print(f"\n*** WARNING: Player '{player}' does not exist in database.")
                        while True:
                            ans = input(f"Do you want to ADD '{player}' as a new player? [Y/N]: ").strip().upper()
                            if ans == "Y":
                                try:
                                    new_id = self.db.add_player(player)   # requiere método simple en TBDatabase
                                    print(f"*** Player '{player}' added to database with ID {new_id}.")
                                    final_player = player
                                    break
                                except Exception as e:
                                    print(f"*** ERROR while adding player: {e}")
                                    print("*** Cannot continue with this chest.")
                                    final_player = None
                                    break

                            elif ans == "N":
                                print("*** Player rejected by user → Chest discarded.")
                                final_player = None
                                break
                            else:
                                print("*** Invalid input. Please press Y or N.")
                    else:
                        # Jugador corregido por OCR / alias
                        final_player = pres[1]

                except Exception as e:
                    print(f"[ERROR] Validating player: {e}")
                    final_player = None

                # Si no hay jugador válido → descartar este chest
                if final_player is None:
                    print("\n*** This chest entry will be SKIPPED because player is invalid.\n")
                    # No hacemos append
                    # No incrementamos records_found
                    # Simplemente pasamos al siguiente chest
                    chest = None
                    player = None
                    source = None
                    time_left = None
                    
                    # Siempre incrementamos 'i' para avanzar a la siguiente línea.
                    # Si se usó 'continue' arriba, esta línea se salta, pero como es un solo cofre
                    # y solo hay 4 líneas, da igual. Lo importante es que no se salte 'Source' por error.
                    i += 1
                    continue

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
        """
        Save validated records directly into the SQLite DB.
        - No TXT intermediates (unless verbose and cfile open)
        - Duplicate detection: same chest, same player, same source,
          collection_date within +/-10 seconds -> replace previous (UPDATE)
        - Keeps print UI output similar to original behavior.
        """

        if not self.records or len(self.records) == 0:
            print("[INFO] No records to save.")
            return

        if not self.db:
            print("[ERROR] No database available - cannot save records.")
            return

        inserted = 0
        replaced = 0
        failed = 0

        for rec in self.records:
            chest_name = rec[0]
            player_name = rec[1]
            time_left_str = rec[2]   # e.g. "7 h : 30 m"
            chest_source = rec[3]

            # Print for user
            print("\n-------------------------------------------------------")
            print(f"{chest_name}")
            print(f"From : {player_name}")
            print(f"Time left : {time_left_str}")
            print(f"Source : {chest_source}")
            print("-------------------------------------------------------")

            # Resolve player id (may prompt if unknown)
            try:
                id_player = self.db.resolve_player_id(player_name)
                if id_player is None:
                    print(f"[ERROR] Player '{player_name}' not found in database after validation")
                    failed += 1
                    continue
            except Exception as e:
                print(f"[ERROR] Player resolution failed for '{player_name}': {e}")
                failed += 1
                continue

            # Compute collection_date using DB helper (consistent logic)
            try:
                collection_date = self.db._calculate_collection_date(time_left_str)
                # Convert to datetime for duplicate window calc
                coll_dt = datetime.strptime(collection_date, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"[WARNING] Could not compute collection_date from '{time_left_str}': {e}")
                coll_dt = datetime.utcnow()

            # Duplicate detection: +/- 10 seconds
            try:
                window_lo = (coll_dt - timedelta(seconds=10)).strftime("%Y-%m-%d %H:%M:%S")
                window_hi = (coll_dt + timedelta(seconds=10)).strftime("%Y-%m-%d %H:%M:%S")
                cur = self.db.conn.cursor()
                cur.execute("""
                    SELECT id_register FROM chest_register
                    WHERE chest_name = ?
                      AND id_player = ?
                      AND chest_source = ?
                      AND collection_date BETWEEN ? AND ?
                    LIMIT 1
                """, (chest_name, id_player, chest_source, window_lo, window_hi))
                dup = cur.fetchone()
            except Exception as e:
                print(f"[WARNING] Duplicate check failed: {e}")
                dup = None

            # Prepare chest_data for insertion/update
            chest_data = {
                'chest_name': chest_name,
                'player_ocr': player_name,
                'time_left': time_left_str,
                'chest_source': chest_source
            }

            if dup:
                # Replace old record (policy B)
                try:
                    existing_id = dup[0]
                    # Delete or update: we will UPDATE fields
                    cur.execute("""
                        UPDATE chest_register
                        SET id_player = ?, time_left = ?, collection_date = ?, points_awarded = ?
                        WHERE id_register = ?
                    """, (
                        id_player,
                        time_left_str,
                        coll_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        (self.db._get_points_for_source(chest_source) if hasattr(self.db, '_get_points_for_source') else 0),
                        existing_id
                    ))
                    self.db.conn.commit()
                    print(f"[INFO] Duplicate found - updated existing record ID {existing_id}")
                    replaced += 1
                except Exception as e:
                    print(f"[ERROR] Failed to replace duplicate record: {e}")
                    failed += 1
                continue

            # No duplicate -> insert via DB API
            try:
                new_id = self.db.insert_chest_record(chest_data, self.config.clan)
                if new_id:
                    inserted += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"[ERROR] Failed to insert chest record: {e}")
                failed += 1

        # Summary
        print("\n======================================================================")
        print(f">>> ✅ {inserted} record(s) inserted, {replaced} record(s) replaced, {failed} failed.")
        print("======================================================================\n")

        # Clear in-memory buffer after save
        self.records = []
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
# ====================================================================================================
# TBCapture  — VERSIÓN FINAL CORREGIDA (sin archivos TXT, sin self.cfile, con validación jugador A)
# ====================================================================================================
class TBCapture(object):
    """
    Main class for capturing chest information from TB Gift screen.
    FIXED: Proper loop control, improved duplicate detection, no infinite loops.
    """

    def __init__(self, config, args):
        self.processing_datetime = datetime.now().strftime("%Y-%m-%d %H.%M.%S")
        self.debug_mode          = args.verbose
        self.clickWait           = args.clickWait
        self.config              = config

        self.db = None
        self.db_integration = None
        
        # OPTIMIZATION 1: Pre-compile regex patterns (usado en validate_capture)
        self.regex_from = re.compile(r"from\s*:?\s*(.+)", re.IGNORECASE)
        self.regex_source = re.compile(r"source\s*:?\s*(.+)", re.IGNORECASE)
        self.regex_time = re.compile(r"time\s*left\s*:?\s*(.+)", re.IGNORECASE)
        
        # Initialize components /config files
        self.chest_def  = TBChest(config.quality_file)
        #self.source_def = TBSource()
        self.source_def = TBSource(score_file=config.score_file, db=self.db)
        self.screen     = TBScreen()
        self.fix_ocr_def = TBFixOCR(config.fix_ocr_file)
        self.time_left_def = TBTimeLeft()
        
        # OPTIMIZATION 2: Memory cache for fast lookups (ligero, <2MB)
        self.player_cache = {}     # {player_name_lower: canonical_name}
        self.source_cache = {}     # {source_lower: canonical_source}
        self.last_player = None    # Para lazy validation

        # OPTIMIZATION 3: Batch commit counter
        self.pending_commits = 0
        self.batch_size = 10       # Commit cada 10 registros
        
        # Connect to database
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_root, "data", "db", "tb_chests.db")
            self.db = TBDatabase(db_path)

            config_players = os.path.join(project_root, "config", "players.csv")
            config_members = os.path.join(project_root, "config", "clan_members.csv")
            config_scores  = os.path.join(project_root, "config", "scores-hlo.csv")

            self.db.load_config_data(config_players, config_members, config_scores)

            try:
                self.db_integration = TBDatabaseIntegration(
                    self.db,
                    clan_name=config.clan,
                    id_user=None,
                    verbose=args.verbose
                )
            except:
                self.db_integration = None
            if not self.debug_mode:
                print("[INFO] Database ready")
            else:
                print("[INFO] Database ready - TXT files disabled")
                
            # Assign db to source_def: Set db reference AFTER connection
            self.source_def.db = self.db
            #print("[INFO] Database ready - TXT files disabled")
            #print(f"[DEBUG] TBSource.db = {self.source_def.db}")
            #print(f"[DEBUG] TBSource.score_file = '{self.source_def.score_file}'")
            
            # ✅ OPTIMIZATION 4: Pre-load players and sources into cache
            self._load_caches()

        except Exception as e:
            print(f"[WARNING] Could not connect to database: {e}")
            self.db = None
            self.db_integration = None

        self.records = list()
        self.maxClicks   = 0
        self.totalClicks = 0

        # Player manager with database integration
        self.player_def = TBPlayer(config.player_file, db=self.db)
        
        
    def _load_caches(self):
        """
        Load players and sources into memory cache for fast lookups.
        Evita consultas repetidas a la BD durante captura.
        """
        if not self.db:
            return
        
        try:
            cursor = self.db.conn.cursor()
            
            # Load players (canonical + aliases)
            cursor.execute("""
                SELECT name_player, alias1_OCR, alias2_OCR, alias3_OCR, alias4_OCR,
                    alias5_OCR, alias6_OCR, alias7_OCR, alias8_OCR
                FROM players_ocr
                WHERE status = 'active'
            """)
            
            for row in cursor.fetchall():
                canonical = row[0]
                # Cache canonical name
                self.player_cache[canonical.lower()] = canonical
                # Cache all aliases
                for i in range(1, 9):
                    if row[i]:
                        self.player_cache[row[i].lower()] = canonical
            
            # Load sources
            cursor.execute("SELECT chest_source FROM chest_scores")
            for row in cursor.fetchall():
                source = row[0]
                self.source_cache[source.lower()] = source
            
            if self.debug_mode:
                print(f"[DEBUG] Cached {len(self.player_cache)} player entries")
                print(f"[DEBUG] Cached {len(self.source_cache)} sources")
        
        except Exception as e:
            if self.debug_mode:
                print(f"[WARNING] Could not load caches: {e}")
    # =====================================================================
    def validate_capture(self, capture, count):
        """
        Validate merged capture (chest info + time).
        Returns True if valid records found, False otherwise.
        """
        import re

        self.records = []
        success = True

        print("\n" + "*"*70)
        print(">> CAPTURED TEXT (merged chest + time):")
        #print("*"*70)
        print(capture)
        print("*"*70 + "\n")

        lines = [x.strip() for x in capture.split("\n") if x.strip()]
        if not lines:
            print("### No chests found (OCR returned empty)")
            return False

        chest = None
        player = None
        source = None
        time_left = None

        total = len(lines)
        records_found = 0
        i = 0

        while i < total and records_found < count:
            text = lines[i]

            # Detect CHEST name
            if (chest is None and 
                "from" not in text.lower() and 
                "source" not in text.lower() and 
                "time" not in text.lower()):
                chest = text

            # Detect FROM (player)
            elif "from" in text.lower() and player is None:
                m = re.search(r"from\s*:?\s*(.+)", text, re.IGNORECASE)
                if m:
                    player = m.group(1).strip()

            # Detect SOURCE
            elif "source" in text.lower() and source is None:
                m = re.search(r"source\s*:?\s*(.+)", text, re.IGNORECASE)
                if m:
                    source = m.group(1).strip()

            # Detect TIME LEFT
            elif time_left is None:
                raw_candidate = None
                lower = text.lower()
                not_time_keywords = ("source", "from", "chest")

                if "time left" in lower:
                    m = re.search(r"time\s*left\s*:?\s*(.+)", text, re.IGNORECASE)
                    raw_candidate = m.group(1).strip() if m else text
                elif not any(k in lower for k in not_time_keywords):
                    if re.search(r"\d", lower):
                        if re.search(r"[hms]", lower) or re.search(r"\d+\s*[:]\s*\d+", lower):
                            raw_candidate = text.strip()

                if raw_candidate:
                    ok_ex, h, mnt, sec, raw_time = self.time_left_def.extract(raw_candidate)
                    if not ok_ex:
                        time_left = "0 h : 0 m"
                    else:
                        ok_v, hcorr, mcorr, scorr, usercorr = self.time_left_def.validate(h, mnt, sec, i)
                        if ok_v:
                            time_left = f"{hcorr} h : {mcorr} m"
                        else:
                            time_left = "0 h : 0 m"

            # Finalize one chest record
            if chest and player and source and time_left:
                # Validate player
                try:
                    pres = self.player_def.validate(player, i)
                    if pres is None:
                        print(f"\n*** WARNING: Player '{player}' not in database")
                        while True:
                            r = input(f"Add '{player}' as new player? [Y/N]: ").upper()
                            if r == "Y":
                                try:
                                    new_id = self.db.add_player(player)
                                    print(f"*** Player '{player}' added (ID: {new_id})")
                                    final_player = player
                                    break
                                except Exception as e:
                                    print(f"[ERROR] Could not add player: {e}")
                                    final_player = None
                                    break
                            elif r == "N":
                                print("*** Player rejected → chest SKIPPED")
                                final_player = None
                                break
                            else:
                                print("*** Invalid input, press Y or N")
                    else:
                        final_player = pres[1]
                except Exception as e:
                    print(f"[ERROR] Player validation failed: {e}")
                    final_player = None

                if final_player is None:
                    print("\n*** Chest discarded (invalid player)\n")
                    chest = player = source = time_left = None
                    i += 1
                    continue

                # Validate source
                try:
                    sres = self.source_def.validate(source, i)
                    final_source = source if sres is None else sres[1]
                except:
                    final_source = source

                # Add record
                self.records.append([chest, final_player, time_left, final_source])
                records_found += 1

                # Reset for next chest
                chest = None
                player = None
                source = None
                time_left = None

            i += 1

        # Handle no records found
        if records_found == 0:
            print("### No valid chests found in capture!")
            print("*** Check: Is the game in English?")
            print("*** Check: Capture area coordinates correct?\n")

            while True:
                print(">>> [1] Capture again")
                print(">>> [2] Save anyway (force)")
                print(">>> [3] Stop process")
                print(">>> [4] Show raw text")
                ans = input("\n*** Choose [1/2/3/4]: ").strip()

                if ans == "4":
                    print("\n" + "="*70)
                    print("RAW OCR TEXT:")
                    print("="*70)
                    print(capture)
                    print("="*70 + "\n")
                    continue

                if ans in ("1", "2", "3"):
                    break

            if ans == "3":
                return False
            if ans == "2":
                return True
            if ans == "1":
                return False

        return True

    # =====================================================================
    def save_records(self):
        """
        Save records to SQLite database with improved duplicate detection.
        Duplicate window: ±3 minutes (hardcoded, no config file needed).
        
        Returns:
            tuple: (inserted_count, skipped_count, failed_count)
        """
        if not self.records or len(self.records) == 0:
            print("[INFO] No records to save")
            return (0, 0, 0)

        if not self.db:
            print("[ERROR] No database connection - cannot save")
            return (0, 0, 0)

        inserted = 0
        skipped_duplicates = 0
        failed = 0

        # ✅ OPTIMIZATION: Prepare session once (outside loop)
        try:
            cur = self.db.conn.cursor()
            cur.execute("""
                SELECT id_session FROM capture_sessions 
                WHERE clan_name = ? AND DATE(session_date) = DATE('now') AND status = 'active'
                LIMIT 1
            """, (self.clan_name,))
            
            session = cur.fetchone()
            if session:
                id_session = session[0]
            else:
                cur.execute("INSERT INTO capture_sessions (clan_name, status) VALUES (?, 'active')", (self.config.clan,))
                self.db.conn.commit()
                id_session = cur.lastrowid
        except Exception as e:
            print(f"[ERROR] Session creation failed: {e}")
            id_session = None
        
        for rec in self.records:
            chest_name, player_name, time_left_str, chest_source = rec
            if self.debug_mode:
                print("\n" + "-"*70)
                print(f"CHEST: {chest_name}")
                print(f"FROM: {player_name}")
                print(f"TIME LEFT: {time_left_str}")
                print(f"SOURCE: {chest_source}")
                print("-"*70)

            # Resolve player ID (usando caché si es posible)
            try:
                id_player = self.db.resolve_player_id(player_name)
                if id_player is None:
                    print(f"[ERROR] Player '{player_name}' not found")
                    failed += 1
                    continue
            except Exception as e:
                print(f"[ERROR] Player resolution failed: {e}")
                failed += 1
                continue

            # Calculate collection date
            try:
                collection_date = self.db._calculate_collection_date(time_left_str)
                coll_dt = datetime.strptime(collection_date, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"[WARNING] Could not compute date: {e}")
                coll_dt = datetime.now()

            # DUPLICATE DETECTION - FIXED: Use capture_timestamp instead of collection_date
            try:
                cur = self.db.conn.cursor()
                
                # Calculate duplicate window: 2x clickWait (in seconds)
                # clickWait is in milliseconds, so convert: (clickWait * 2) / 1000
                duplicate_window_seconds = (int(self.clickWait) * 2) / 1000
                
                # Check for duplicate: same chest + same player + same source + capture_timestamp
                cur.execute("""
                    SELECT id_register, capture_timestamp, collection_date 
                    FROM chest_register
                    WHERE chest_name = ?
                      AND id_player = ?
                      AND chest_source = ?
                       AND capture_timestamp >= datetime('now', printf('-%d seconds', ?))
                    ORDER BY capture_timestamp DESC
                    LIMIT 1
                """,  (chest_name, id_player, chest_source, duplicate_window_seconds))
                
                dup = cur.fetchone()
                
                if dup:
                    if self.debug_mode:
                        existing_id = dup[0]
                        existing_capture = dup[1]
                        
                        print(f"\n⚠️  DUPLICATE DETECTED (within {duplicate_window_seconds:.1f}s):")
                        print(f"   - Existing ID: {existing_id}")
                        print(f"   - Previous capture: {existing_capture}")
                        print(f"   → SKIPPED (same OCR capture repeated)\n")
                    skipped_duplicates += 1
                    continue
                    
            except Exception as e:
                print(f"[WARNING] Duplicate check failed: {e}")

            # INSERT RECORD
            try:
                cur.execute("""
                    INSERT INTO chest_register 
                    (id_player, chest_name, chest_source, time_left, collection_date, id_session)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id_player, chest_name, chest_source, time_left_str, 
                      coll_dt.strftime("%Y-%m-%d %H:%M:%S"), id_session))
                
                # ✅ OPTIMIZATION: Batch commit (cada 10 registros)
                self.pending_commits += 1
                if self.pending_commits >= self.batch_size:
                    self.db.conn.commit()
                    self.pending_commits = 0
                    if self.debug_mode:
                        print(f"[BATCH COMMIT] {self.batch_size} records")
                
                id_chest = cur.lastrowid
                
                # Update session counter
                if id_session:
                    cur.execute("UPDATE capture_sessions SET total_chests_captured = total_chests_captured + 1 WHERE id_session = ?", (id_session,))
                    #self.db.conn.commit()
                    
                if not self.debug_mode:
                    print(f">>✅ Saved: {chest_name} ({player_name}) >{time_left_str}")
                else:
                    print(f">>✅ [SAVED] Record ID: {id_chest}")
                inserted += 1
                
            except Exception as e:
                print(f"❌ [ERROR] Insert failed: {e}")
                failed += 1

        # ✅ OPTIMIZATION: Final commit for remaining records
        if self.pending_commits > 0:
            try:
                self.db.conn.commit()
                if self.debug_mode:
                    print(f"[FINAL COMMIT] {self.pending_commits} records")
                self.pending_commits = 0
            except Exception as e:
                print(f"[ERROR] Final commit failed: {e}")

        # Summary
        print("\n" + "="*70)
        print(f"SAVE SUMMARY: ✅ {inserted} inserted")
        if skipped_duplicates > 0:
            print(f"  ⏭️  {skipped_duplicates} duplicates skipped")
        if failed > 0:
            print(f"  ❌ {failed} failed")
        print("="*70 + "\n")

        self.records = []
        return (inserted, skipped_duplicates, failed)

    # =====================================================================
    def run(self):
        """
        Main capture loop with proper termination control.
        FIXED: No more infinite loops - stops at target.
        """
        value = ""
        while True:
            value = input("\nTotal Chests to collect? ('-' to exit): ")
            if value.isdigit() or value == "-":
                break

        if value == "-":
            exit(0)

        maxClicks = int(value)
        print(f"\n[INFO] TARGET: Capture {maxClicks} chest(s)")
        
        # ✅ START TIMER
        self.session_start_time = time.time()
        start_datetime = datetime.now()
        #print(f"[INFO] Session started at: {start_datetime.strftime('%H:%M:%S')}\n")

        while True:
            
            # CRITICAL CHECK: Stop if target reached
            if self.totalClicks >= maxClicks:
                print("\n" + "="*70)
                print(f"✅ TARGET REACHED: {self.totalClicks}/{maxClicks} chests collected")
                print("="*70 + "\n")
                break

            # Capture screen
            print(f"\n>>>>> OCR processing {self.totalClicks+1}/{maxClicks}....")

            image_main = self.screen.get_screenshot(
                self.config.x1, self.config.y1, 
                self.config.x2, self.config.y2
            )
            image_main = self.screen.get_grayscale(numpy.array(image_main))
            capture_main = self.screen.ocr_core(image_main)

            image_time = self.screen.get_screenshot(
                self.config.time_x1, self.config.time_y1,
                self.config.time_x2, self.config.time_y2
            )
            capture_time = self.screen.ocr_time_specialized(image_time)

            capture = capture_main + "\n" + capture_time

            count = min(4, maxClicks - self.totalClicks)

            # Validate capture
            success = self.validate_capture(capture, count)

            if success and len(self.records) == 0:
                print(f"\n*** {self.totalClicks}/{maxClicks} chests saved. No more chests detected.")
                break

            # Error handling
            proceed = ""
            if not success:
                while True:
                    print("\n*** ERROR: Capture validation failed")
                    print(">>> [1] Capture again")
                    print(">>> [2] Save anyway")
                    print(">>> [3] Stop process")
                    print(">>> [4] Show captured text")
                    proceed = input("\n*** Choose [1/2/3/4]: ").strip()

                    if proceed == "4":
                        print("\n" + "="*70)
                        print("DEBUG: RAW TEXT")
                        print("="*70)
                        print(capture)
                        print("="*70 + "\n")
                        continue

                    if proceed in ("1", "2", "3"):
                        break

            if proceed == "3":
                print(f"\n*** Process stopped at {self.totalClicks}/{maxClicks}")
                break

            # Save records and track what happened
            records_found = len(self.records)
            inserted_count = 0
            skipped_count = 0
            
            if success or proceed == "2":
                inserted_count, skipped_count, failed_count = self.save_records()

            # Determine how many chests to click
            # LOGIC: Click only the ones that were actually INSERTED (not duplicates)
            if success and inserted_count > 0:
                clicks = min(inserted_count, maxClicks - self.totalClicks)
                moveX = [0, 3, -6, 6, -3, 0]
                hwndThis = pygetwindow.getActiveWindow()

                for j in range(clicks):
                    pyautogui.click(
                        x=int(self.config.mx) + moveX[j % len(moveX)],
                        y=int(self.config.my)
                    )
                    self.totalClicks += 1
                    time.sleep(int(self.clickWait) / 1000.0)
                    print(f"[CLICK] Collected {self.totalClicks}/{maxClicks}")

                hwndThis.activate()
                time.sleep(2 * int(self.clickWait) / 1000.0)
            
            # If all were duplicates but we validated them, count as "processed attempts"
            elif success and records_found > 0 and inserted_count == 0:
                # All records were duplicates - this chest batch was already collected
                # Increment counter to avoid infinite loop
                processed_attempts = min(records_found, maxClicks - self.totalClicks)
                self.totalClicks += processed_attempts
                print(f"\n[INFO] All records were duplicates - skipping clicks")
                print(f"[INFO] Progress: {self.totalClicks}/{maxClicks} (duplicate batch counted as attempt)\n")

            # Final check after clicks
            if self.totalClicks >= maxClicks:
                print("\n" + "="*70)
                print(f"✅ COMPLETED: {self.totalClicks}/{maxClicks} chests")
                print("="*70 + "\n")
                break
        
        # ✅ STOP TIMER
        self.session_end_time = time.time()
        end_datetime = datetime.now()
        
        # Calculate duration
        total_seconds = self.session_end_time - self.session_start_time
        duration_minutes = int(total_seconds // 60)
        duration_seconds = int(total_seconds % 60)
        
        # Calculate average time per chest
        #avg_seconds_per_chest = total_seconds / self.totalClicks if self.totalClicks > 0 else 0    

        # Cleanup
        self.player_def.save()
        if self.db:
            self.db.close()
            print("[INFO] Database closed")
            print(f"SESSION Total time:    {duration_minutes}m {duration_seconds}s")
            #print(f"Chests:        {self.totalClicks}")
            #print(f"Avg per chest: {avg_seconds_per_chest:.1f}s")

        if not success and proceed != "2":
            print("\n" + "*"*70)
            print("*** WARNING: PROCESS HAD ERRORS")
            print("*"*70 + "\n")
# TBChestCounter ----------------------------------------------------------------
parser = argparse.ArgumentParser()

parser.add_argument("--config", help="a separate configuration file that contains relevant processing paramters. these can be overridden by providing arguments", required="True")

parser.add_argument("--clan", help="specific clan name to use", default="")  # <-- AÑADIR

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

if args.clan:
    config.clan = args.clan
    print(f"[INFO] Clan override: using '{args.clan}' instead of '{config.clan}' from config")

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
