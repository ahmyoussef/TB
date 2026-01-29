# tb.py --
# 1. IMPORTS Y CONFIGURACIÓN GLOBAL ----------------------------------------------------------------------
from logging import captureWarnings
from pathlib import Path
import sys
import os
import re
import argparse
import shutil
import glob
import clipboard
import time
from datetime import datetime
from datetime import timedelta
from difflib import SequenceMatcher as SM
import cv2
import numpy
import easyocr

from PIL import ImageGrab
import pyautogui, sys
import pygetwindow

# ============================================================================
# ✅ NUEVA IMPORTACIÓN — DATABASE MANAGER
# ============================================================================
try:
    from TBDatabase_manager import TBDatabaseManager
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  WARNING: Database module not available: {str(e)}")
    print("⚠️  Running in TXT-only mode")
    DATABASE_AVAILABLE = False
    TBDatabaseManager = None
# ============================================================================

# ---------------- CHECK ABSOLUTE PATH END ---------------------------------------------------
# Archivos de log
LOG_CORRECTIONS = Path('../logs/ocr_debug/ocr_corrections.log')
LOG_MISSING_TIME = Path('../logs/ocr_debug/missing_timeleft.log')

class LanguageManager:
    """Gestor centralizado de idiomas que consulta la base de datos."""
    
    _instance = None
    _languages_cache = None
    _cache_timestamp = None
    CACHE_TIMEOUT = 300  # 5 minutos
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LanguageManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.db = None
    
    def set_database(self, db_manager):
        """Establecer referencia al gestor de base de datos."""
        self.db = db_manager
    
    def get_active_languages(self, force_refresh=False):
        """Obtener lista de idiomas activos desde la base de datos."""
        
        # Verificar cache
        current_time = time.time()
        if (not force_refresh and self._languages_cache and 
            self._cache_timestamp and 
            (current_time - self._cache_timestamp) < self.CACHE_TIMEOUT):
            return self._languages_cache
        
        if not self.db:
            return {'en': 'English'}
        
        try:
            languages = self.db.execute_raw_query("""
                SELECT code_language, name_language, is_default 
                FROM supported_languages 
                WHERE is_active = 1
                ORDER BY is_default DESC, name_language
            """)
            
            # Convertir a diccionario para fácil acceso
            lang_dict = {}
            default_lang = 'en'
            
            for lang in languages:
                code = lang['code_language']
                lang_dict[code] = {
                    'name': lang['name_language'],
                    'is_default': bool(lang['is_default'])
                }
                if lang['is_default']:
                    default_lang = code
            
            self._languages_cache = lang_dict
            self._cache_timestamp = current_time
            
            print(f"### [LANG MANAGER] Loaded {len(lang_dict)} active languages from DB")
            print(f"### [LANG MANAGER] Default language: {default_lang}")
            
            return lang_dict
            
        except Exception as e:
            print(f"⚠️  Error loading languages from DB: {e}")
            return {'en': {'name': 'English', 'is_default': True}}
    
    def is_language_active(self, language_code):
        """Verificar si un idioma está activo en la base de datos."""
        languages = self.get_active_languages()
        return language_code in languages
    
    def get_default_language(self):
        """Obtener el idioma por defecto de la base de datos."""
        languages = self.get_active_languages()
        for code, info in languages.items():
            if info.get('is_default'):
                return code
        return 'en'  # Fallback
    
    def get_language_name(self, language_code):
        """Obtener el nombre completo de un idioma."""
        languages = self.get_active_languages()
        if language_code in languages:
            return languages[language_code]['name']
        return f"Unknown ({language_code})"
    
    def refresh_cache(self):
        """Forzar refresco de la caché de idiomas."""
        self._languages_cache = None
        self._cache_timestamp = None
        return self.get_active_languages(force_refresh=True)

# Crear instancia global del gestor de idiomas
language_manager = LanguageManager()

# 2. CLASE TBConfig (CONFIGURACIÓN ESCALABLE) ------------------------------------------------------------

class TBConfig(object):
    """
    Clase para parsear y gestionar parámetros de archivo de configuración: config/config.cfg.
    Mejorada para manejar clanes de forma escalable y asegurar tipos de datos.
    """
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
            self.zip             = config_kvp.get('zip', '') #indica el clan activo
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
            # --------------------------------------------------------------------
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
            
            self.active_clan_name = self._get_active_clan_name(config_kvp)
            
            # Estructura escalable para clanes (Busca hasta 4 clanes)
            global clan1, clan2, clan3, clan4, pshellpath1, pshellpath2, pshellpath3, pshellpath4
            clip  = self.zip
            clan1 = self.clangui
            clan2 = self.clangui2
            clan3 = self.clangui3
            clan4 = self.clangui4
            pshellpath1 = self.pshellpath1
            pshellpath2 = self.pshellpath2
            pshellpath3 = self.pshellpath3
            pshellpath4 = self.pshellpath4
            
            
            
            print(f"### [CONFIG] zip = {self.zip}")
            print(f"### [CONFIG] clan (abbreviation) = {self.clan}")
            print(f"### [CONFIG] active_clan_name = {self.active_clan_name}")
        
    def _get_active_clan_name(self, config_kvp):
        """Determine active clan name based on zip value."""
        zip_value = config_kvp.get('zip', '').lower()
        
        if zip_value == 'c1':
            return config_kvp.get('clanname1', '')
        elif zip_value == 'c2':
            return config_kvp.get('clanname2', '')
        elif zip_value == 'c3':
            return config_kvp.get('clanname3', '')
        elif zip_value == 'c4':
            return config_kvp.get('clanname4', '')
        else:
            # Por defecto, usar clanname1
            return config_kvp.get('clanname1', '')
                            
#  3. BScreen: CLASES DE PANTALLA Y UTILIDADES OCR -----------------------------------------------------------------------------
class TBScreen(object):
    
    """ This class takes the screen capture and runs the OCR processing, and contains image processing functions """
    """Manejo de captura de pantalla, preprocesamiento y OCR."""
    
    def __init__(self, languages=['en']):
        """
        Initialize EasyOCR reader with multiple languages.
        
        Args:
            languages: List of language codes (e.g., ['en', 'es'])
        """
        # Mapeo de códigos de idioma a códigos EasyOCR
        ocr_lang_map = {
            'en': 'en',
            'es': 'es',
            'fr': 'fr',
            'de': 'de',
            'pt': 'pt',
            'ru': 'ru',
            'zh': 'ch_sim',  # Chino simplificado
            'ja': 'ja',      # Japonés
            'ko': 'ko'       # Coreano
        }
        
        # Convertir códigos a formato EasyOCR
        ocr_languages = []
        for lang in languages:
            if lang in ocr_lang_map:
                ocr_languages.append(ocr_lang_map[lang])
            else:
                print(f"### Warning: Language '{lang}' not supported by OCR, using 'en'")
                ocr_languages.append('en')
        
        # Siempre incluir inglés como fallback si no está en la lista
        if 'en' not in ocr_languages:
            ocr_languages.append('en')
        
        print(f"### Initializing EasyOCR with languages: {ocr_languages}")
        
        try:
            self.reader = easyocr.Reader(ocr_languages, gpu=False)
            print(f"### ✅ EasyOCR initialized successfully")
        except Exception as e:
            print(f"### ❌ Error initializing EasyOCR: {e}")
            print(f"### Falling back to English only")
            self.reader = easyocr.Reader(['en'], gpu=False)

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
    def ocr_core(self, img):
        """Extract text using EasyOCR (replaces Tesseract)"""
        # Convert PIL Image to numpy array if needed
        if hasattr(img, 'mode'):
            img = numpy.array(img)
        
        # Apply preprocessing
        if len(img.shape) == 3:
            img = self.get_grayscale(img)
        
        # Use EasyOCR
        results = self.reader.readtext(img, detail=0, paragraph=True)
        
        # Combine all results into single text
        text = "\n".join(results) if results else ""
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
        
        # Use EasyOCR with character whitelist in post-processing
        results = self.reader.readtext(img, detail=0, paragraph=False)
        
        # Combine results
        raw_text = " ".join(results) if results else ""
        
        # Post-processing: filter to allowed characters only
        allowed_chars = set('0123456789hms: ')
        filtered_text = ''.join(c for c in raw_text if c.lower() in allowed_chars)
        
        return filtered_text.strip()

# 4. TBFixOCR CLASE DE MODELADO DE DATOS Y LIMPIEZA OCR (Placeholders) ------------------------------------------------
# Estas clases se mantienen para modularidad, asumiendo que implementan la lógica de validación
# y carga de archivos CSV de forma robusta.
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
                    if fix_string == "":
                        continue
                    kvp = fix_string.split(",")

                    self.fixed[kvp[1].lower()] = kvp[0]
                    self.fix_ocr[kvp[1].lower()] = kvp[2]
        else:
            print("### No OCR Fix configration file")
# -------------------------------------------------------------------------------
    def fix(self, line1, line2):
        if self.fix_ocr.get(line1.lower()) == None:
            return ""
        elif self.fix_ocr[line1.lower()] == line2:
            return self.fixed.get(line1.lower())
        else:
            return ""

# TBPlayer ------------------------------------------------------------------------------------------------------
class TBPlayer(object):
    """
    Validates player names using multilingual patterns from database.
    
    CAMBIO PRINCIPAL: Ahora recibe ml_validator para limpiar prefijos multiidioma.
    """
    
    def __init__(self, player_file, ml_validator):
        """
        Initialize player validator with multilingual support.
        
        Args:
            player_file: Path to CSV file with player names and aliases
            ml_validator: TBMultilingualValidator instance
        """
        self.player_file = player_file
        self.player_set = set()
        self.player_kvp = {}
        self.player_set_changed = False
        self.ml_validator = ml_validator
        
        # Load players from CSV
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
        """Save updated player list to CSV file"""
        
        if self.player_set_changed and self.player_file:
            
            while True:
                print("----------------- New Player! ------------------")
                print("### Do you want to save him to the player-list ?\n")
                save = input("### <Enter/y> or <n> ? ")
                if len(save) == 0 or save == "y" or save == "n":
                    break
            
            if len(save) == 0 or save == "y":
                with open(self.player_file, 'w') as pfp:
                    
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
        """
        Validate player name using multilingual 'from' patterns.
        
        Args:
            player: Raw player string from OCR (e.g., "De: Torin" or "From: Torin")
            line: Line number for error reporting
            
        Returns:
            tuple: (success: bool, validated_player: str)
        """
        
        original_player = player
        success = True
        
        # NUEVO: Limpiar usando patrones multiidioma de la BD
        player = self.ml_validator.extract_field(player, 'from')
        
        # Limpiar separadores residuales
        player = re.sub(r'^[:;.]\s*', '', player).strip()
        
        print(f"### Player after cleanup: '{player}'")
        
        # Check if player is in the player set
        if player in self.player_set:
            print(f"### Player '{player}' found in player set")
            return success, player
        
        # Si no tiene prefijo "From:"/"De:" pero es un nombre válido
        if not player.lower().startswith("from") and not player.lower().startswith("de") and player in self.player_set:
            return success, player
        
        else:
            # Verificar si el jugador tiene un formato mal formado
            splitter = ""
            separators = [":", ";", ".", ","]
            
            # Buscar separadores
            for sep in separators:
                if sep in player:
                    splitter = sep
                    break
            
            if splitter:  # Si encontramos un separador, dividir
                try:
                    split_player = player.split(splitter, 1)
                    if len(split_player) > 1:
                        player = split_player[1].strip()
                        print(f"### Split player with '{splitter}': '{player}'")
                    else:
                        player = split_player[0].strip()
                except Exception as e:
                    print(f"*** ERROR splitting player '{player}' with separator '{splitter}': {e}")
                    pass
            
            # Handle OCR issues with player names
            if player.endswith('.'):
                player = player.replace('.', '')
            
            # Verificar si después de la limpieza está en la lista
            if player in self.player_set:
                print(f"### Player '{player}' found in player set after cleanup")
                return success, player
            
            # Player name not in players file or malformed by OCR
            print(f"### Player '{player}' not in player set, checking aliases...")
            
            # Attempt a fuzzy match
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
                player = best_string
                return success, player
            
            else:
                # Look in alias map
                tmp_player = self.player_kvp.get(player.lower())
                
                if tmp_player == None:  # Alias for this player is not defined
                    print("\n* ATTENTION: UNKNOWN OR NEW PLAYER")
                    print("- Press <Enter> if player '{}' is correct".format(player))
                    print("- Or type the correct 'Name/Alias' for the player")
                    print("- Or type '-' to abort the process!\n")
                    player_name = input("<Enter> or ['Name/Alias'] or ['-']: ").strip()
                    
                    if player_name == "-":
                        success = False
                        return success, player
                    else:
                        player_alias = player
                        
                        if len(player_name) > 0:
                            player = player_name
                        
                        if player not in self.player_set:
                            self.player_set_changed = True
                            self.player_set.add(player)
                        
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
                                success = False
                
                else:
                    print("\nFUZZY LOGIC: Player {}".format(player))
                    print("MAPPED TO  : Player {}".format(tmp_player))
                    player = tmp_player
        
        return success, player

# TBChest ------------------------------------------------------------------------------------------------------
class TBChest(object):
    """ This class parses CHEST configuration parameters and validates chest names captured by the OCR """
# ------------------------------------------------------------------------------------------------------
    def __init__(self, quality_file):

        self.quality_kvp = {}

        if quality_file:
            with open(quality_file) as qfp:
                for cmt, quality_line in enumerate(qfp):
                    kvp_string = quality_line.rstrip('\n')
                    kvp = kvp_string.split(",")
                    for player_alias in kvp[1:]:
                        self.quality_kvp[player_alias] = kvp[0]

# ------------------------------------------------------------------------------------------------------
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
    """Validates chest SOURCE using multilingual patterns from database"""
    
    def __init__(self, ml_validator):
        """
        Args:
            ml_validator: TBMultilingualValidator instance
        """
        self.ml_validator = ml_validator
    
    def validate(self, source, line):
        """
        Validate and clean source string using database patterns.
        Returns: (success: bool, cleaned_source: str)
        """
        success = True
        
        # NUEVO: Si ya viene limpio (sin prefijo), validar directamente
        if not self.ml_validator.match_keyword(source, 'source'):
            # Ya está limpio, solo aplicar correcciones
            source = self._apply_corrections(source)
            return True, source
        
        # Extraer el valor después del patrón "Source:", "Fuente:", etc.
        source_clean = self.ml_validator.extract_field(source, 'source')
        
        if not source_clean:
            print(f"\n*** ERROR: Could not extract source from '{source}' at line {line}")
            return False, source
        
        # Apply corrections
        source = self._apply_corrections(source_clean)
        
        return True, source
    
    def _apply_corrections(self, source):
        """Apply common OCR corrections to source string"""
        
        # Crypt corrections
        if source.endswith("Cr"):
            source += "ypt"
        elif source.endswith("Cry"):
            source += "pt"
        elif source.endswith("Cryp"):
            source += "t"
        
        # Chest corrections
        if source.endswith("Ch"):
            source += "est"
        elif source.endswith("Che"):
            source += "st"
        elif source.endswith("Ches"):
            source += "t"

        # Clan wealth
        if source.endswith("wea"):
            source += "lth"
        elif source.endswith("weal"):
            source += "th"
        elif source.endswith("wealt"):
            source += "h"

        # Monster
        if source.endswith("Mons"):
            source += "ter"
        elif source.endswith("Monst"):
            source += "er"
        elif source.endswith("Monste"):
            source += "r"

        # Citadel
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

        # Authority Rush tournament
        if source.endswith("tourna"):
            source += "ment"
        elif source.endswith("tournam"):
            source += "ent"
        elif source.endswith("tourname"):
            source += "nt"
        elif source.endswith("tournamen"):
            source += "t"

        # Bank                    
        if source.endswith("Ba"):
            source += "nk"
        elif source.endswith("Ban"):
            source += "k"
        
        # Capitalize common words
        source = source.replace("crypt", "Crypt")
        source = source.replace("chest", "Chest")
        source = source.replace("citadel", "Citadel")
        source = source.replace("monster", "Monster")
        source = source.replace("bank", "Bank")
        
        return source

# NEW MODIFICATION YOZAHM
# 2.5 CLASE TBTimeLeft (PARSEO Y CORRECCIÓN DE TIEMPO RESTANTE) ------------------------------------------
# --------------------------------------------------------------------------------------------------------
class TBTimeLeft:
    """
    Robust time extractor with multilingual prefix support.
    
    CAMBIO PRINCIPAL: Ahora usa ml_validator para limpiar prefijos multiidioma.
    """
    
    def __init__(self, log_dir="../logs/ocr_debug", batch_mode=False, ml_validator=None):
        """
        Initialize time extractor with multilingual support.
        
        Args:
            log_dir: Directory for debug logs
            batch_mode: Enable batch processing mode
            ml_validator: TBMultilingualValidator instance (optional)
        """
        self.max_hours = 19
        self.max_minutes = 59
        self.max_seconds = 59
        self.log_dir = log_dir
        self.batch_mode = batch_mode
        self.ml_validator = ml_validator
        
        import os
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.corrections_log = os.path.join(log_dir, "ocr_corrections.log")
        self.missing_log = os.path.join(log_dir, "missing_timeleft.log")
        
        # Universal time patterns (work for all languages)
        self.TIME_PATTERNS = [
            # 1. Full H M S pattern
            re.compile(r'(?P<h>\d{1,3})\s*[hH]\s*[:\s]?\s*(?P<m>\d{1,2})\s*[mM]\s*[:\s]?\s*(?P<s>\d{1,2})\s*[sS]?', re.IGNORECASE),
            # 2. H + M
            re.compile(r'(?P<h>\d{1,3})\s*[hH]\s*[:\s]?\s*(?P<m>\d{1,2})\s*[mM]?', re.IGNORECASE),
            # 3. M + S
            re.compile(r'(?P<m>\d{1,3})\s*[mM]\s*[:\s]?\s*(?P<s>\d{1,2})\s*[sS]?', re.IGNORECASE),
            # 4. Fallback generic
            re.compile(r'(?P<n1>\d{1,3})\D+(?P<n2>\d{1,2})(?:\D+(?P<n3>\d{1,2}))?'),
            # 5. Single number
            re.compile(r'^(?P<only>\d{1,3})$')
        ]
    
    def _log_correction(self, original, corrected, reason):
        """Log time corrections to file"""
        try:
            from datetime import datetime
            with open(self.corrections_log, "a", encoding="utf-8") as f:
                f.write(
                    f"{datetime.utcnow().isoformat()} | ORIGINAL={original!r} | "
                    f"CORRECTED={corrected!r} | REASON={reason}\n"
                )
        except:
            pass
    
    def _log_missing(self, context):
        """Log missing time values"""
        try:
            from datetime import datetime
            with open(self.missing_log, "a", encoding="utf-8") as f:
                f.write(f"{datetime.utcnow().isoformat()} | MISSING={context}\n")
        except:
            pass
    
    def extract(self, line):
        """
        Extract hours/minutes/seconds from OCR string with multilingual support.
        
        Args:
            line: Raw OCR line (e.g., "Quedan: 14 h 2 m" or "Time left: 14 h 2 m")
            
        Returns:
            tuple: (ok: bool, hours: int, minutes: int, seconds: int, raw_text: str)
        """
        
        raw_original = (line or "").strip()
        if not raw_original:
            print("*** WARNING: Time-left empty OCR line")
            self._log_missing("empty_time_line")
            return False, 0, 0, 0, "0 h : 0 m : 0 s"
        
        # NUEVO: Limpiar usando patrones multiidioma si están disponibles
        if self.ml_validator:
            # Eliminar prefijos: "Time left:", "Quedan:", "Temps restant:", etc.
            s = self.ml_validator.extract_field(raw_original, 'time_left')
        else:
            # Fallback: limpiar genéricamente (solo inglés)
            s = re.sub(r'(?i).*time\s*left[:\s]*', '', raw_original).strip()
        
        # Normalize Unicode characters
        s = s.replace('\u2212', '-').replace('\u2013', '-').replace('\u00A0', ' ')
        s = re.sub(r'[^\x00-\x7F]', ' ', s)
        
        # Normalize spaces around h/m/s
        s = re.sub(r'(\d+)\s*([hHmMsS])', r'\1\2 ', s)
        
        # Remove problematic characters except digits, h/m/s, spaces, colons
        s = re.sub(r'[^0-9hHmMsS:\s]', ' ', s)
        
        # Clean multiple spaces
        s = re.sub(r'\s+', ' ', s).strip()
        
        hours = minutes = seconds = 0
        matched = False
        
        # Apply extraction patterns in order of specificity
        for idx, pat in enumerate(self.TIME_PATTERNS):
            m = pat.search(s)
            if not m:
                continue
            
            matched = True
            groups = m.groupdict()
            
            # Extract H, M, S based on named groups
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
            
            # Extract generic values (n1, n2, n3)
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
            
            # Single number → assume minutes
            if groups.get("only"):
                try:
                    minutes = int(groups["only"])
                except:
                    minutes = 0
            
            raw_text = f"{hours} h : {minutes} m : {seconds} s"
            return True, hours, minutes, seconds, raw_text
        
        # Fallback: extract all digits and assume H M S or H M order
        if not matched:
            digits = re.findall(r'\d+', s)
            
            if len(digits) >= 2:
                hours = int(digits[0])
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
    
    def validate(self, hours, minutes, seconds, line_number=0, batch_mode=None):
        """
        Validate & normalize time-left values.
        
        Returns:
            tuple: (ok: bool, hours: int, minutes: int, seconds: int, user_corrected: bool)
        """
        
        if batch_mode is None:
            batch_mode = self.batch_mode
        
        user_corrected = False
        
        # Safe conversion to integers
        try:
            h = int(hours)
        except:
            h = 0
        try:
            m = int(minutes)
        except:
            m = 0
        try:
            s = int(seconds)
        except:
            s = 0
        
        # Round seconds
        if s >= 30:
            print(f"*** INFO: seconds {s} >=30 → add 1 minute")
            m += 1
            s = 0
        
        # Normalize minute overflow
        if m >= 60:
            print(f"*** INFO: normalizing minutes: {m} -> add hours")
            h += m // 60
            m = m % 60
        
        # OCR heuristic: 80-89 → subtract 80
        if 80 <= h <= 89:
            orig = h
            h = h - 80
            print(f"*** INFO: hours {orig} -> {h} (OCR misread fix 80-89)")
            self._log_correction(f"{orig} h", f"{h} h", "80-89 heuristic")
        
        # Clamp to valid values
        if h < 0:
            h = 0
        if m < 0:
            m = 0
        if s < 0:
            s = 0
        
        # Validate suspicious hour range (>= 20)
        if h >= 20:
            print(f"*** WARNING: Suspicious hours: {h}h {m}m (max expected: {self.max_hours}h)")
            
            if not batch_mode:
                while True:
                    print(f"\n*** Current: {h} h : {m} m")
                    print(f"*** Is this correct? (Enter to accept, or type: H M)")
                    user_input = input("*** > ").strip()
                    
                    if not user_input:
                        break
                    
                    parts = user_input.split()
                    if len(parts) == 2:
                        try:
                            nh = int(parts[0])
                            nm = int(parts[1])
                            if 0 <= nh <= self.max_hours and 0 <= nm <= self.max_minutes:
                                h, m = nh, nm
                                self._log_correction(f"{hours}h {minutes}m", f"{h}h {m}m", "user_manual")
                                return True, nh, nm, 0, True
                            else:
                                print(f"*** Values out of range 0–{self.max_hours}h / 0–{self.max_minutes}m")
                                continue
                        except:
                            print("*** Invalid input")
                            continue
                    else:
                        print("*** Invalid format. Please enter: H M (e.g., 7 24)")
                        continue
        
        # Final range validation
        if 0 <= h <= self.max_hours and 0 <= m <= self.max_minutes:
            return True, h, m, s, user_corrected
        
        # Out of range
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
        self.source_to_points = {}  # Para búsqueda rápida por source solamente
        self.no_score = set()
        self.chest_definitions = {}  # Para mapear nombre/source a definición completa

        if score_file:
            with open(score_file, encoding='utf-8') as sfp:
                for cmt, score_line in enumerate(sfp):
                    kvp_string = score_line.strip()
                    
                    # Saltar línea de encabezado si existe
                    if cmt == 0 and (kvp_string.lower().startswith('type') or 
                                     kvp_string.lower().startswith('chest')):
                        print(f"### Skipping header: {kvp_string}")
                        continue
                    
                    kvp = kvp_string.split(",")
                    
                    if len(kvp) >= 4:
                        # NUEVO FORMATO: Type,Name,Source,Points
                        chest_type = kvp[0].strip()
                        chest_name = kvp[1].strip()
                        chest_source = kvp[2].strip()
                        points = kvp[3].strip()
                        
                        # Guardar para búsqueda por nombre y source (clave combinada)
                        key = f"{chest_name.lower()}|{chest_source.lower()}"
                        self.score_kvp[key] = points
                        
                        # También guardar para búsqueda solo por source
                        self.source_to_points[chest_source.lower()] = points
                        
                        # Guardar definición completa
                        self.chest_definitions[key] = {
                            'type': chest_type,
                            'name': chest_name,
                            'source': chest_source,
                            'points': points
                        }
                        
                        print(f"### Loaded chest: {chest_name} | {chest_source} = {points} points")
                        
                    elif len(kvp) >= 2:
                        # FORMATO ANTIGUO: source,points (compatibilidad)
                        source = kvp[0].strip().lower()
                        points = kvp[1].strip()
                        
                        # Para compatibilidad, usar source como nombre también
                        key = f"{source}|{source}"
                        self.score_kvp[key] = points
                        self.source_to_points[source] = points
                        
                        print(f"### Loaded (legacy): {source} = {points} points")

        print(f"### Total chest definitions loaded: {len(self.score_kvp)}")

# ------------------------------------------------------------------------------------------------------
    def calculate(self, source, chest, player, line):
        # Primero, intentar el mapeo especial (bank, etc.)
        original_source = source
        original_chest = chest
        
        if source.lower() in self.convert_chest_to_source:
            switch_chest_and_source = True
            tmp_source = source.lower()
            source = chest
            if tmp_source.find("throne") > -1:
                chest = "Clash for the Throne tournament"
            else:
                chest = 'Bank'
            print(f"### Special mapping: {original_source} -> {source}, chest -> {chest}")

        score = "0"
        
        # Manejar Cursed Citadel Chest (caso especial)
        if chest == "Cursed Citadel Chest":
            split_source = source.split(" ")
            if len(split_source) >= 2:
                citadel_level = split_source[1]
                source = "Level " + citadel_level + " cursed Citadel"
                print(f"### Cursed Citadel detected: {original_source} -> {source}")

        print(f"### Calculating score for: Chest='{chest}', Source='{source}'")
        
        # ESTRATEGIA DE BÚSQUEDA:
        # 1. Primero intentar con combinación exacta Name|Source
        key_exact = f"{chest.lower()}|{source.lower()}"
        temp_score = self.score_kvp.get(key_exact)
        
        if temp_score is not None:
            print(f"### Found exact match: {key_exact} = {temp_score}")
            score = temp_score
        else:
            # 2. Intentar buscar solo por Source
            temp_score = self.source_to_points.get(source.lower())
            
            if temp_score is not None:
                print(f"### Found by source only: {source.lower()} = {temp_score}")
                score = temp_score
            else:
                # 3. Intentar variaciones comunes
                # Para cofres de ciudadela
                if "citadel" in source.lower() and "chest" in chest.lower():
                    # Intentar con "Elven Citadel Chest" o "Cursed Citadel Chest"
                    if "cursed" in source.lower():
                        citadel_chest = "Cursed Citadel Chest"
                    else:
                        citadel_chest = "Elven Citadel Chest"
                    
                    key_citadel = f"{citadel_chest.lower()}|{source.lower()}"
                    temp_score = self.score_kvp.get(key_citadel)
                    
                    if temp_score is not None:
                        print(f"### Found citadel variant: {key_citadel} = {temp_score}")
                        score = temp_score
                    else:
                        # Último intento: buscar cualquier cofre con este source
                        for key in self.score_kvp.keys():
                            if f"|{source.lower()}" in key:
                                temp_score = self.score_kvp[key]
                                print(f"### Found by source in key: {key} = {temp_score}")
                                score = temp_score
                                break
        
        if score == "0":
            print(f"*** Warning at line {line}: No score found for Player:{player}, Chest:{original_chest}, Source:{original_source}")
            self.no_score.add(f"{original_chest}|{original_source}")

        return score

# ------------------------------------------------------------------------------------------------------
    def print_no_scores(self):
        if len(self.no_score) > 0:
            print("\n*** Warning: The following chest types have no score assigned:")
            for chest_source in sorted(self.no_score):
                print(f"  - {chest_source}")
                
class TBMultilingualValidator:
    """
    Validador multiidioma que usa patrones OCR de la base de datos.
    Carga dinámicamente las variaciones de palabras clave desde ocr_language_patterns.
    """
    
    def __init__(self, db, language_code='en'):
        self.db = db
        self.language_code = language_code
        self.patterns = {}
        self.loaded = False
        
        print(f"\n### [ML-VALIDATOR] Initializing for language: {language_code}")
        
        if db:
            self._load_patterns_from_db()
        else:
            print(f"### [ML-VALIDATOR] No database available, using hardcoded fallback")
            self._load_default_patterns()
    
    def _load_patterns_from_db(self):
        """Cargar patrones - ¡Ahora simple porque los tipos son universales!"""
        try:
            import json
            
            # ¡SIMPLE! Buscamos siempre los mismos tipos
            patterns_data = self.db.execute_raw_query("""
                SELECT keyword_type, keyword_variations 
                FROM ocr_language_patterns 
                WHERE language_code = ?
                ORDER BY keyword_type
            """, (self.language_code,))
            
            if not patterns_data:
                print(f"### [ML-VALIDATOR] ⚠️ No patterns found for '{self.language_code}'")
                self._load_default_patterns()
                return
            
            for row in patterns_data:
                keyword_type = row['keyword_type']  # 'from', 'source', 'time_left'
                variations_json = row['keyword_variations']
                
                try:
                    variations = json.loads(variations_json)
                    self.patterns[keyword_type] = variations
                    print(f"### [ML-VALIDATOR] ✅ Loaded '{keyword_type}': {len(variations)} variations")
                except json.JSONDecodeError as e:
                    print(f"### [ML-VALIDATOR] ⚠️ Invalid JSON for '{keyword_type}': {e}")
                    continue
            
            self.loaded = True
            print(f"### [ML-VALIDATOR] ✅ Loaded {len(self.patterns)} pattern types")
            
        except Exception as e:
            print(f"### [ML-VALIDATOR] ❌ Error loading patterns: {e}")
            self._load_default_patterns()
    
    def _load_default_patterns(self):
        """Patrones hardcoded como fallback si falla la BD"""
        
        if self.language_code == 'es':
            self.patterns = {
                'from': ['De', 'D e', 'Desde'],
                'source': ['Fuente', 'Fuen te', 'uente'],
                'time_left': ['Tiempo restante', 'Tiemp o restante', 'Tiempo']
            }
        elif self.language_code == 'fr':
            self.patterns = {
                'from': ['De', 'D e'],
                'source': ['Source', 'S ource', 'ource'],
                'time_left': ['Temps restant', 'Temps', 'Temp s restant']
            }
        elif self.language_code == 'de':
            self.patterns = {
                'from': ['Von', 'V on'],
                'source': ['Quelle', 'Q uelle', 'uelle'],
                'time_left': ['Verbleibende Zeit', 'Zeit übrig', 'Zeit']
            }
        elif self.language_code == 'pt':
            self.patterns = {
                'from': ['De', 'D e'],
                'source': ['Fonte', 'F onte', 'onte'],
                'time_left': ['Tempo restante', 'Temp o restante', 'Tempo']
            }
        elif self.language_code == 'ru':
            self.patterns = {
                'from': ['От', 'О т'],
                'source': ['Источник', 'Исто чник'],
                'time_left': ['Осталось времени', 'Время', 'Врем я']
            }
        else:  # English (default)
            self.patterns = {
                'from': ['From', 'Fr om', 'F rom', 'rom'],
                'source': ['Source', 'S ource', 'ource', 'urce'],
                'time_left': ['Time left', 'Time lef t', 'ime left', 'Time']
            }
        
        self.loaded = True
        print(f"### [ML-VALIDATOR] Using hardcoded fallback patterns for: {self.language_code}")
    
    def match_keyword(self, text, keyword_type):
        """Verificar si el texto contiene alguna variación de la palabra clave"""
        if keyword_type not in self.patterns:
            return False
        
        text_lower = text.lower()
        
        for pattern in self.patterns[keyword_type]:
            pattern_lower = pattern.lower()
            
            # Buscar patrón seguido de delimitadores típicos (: ; .)
            # o al inicio del texto
            regex_patterns = [
                # Patrón con delimitador después (más común)
                rf'\b{re.escape(pattern_lower)}\s*[:;.]\s*',
                # Patrón al inicio seguido de espacio y mayúscula (menos común)
                rf'^{re.escape(pattern_lower)}\s+[A-Z]',
            ]
            
            for regex in regex_patterns:
                if re.search(regex, text_lower):
                    return True
        
        return False
    
    def extract_field(self, text, keyword_type):
        """Extraer el valor después de la palabra clave"""
        if keyword_type not in self.patterns:
            return text.strip()
        
        import re
        
        for pattern in self.patterns[keyword_type]:
            pattern_escaped = re.escape(pattern)
            match = re.search(rf'{pattern_escaped}\s*[:;.]?\s*(.+)', text, re.IGNORECASE)
            
            if match:
                extracted = match.group(1).strip()
                return extracted
        
        return text.strip()
    
    def get_patterns(self, keyword_type):
        """Obtener lista de patrones para un tipo de keyword"""
        return self.patterns.get(keyword_type, [])
    
    def is_loaded(self):
        """Verificar si los patrones se cargaron correctamente"""
        return self.loaded
    
    def get_all_patterns(self):
        """Obtener diccionario completo de patrones"""
        return self.patterns.copy()

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
    """Main class for capturing chest information from the TB Gift screen"""
    
    # ========================================================================
    # TBMultilingualValidator - CLASE INTERNA CORREGIDA
    # ========================================================================
    class TBMultilingualValidator:
        """
        Validador multiidioma SIMPLIFICADO con tipos universales
        """
        
        def __init__(self, db, language_code='en'):
            self.db = db
            self.language_code = language_code
            self.patterns = {}
            self.loaded = False
            
            print(f"\n### [ML-VALIDATOR] Initializing for language: {language_code}")
            
            if db:
                self._load_patterns_from_db()
            else:
                print(f"### [ML-VALIDATOR] No database available, using hardcoded fallback")
                self._load_default_patterns()
        
        def _load_patterns_from_db(self):
            """Cargar patrones desde BD - TIPOS UNIVERSALES"""
            try:
                import json
                
                # Consulta SIMPLE - mismos tipos para todos los idiomas
                patterns_data = self.db.execute_raw_query("""
                    SELECT keyword_type, keyword_variations 
                    FROM ocr_language_patterns 
                    WHERE language_code = ?
                    ORDER BY keyword_type
                """, (self.language_code,))
                
                if not patterns_data:
                    print(f"### [ML-VALIDATOR] ⚠️ No patterns found for '{self.language_code}' in DB")
                    self._load_default_patterns()
                    return
                
                for row in patterns_data:
                    keyword_type = row['keyword_type']  # 'from', 'source', 'time_left'
                    variations_json = row['keyword_variations']
                    
                    try:
                        variations = json.loads(variations_json)
                        self.patterns[keyword_type] = variations
                        print(f"### [ML-VALIDATOR] ✅ Loaded '{keyword_type}': {len(variations)} variations")
                    except json.JSONDecodeError as e:
                        print(f"### [ML-VALIDATOR] ⚠️ Invalid JSON for '{keyword_type}': {e}")
                        continue
                
                # Verificar patrones esenciales
                essential_types = ['from', 'source']
                missing_types = [t for t in essential_types if t not in self.patterns]
                
                if missing_types:
                    print(f"### [ML-VALIDATOR] ⚠️ Missing types: {missing_types}, adding defaults")
                    for missing_type in missing_types:
                        self.patterns[missing_type] = self._get_default_patterns(missing_type)
                
                self.loaded = True
                print(f"### [ML-VALIDATOR] ✅ Loaded {len(self.patterns)} pattern types")
                
            except Exception as e:
                print(f"### [ML-VALIDATOR] ❌ Error loading patterns: {e}")
                import traceback
                traceback.print_exc()
                self._load_default_patterns()
        
        def _get_default_patterns(self, keyword_type):
            """Obtener patrones por defecto"""
            defaults = {
                'en': {
                    'from': ['From', 'Fr om', 'F rom', 'rom'],
                    'source': ['Source', 'S ource', 'ource', 'urce'],
                    'time_left': ['Time left', 'Time lef t', 'ime left']
                },
                'es': {
                    'from': ['De', 'D e', 'Desde'],
                    'source': ['Fuente', 'Fuen te', 'uente'],
                    'time_left': ['Quedan', 'Tiempo restante', 'Tiemp o', 'quedan']
                }
            }
            
            if self.language_code in defaults and keyword_type in defaults[self.language_code]:
                return defaults[self.language_code][keyword_type]
            elif keyword_type in defaults['en']:
                return defaults['en'][keyword_type]
            return []
        
        def _load_default_patterns(self):
            """Cargar patrones por defecto"""
            if self.language_code == 'es':
                self.patterns = {
                    'from': ['De', 'D e', 'Desde'],
                    'source': ['Fuente', 'Fuen te', 'uente'],
                    'time_left': ['Quedan', 'Tiempo restante', 'Tiemp o', 'quedan']
                }
            else:  # English default
                self.patterns = {
                    'from': ['From', 'Fr om', 'F rom', 'rom'],
                    'source': ['Source', 'S ource', 'ource', 'urce'],
                    'time_left': ['Time left', 'Time lef t', 'ime left']
                }
            
            self.loaded = True
            print(f"### [ML-VALIDATOR] Using default patterns for: {self.language_code}")
        
        # def match_keyword(self, text, keyword_type):
        #     """Verificar si el texto contiene la palabra clave"""
        #     if keyword_type not in self.patterns:
        #         return False
            
        #     text_lower = text.lower()
        #     for pattern in self.patterns[keyword_type]:
        #         if pattern.lower() in text_lower:
        #             return True
        #     return False
        def match_keyword(self, text, keyword_type):
            """Verificar si el texto contiene alguna variación de la palabra clave"""
            if keyword_type not in self.patterns:
                return False
            
            import re
            text_lower = text.lower()
            
            for pattern in self.patterns[keyword_type]:
                pattern_lower = pattern.lower()
                
                # Buscar patrón seguido de delimitadores típicos (: ; .)
                regex_patterns = [
                    rf'\b{re.escape(pattern_lower)}\s*[:;.]\s*',
                    rf'^{re.escape(pattern_lower)}\s+[A-Z]',
                ]
                
                for regex in regex_patterns:
                    if re.search(regex, text_lower):
                        return True
            
            return False
        
        def extract_field(self, text, keyword_type):
            """Extraer valor después de la palabra clave"""
            if keyword_type not in self.patterns:
                return text.strip()
            
            import re
            for pattern in self.patterns[keyword_type]:
                pattern_escaped = re.escape(pattern)
                match = re.search(rf'{pattern_escaped}\s*[:;.]?\s*(.+)', text, re.IGNORECASE)
                if match:
                    extracted = match.group(1).strip()
                    # Limpiar separadores residuales
                    extracted = re.sub(r'^[:;.]\s*', '', extracted).strip()
                    return extracted
            
            return text.strip()
        
        def get_patterns(self, keyword_type):
            """Obtener lista de patrones"""
            return self.patterns.get(keyword_type, [])
        
        def is_loaded(self):
            return self.loaded
        
        def debug_patterns(self):
            """Mostrar patrones para debugging"""
            print(f"\n{'='*60}")
            print(f"[ML-VALIDATOR DEBUG] Language: {self.language_code}")
            print(f"{'='*60}")
            for keyword_type, patterns in self.patterns.items():
                print(f"  {keyword_type}: {patterns}")
            print(f"{'='*60}\n")
    
    # ========================================================================
    # __init__ de TBCapture
    # ========================================================================
    def __init__(self, config, args):
        """Inicializar TBCapture con soporte multiidioma"""
        
        # ============================================================
        # SECCIÓN 1: Variables básicas
        # ============================================================
        self.processing_datetime = datetime.now().strftime("%Y-%m-%d %H.%M.%S")
        self.debug_mode = args.verbose
        self.clickWait = args.clickWait
        self.config = config
        
        # Idioma del juego
        self.game_language = args.language if hasattr(args, 'language') else 'en'
        print(f"\n### [LANGUAGE] Game language: {self.game_language}")
        
        print(f"\n### [ACTIVE CLAN] zip = {config.zip}")
        print(f"### [ACTIVE CLAN] Abbreviation: '{config.clan}'")
        
        # ============================================================
        # SECCIÓN 2: Base de datos (MOVER AQUÍ - antes era después)
        # ============================================================
        self.db_enabled = False
        self.clan_id = None
        self.session_id = None
        
        if DATABASE_AVAILABLE:
            try:
                self.db = db  # Usar instancia global
                
                # Buscar clan
                clan_data = self.db.get_clan_by_abbr(config.clan)
                if not clan_data:
                    self.clan_id = self.db.get_or_create_clan(config.active_clan_name, config.clan)
                else:
                    self.clan_id = clan_data['id_clan']
                
                print(f"✅ Using clan ID: {self.clan_id}")
                
                # Crear sesión
                self.session_id = self.db.create_session(self.clan_id)
                self.db_enabled = True
                print(f"✅ Database session created: {self.session_id}")
                
            except Exception as e:
                print(f"⚠️ Error accessing database: {str(e)}")
                self.db_enabled = False
        else:
            print("⚠️ Database module not available")
        
        # ============================================================
        # SECCIÓN 3: Validador multiidioma (MOVER AQUÍ - antes era después)
        # ============================================================
        if self.db_enabled and hasattr(self, 'db'):
            self.ml_validator = self.TBMultilingualValidator(self.db, self.game_language)
            print(f"### [ML-VALIDATOR] Created with database for '{self.game_language}'")
        else:
            self.ml_validator = self.TBMultilingualValidator(None, self.game_language)
            print(f"### [ML-VALIDATOR] Created with fallback for '{self.game_language}'")
        
        # Mostrar patrones si debug
        if self.debug_mode:
            self.ml_validator.debug_patterns()
        
        # ============================================================
        # SECCIÓN 4: Instancias de validadores (CON ml_validator)
        # ============================================================
        # ✅ CORREGIDO: Ahora pasamos ml_validator
        self.source_def = TBSource(self.ml_validator)
        self.player_def = TBPlayer(config.player_file, self.ml_validator)
        self.time_left_def = TBTimeLeft(ml_validator=self.ml_validator)
        self.chest_def = TBChest(config.quality_file)
        self.screen = TBScreen(languages=[self.game_language, 'en'])
        self.fix_ocr_def = TBFixOCR(config.fix_ocr_file)
        
        print(f"### [VALIDATORS] All validators initialized")
        
        # ============================================================
        # SECCIÓN 5: Archivos de salida (sin cambios)
        # ============================================================
        workfile = config.working_dir + '/TB_Capture_Clean'
        if len(config.clan) > 0:
            workfile += '_' + config.clan
        workfile += '_' + self.processing_datetime + '.txt'
        
        capturefile = config.working_dir + '/TB_Capture_RAW'
        if len(config.clan) > 0:
            capturefile += '_' + config.clan
        capturefile += '_' + self.processing_datetime + '.txt'
        
        self.wfile = open(workfile, 'w')
        self.sfile = open(config.datafile, 'a')
        self.tfile = open(config.totalfile, 'a')
        self.cfile = open(capturefile, 'w')
        
        self.records = list()
        self.maxClicks = 0
        self.totalClicks = 0
        self.user_choice = None
    
    # ========================================================================
    # parse_combined_line - MÉTODO NUEVO
    # ========================================================================
    def parse_combined_line(self, text):
        """
        Parsear líneas combinadas (chest + player + source en una línea)
        """
        import re
        
        print(f"### [PARSER] Parsing: '{text}'")
        
        # Obtener patrones
        from_patterns = self.ml_validator.get_patterns('from')
        source_patterns = self.ml_validator.get_patterns('source')
        
        if not from_patterns or not source_patterns:
            print(f"### [WARNING] No patterns loaded")
            return text.strip(), "", ""
        
        # Pre-procesar texto
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Corregir "De: De Jugador" → "De: Jugador"
        for from_pat in from_patterns:
            pattern = rf'({re.escape(from_pat)}\s*[:;.]?\s*){re.escape(from_pat)}\s*[:;.]?\s*'
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, r'\1', text, flags=re.IGNORECASE)
                print(f"### [FIX] Fixed duplicate '{from_pat}'")
        
        # Asegurar espacio después de ':'
        text = re.sub(r'([^:\s]):([^\s])', r'\1: \2', text)
        
        print(f"### [PARSER] Cleaned: '{text}'")
        
        # Buscar patrones
        from_match = None
        source_match = None
        
        for pattern in from_patterns:
            regex = rf'\b{re.escape(pattern)}\b\s*[:;.]?\s*'
            match = re.search(regex, text, re.IGNORECASE)
            if match:
                from_match = match
                break
        
        for pattern in source_patterns:
            regex = rf'\b{re.escape(pattern)}\b\s*[:;.]?\s*'
            match = re.search(regex, text, re.IGNORECASE)
            if match:
                source_match = match
                break
        
        chest = player = source = ""
        
        # Caso 1: Ambos patrones encontrados
        if from_match and source_match:
            if from_match.start() < source_match.start():
                # Formato: Chest [De:] Player [Fuente:] Source
                chest = text[:from_match.start()].strip()
                player_raw = text[from_match.end():source_match.start()].strip()
                source_raw = text[source_match.end():].strip()
            else:
                # Formato: Chest [Fuente:] Source [De:] Player
                chest = text[:source_match.start()].strip()
                source_raw = text[source_match.end():from_match.start()].strip()
                player_raw = text[from_match.end():].strip()
            
            player = self.ml_validator.extract_field(player_raw, 'from')
            source = self.ml_validator.extract_field(source_raw, 'source')
            
            print(f"### [PARSER] Both: Chest='{chest}', Player='{player}', Source='{source}'")
            return chest, player, source
        
        # Caso 2: Solo 'from'
        elif from_match:
            chest = text[:from_match.start()].strip()
            player_raw = text[from_match.end():].strip()
            player = self.ml_validator.extract_field(player_raw, 'from')
            
            print(f"### [PARSER] Only from: Chest='{chest}', Player='{player}'")
            return chest, player, source
        
        # Caso 3: Solo 'source'
        elif source_match:
            chest = text[:source_match.start()].strip()
            source_raw = text[source_match.end():].strip()
            source = self.ml_validator.extract_field(source_raw, 'source')
            
            print(f"### [PARSER] Only source: Chest='{chest}', Source='{source}'")
            return chest, player, source
        
        # Caso 4: Dividir por ':'
        elif ':' in text:
            parts = [p.strip() for p in text.split(':')]
            if len(parts) >= 3:
                chest = parts[0]
                player = self.ml_validator.extract_field(parts[1], 'from')
                source_raw = ':'.join(parts[2:])
                source = self.ml_validator.extract_field(source_raw, 'source')
                
                print(f"### [PARSER] Colon split: Chest='{chest}', Player='{player}', Source='{source}'")
                return chest, player, source
        
        # Caso 5: Fallback
        chest = text
        print(f"### [PARSER] Fallback: returning as chest only")
        return chest, player, source
    
    # ========================================================================
    # validate_capture - MÉTODO PRINCIPAL CORREGIDO
    # ========================================================================
    def validate_capture(self, capture, count):
        """Validate merged capture (main + time region)"""
        import re
        
        success = True
        self.records = []
        
        # Log raw capture
        self.cfile.write(f"--------------- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} --------------------------\n")
        self.cfile.write(capture + "\n")
        self.cfile.flush()
        
        print("\n" + "="*60)
        print("CAPTURED TEXT (merged chest+time):")
        print("="*60)
        print(capture)
        print("="*60 + "\n")
        
        # Normalize input
        lines = [x.strip() for x in capture.split("\n") if x.strip()]
        print(f"### Lines to process: {lines}")
        
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
        
        while i < total and records_found < count:
            text = lines[i]
            print(f"\n### [LINE {i+1}/{total}] Processing: '{text}'")
            
            # Detectar si es línea combinada
            text_lower = text.lower()
            has_from = self.ml_validator.match_keyword(text, 'from')
            has_source = self.ml_validator.match_keyword(text, 'source')
            has_multiple = (has_from or has_source)
            
            print(f"### [DETECT] Has from: {has_from}, Has source: {has_source}, Multiple: {has_multiple}")
            
            # PROCESAR LÍNEA COMBINADA
            if has_multiple and (chest is None or player is None or source is None):
                print(f"### [INFO] Parsing as combined line")
                parsed_chest, parsed_player, parsed_source = self.parse_combined_line(text)
                
                if chest is None and parsed_chest:
                    chest = parsed_chest
                if player is None and parsed_player:
                    player = parsed_player
                if source is None and parsed_source:
                    source = parsed_source
                
                print(f"### [PARSED] Chest: '{chest}', Player: '{player}', Source: '{source}'")
                
                # Buscar tiempo en siguiente línea
                if time_left is None and i + 1 < total:
                    next_line = lines[i + 1]
                    if re.search(r'\d', next_line) and (re.search(r'[hm]', next_line.lower()) or ':' in next_line):
                        ok_ex, h, mnt, sec, raw_time = self.time_left_def.extract(next_line)
                        if ok_ex:
                            ok_v, hcorr, mcorr, scorr, usercorr = self.time_left_def.validate(h, mnt, sec, i+1)
                            if ok_v:
                                time_left = f"{hcorr} h : {mcorr} m"
                                print(f"### [TIME] Found: {time_left}")
                                i += 1  # Saltar línea de tiempo
                
                i += 1
                
            else:
                # PROCESAMIENTO LÍNEA POR LÍNEA (original)
                print(f"### [INFO] Processing as separate line")
                
                if chest is None and not has_from and not has_source and "time" not in text_lower:
                    chest = text
                    print(f"### [FIELD] Chest set: '{chest}'")
                
                elif has_from and player is None:
                    player_raw = self.ml_validator.extract_field(text, 'from')
                    if player_raw:
                        player = player_raw
                        print(f"### [FIELD] Player set: '{player}'")
                
                elif has_source and source is None:
                    source_raw = self.ml_validator.extract_field(text, 'source')
                    if source_raw:
                        source = source_raw
                        print(f"### [FIELD] Source set: '{source}'")
                
                elif time_left is None:
                    # Verificar si es tiempo
                    if re.search(r'\d', text_lower) and (re.search(r'[hm]', text_lower) or ':' in text_lower):
                        ok_ex, h, mnt, sec, raw_time = self.time_left_def.extract(text)
                        if ok_ex:
                            ok_v, hcorr, mcorr, scorr, usercorr = self.time_left_def.validate(h, mnt, sec, i)
                            if ok_v:
                                time_left = f"{hcorr} h : {mcorr} m"
                                print(f"### [TIME] Found: {time_left}")
                            else:
                                time_left = "0 h : 0 m"
                                print(f"### [TIME] Using default: {time_left}")
                
                i += 1
            
            # VERIFICAR Y GUARDAR REGISTRO COMPLETO
            if chest and player and source and time_left:
                print(f"### [COMPLETE] All fields found, validating...")
                
                # Validar jugador
                player_success, validated_player = self.player_def.validate(player, i)
                if not player_success:
                    print(f"### [ERROR] Player validation failed: '{player}'")
                    chest = player = source = time_left = None
                    continue
                
                # Validar fuente
                source_success, validated_source = self.source_def.validate(source, i)
                if not source_success:
                    print(f"### [ERROR] Source validation failed: '{source}'")
                    chest = player = source = time_left = None
                    continue
                
                # Guardar registro
                self.records.append([chest, validated_player, time_left, validated_source])
                records_found += 1
                
                print(f"### [SUCCESS] Record saved: {records_found}/{count}")
                print(f"    Chest:  {chest}")
                print(f"    Player: {validated_player}")
                print(f"    Source: {validated_source}")
                print(f"    Time:   {time_left}")
                
                # Resetear para siguiente registro
                chest = player = source = time_left = None
        
        # MANEJO DE RESULTADOS
        if records_found == 0:
            print("\n### [ERROR] No chests found!")
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
                
                if ans in ("1", "2", "3"):
                    self.user_choice = ans
                    break
            
            if ans == "3":
                return False
            if ans == "2":
                return True
            if ans == "1":
                return False
        
        print(f"\n### [SUMMARY] Records validated: {records_found}/{count}")
        return True
    
    # ========================================================================
    # MÉTODOS AUXILIARES (sin cambios)
    # ========================================================================
    def _calculate_collection_date(self, time_left_str):
        """Calculate collection_date (obtained_at)"""
        from datetime import datetime, timedelta
        import re
        
        TOTAL_CHEST_DURATION = timedelta(hours=19, minutes=59, seconds=59)
        
        try:
            time_left_str_clean = time_left_str.lower().replace(' ', '')
            patterns = [
                r'(\d+)h[:]?(\d+)m',
                r'(\d+)[h:]\s*(\d+)m?',
                r'^(\d+)[h:]?$',
            ]
            
            hours = minutes = 0
            for pattern in patterns:
                match = re.search(pattern, time_left_str_clean)
                if match:
                    if len(match.groups()) >= 2:
                        hours = int(match.group(1))
                        minutes = int(match.group(2))
                    else:
                        hours = int(match.group(1))
                        minutes = 0
                    break
            
            time_left_delta = timedelta(hours=hours, minutes=minutes)
            time_held_delta = TOTAL_CHEST_DURATION - time_left_delta
            
            if time_held_delta.total_seconds() < 0:
                time_held_delta = timedelta(seconds=0)
            
            obtained_at = datetime.now() - time_held_delta
            return obtained_at.strftime("%Y-%m-%d %H:%M:%S")
            
        except Exception as e:
            print(f"### [WARNING] Error calculating collection_date: {e}")
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def save_roi_image(self, image, roi_type, capture_index=None):
        """Save ROI image for visual logging"""
        try:
            import os
            import cv2
            import numpy
            from pathlib import Path
            
            log_dir = Path('..') / 'data' / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            if capture_index is None:
                capture_index = self.totalClicks + 1
            
            filename = f"{timestamp}_{capture_index:03d}_{roi_type}.png"
            filepath = log_dir / filename
            
            if hasattr(image, 'mode'):
                image = numpy.array(image)
            
            cv2.imwrite(str(filepath), image)
            
            if self.debug_mode:
                print(f"### Saved ROI image: {filename}")
                
        except Exception as e:
            if self.debug_mode:
                print(f"### Warning: Failed to save ROI image: {e}")
    
    def save_records(self):
        """Save records to TXT files AND database"""
        index = 0
        rows = list()
        
        print(f"\n### Starting save_records() - {len(self.records)} records")
        
        while index < len(self.records):
            chest_name = self.records[index][0]
            player_name = self.records[index][1]
            time_left_clean = self.records[index][2]
            source_name = self.records[index][3]
            
            # Construir strings para TXT
            chest_txt = chest_name
            player_txt = "From : " + player_name
            source_txt = "Source : " + source_name
            time_txt = "Time left : " + time_left_clean
            
            print("\n" + "-"*55)
            print(f"{chest_txt}")
            print(f"{player_txt}")
            print(f"{source_txt}")
            print(f"{time_txt}")
            print("-"*55)
            
            rows.append(chest_txt)
            rows.append(player_txt)
            rows.append(source_txt)
            rows.append(time_txt)
            
            # Database save
            if self.db_enabled and self.db:
                try:
                    print(f"\n### [DB {index+1}/{len(self.records)}] Processing chest")
                    print(f"    [DB] Chest: '{chest_name}'")
                    print(f"    [DB] Source: '{source_name}'")
                    print(f"    [DB] Player: '{player_name}'")
                    print(f"    [DB] Language: '{self.game_language}'")
                    
                    # Calcular obtained_at
                    obtained_at = self._calculate_collection_date(time_left_clean)
                    print(f"    [DB] Time left: {time_left_clean}")
                    print(f"    [DB] Calculated obtained_at: {obtained_at}")
                    
                    # Get or create player
                    player_data = self.db.get_player_by_name(player_name, self.clan_id)
                    if not player_data:
                        player_data = self.db.get_player_by_alias(player_name, self.clan_id)
                    
                    if not player_data:
                        print(f"    [DB] Creating new player: '{player_name}'")
                        player_id = self.db.create_player(player_name, self.clan_id)
                    else:
                        player_id = player_data['id_player']
                    
                    # Get chest definition - usar la función existente get_chest_by_translation
                    print(f"    [DB] Searching chest definition: LANG {self.game_language} NAME CHEST {chest_name} - SOURCE {source_name} ")
                    
                    chest_def = self.db.get_chest_by_translation(chest_name, source_name, self.game_language)
                    
                    if not chest_def:
                        print(f"    [DB] No chest definition found in '{self.game_language}'")
                        
                        # Intentar buscar en inglés como fallback
                        if self.game_language != 'en':
                            print(f"    [DB] Trying English fallback...")
                            chest_def = self.db.get_chest_by_translation(chest_name, source_name, 'en')
                            if chest_def:
                                print(f"    [DB] Found chest definition in English fallback")
                    
                    if not chest_def:
                        # Último intento: búsqueda flexible por palabras clave
                        print(f"    [DB] Trying keyword search...")
                        
                        # Preparar palabras clave (eliminar palabras comunes)
                        common_words = ['de', 'del', 'la', 'el', 'las', 'los', 'y', 'e', 'o', 'u']
                        keywords = []
                        
                        # Extraer palabras del nombre del cofre
                        chest_words = chest_name.lower().split()
                        for word in chest_words:
                            if word not in common_words and len(word) > 2:
                                keywords.append(word)
                        
                        # Extraer palabras de la fuente
                        source_words = source_name.lower().split()
                        for word in source_words:
                            if word not in common_words and len(word) > 2:
                                keywords.append(word)
                        
                        print(f"    [DB] Keywords to search: {keywords}")
                        
                        # Buscar por cada palabra clave
                        for keyword in keywords:
                            try:
                                result = self.db.execute_raw_query("""
                                    SELECT cs.id_score, cs.code_chest, cs.base_point_value,
                                        cdt.name_chest, cdt.source_chest 
                                    FROM chest_score cs
                                    JOIN chest_def_translations cdt ON cs.id_score = cdt.id_score
                                    JOIN supported_languages sl ON cdt.id_language = sl.id_language
                                    WHERE (cdt.name_chest LIKE ? OR cdt.source_chest LIKE ?)
                                    AND sl.code_language IN (?, 'en')
                                    LIMIT 1
                                """, (f"%{keyword}%", f"%{keyword}%", self.game_language))
                                
                                if result:
                                    chest_def = result[0]
                                    print(f"    [DB] Found by keyword '{keyword}': {chest_def.get('name_chest', 'N/A')}")
                                    break
                            except Exception as e:
                                print(f"    [DB] Keyword search error for '{keyword}': {e}")
                    
                    if chest_def:
                        # Extraer id_score de diferentes campos posibles
                        chest_def_id = chest_def.get('id_score') or chest_def.get('id_chest_def')
                        
                        if chest_def_id:
                            
                            print(f"    [DB] Chest name: {chest_def.get('name_chest', 'N/A')}")
                            print(f"    [DB] Chest source: {chest_def.get('source_chest', 'N/A')}")
                            print(f"    [DB] Found chest definition ID: {chest_def_id}")
                            print(f"    [DB] ocr language used : {self.game_language}")
                            print(f"    [DB] Points: {chest_def.get('base_point_value', chest_def.get('point_value', 'N/A'))}")
                            
                            print(f"    [DB DEBUG] Verifying player_id {player_id} exists...")
                            try:
                                player_check = self.db.get_player_by_name(player_name, self.clan_id)
                                if player_check:
                                    print(f"    [DB DEBUG] ✅ Player exists in DB: {player_check}")
                                else:
                                    print(f"    [DB DEBUG] ❌ Player NOT in database!")
                                    print(f"    [DB DEBUG] Attempting to create player...")
                                    player_id = self.db.create_player(player_name, self.clan_id)
                                    print(f"    [DB DEBUG] ✅ Created player with ID: {player_id}")
                            except Exception as e:
                                print(f"    [DB DEBUG] ❌ Player verification failed: {e}")
                            
                            # Save chest record
                            print(f"    [DB] Save chest record ...")
                            print(f"    [DB] id_clan: {self.clan_id}")
                            print(f"    [DB] id_player: {player_id}")
                            print(f"    [DB] Found chest definition ID: {chest_def_id}")
                            print(f"    [DB] time_left : {time_left_clean}")
                            print(f"    [DB] obtained_at: {obtained_at}")
                            print(f"    [DB] id_session: {self.session_id}")
                            
                            chest_id = self.db.save_chest(
                                self.game_language,  # <--- Este es el argumento que faltaba
                                {
                                    'id_clan': self.clan_id,
                                    'id_player': player_id,
                                    'id_chest_def': chest_def_id,
                                    'time_left': time_left_clean,
                                    'obtained_at': obtained_at,
                                    'id_session': self.session_id
                                }
                            )
                            # chest_id = self.db.save_chest({
                            #     'id_clan': self.clan_id,
                            #     'id_player': player_id,
                            #     'id_chest_def': chest_def_id,
                            #     'time_left': time_left_clean,
                            #     'obtained_at': obtained_at,
                            #     'ocr_language_used': self.game_language,
                            #     'id_session': self.session_id
                            # })
                            # self.game_language
                            
                            print(f"✅ [DB] Saved chest ID {chest_id}")
                        else:
                            print(f"    ❌ [DB] ERROR: No id_score/id_chest_def in chest definition")
                            print(f"    ❌ [DB] Chest definition structure: {list(chest_def.keys())}")
                    else:
                        print(f"    ❌ [DB] ERROR: No chest definition found at all!")
                        print(f"    ❌ [DB] Searched: name='{chest_name}' source='{source_name}'")
                        print(f"    ❌ [DB] You may need to add this chest to your score.csv file")
                        
                        # DEBUG: Mostrar qué cofres existen en la base de datos
                        try:
                            existing_chests = self.db.execute_raw_query("""
                                SELECT cdt.name_chest, cdt.source_chest, sl.code_language
                                FROM chest_def_translations cdt
                                JOIN supported_languages sl ON cdt.id_language = sl.id_language
                                WHERE sl.code_language IN (?, 'en')
                                LIMIT 20
                            """, (self.game_language,))
                            
                            print(f"    [DB DEBUG] Existing chests in database:")
                            for chest in existing_chests:
                                print(f"        - {chest['name_chest']} | {chest['source_chest']} ({chest['code_language']})")
                        except Exception as e:
                            print(f"    [DB] Could not query existing chests: {e}")
                    
                except Exception as e:
                    print(f"    ❌ [DB] Exception during save: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            index += 1
        
        # Save to TXT files
        for row in rows:
            self.sfile.writelines(row + "\n")
            self.tfile.writelines(row + "\n")
            self.wfile.writelines(row + "\n")
        
        self.sfile.flush()
        self.tfile.flush()
        self.wfile.flush()
        
        print(f"\n### ✅ Records saved to TXT files: {len(self.records)} chests")
        
        # Verificación final
        if self.db_enabled and self.session_id:
            try:
                saved_chests = self.db.execute_raw_query(
                    "SELECT COUNT(*) as count FROM chest_registers WHERE id_session = ?",
                    (self.session_id,)
                )
                saved_count = saved_chests[0]['count'] if saved_chests else 0
                print(f"### [DB] Verification: {saved_count} chests saved in session {self.session_id}")
            except Exception as e:
                print(f"### ⚠️  Could not verify database save: {e}")
            
    def run(self):
        """Main execution method"""
        import time
        import pyautogui
        import pygetwindow
        
        value = ""
        while True:
            value = input("\nTotal Chests to collect? ('-' exit): ")
            if value.isdigit() or value == "-":
                break
        
        if value == "-":
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if self.db_enabled and self.session_id:
                self.db.close_session(self.session_id, status='cancelled', started_at=now_str, ended_at=now_str)
            exit(0)
        
        # Inicio del cronómetro
        session_start_time = time.time()
        started_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        maxClicks = int(value)
        
        while True:
            print(f"\n\n>>>>> OCR processing {self.totalClicks+1}/{maxClicks}....")
            
            # CAPTURA 1: Información principal
            image_main = self.screen.get_screenshot(self.config.x1, self.config.y1, 
                                                    self.config.x2, self.config.y2)
            image_main = self.screen.get_grayscale(numpy.array(image_main))
            capture_main = self.screen.ocr_core(image_main)
            
            # CAPTURA 2: Time Left
            image_time = self.screen.get_screenshot(self.config.time_x1, self.config.time_y1,
                                                    self.config.time_x2, self.config.time_y2)
            capture_time = self.screen.ocr_time_specialized(image_time)
            
            # MERGE BOTH CAPTURES
            capture = capture_main + "\n" + capture_time
            
            # VISUAL LOGGING
            self.save_roi_image(image_main, "chest", self.totalClicks + 1)
            self.save_roi_image(image_time, "time", self.totalClicks + 1)
            
            count = 4
            if self.totalClicks + count > maxClicks:
                count = maxClicks - self.totalClicks
            
            success = self.validate_capture(capture, count)
            
            if len(self.records) < count and len(self.records) > 0:
                nofunc = maxClicks + 1
            
            if success and len(self.records) == 0:
                print(f"\n*** {self.totalClicks} from {maxClicks} Chests saved. Process cancelled.\n")
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
                clicks = len(self.records)
                if self.totalClicks + clicks > maxClicks:
                    clicks = maxClicks - self.totalClicks
                
                moveX = [0, 3, -6, 6, -3, 0]
                hwndThis = pygetwindow.getActiveWindow()
                
                for i in range(clicks):
                    pyautogui.click(x=int(self.config.mx) + moveX[i], y=int(self.config.my))
                    self.totalClicks += 1
                    time.sleep(int(self.clickWait) / 2000.0)
                hwndThis.activate()
                time.sleep(2 * int(self.clickWait) / 2000.0)
            
            if self.totalClicks >= maxClicks:
                print(f"\n{'='*40}")
                print(f"{self.totalClicks} Chests total collected.")
                print(f"{'='*40}\n\n")
                break
        
        self.player_def.save()
        
        # Fin del cronómetro
        session_end_time = time.time()
        ended_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session_duration = session_end_time - session_start_time
        
        print(f"\n{'='*70}")
        print(f"SESSION STATISTICS")
        print(f"{'='*70}")
        print(f"Total chests collected: {self.totalClicks}")
        print(f"Session duration: {session_duration:.2f} seconds")
        print(f"{'='*70}\n")
        
        # Close database session
        if self.db_enabled and self.session_id:
            try:
                self.db.close_session(self.session_id, status='completed', started_at=started_at_str, ended_at=ended_at_str)
                print(f"✅ Database session {self.session_id} closed successfully")
            except Exception as e:
                print(f"⚠️  Failed to close session: {str(e)}")
        
        if not success:
            print("\n" + "*"*40)
            print("** THERE ARE ERRORS IN THE PROCESS **")
            print("*"*40)         
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
            while i < len(lines) - 2: 
                if word1 in lines[i] and word2 in lines[i+2]:
                    lines[i+2] = lines[i+2].replace(word2, nword2)
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
            while i < len(lines) - 2: 
                if word1 in lines[i] and word2 in lines[i+2]:
                    lines[i+2] = lines[i+2].replace(word2, nword2)
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
            
                # Prüfen Sie die dritte gelesene Zeile auf Leerheit (die 3. Zeile ist la próxima línea después del par)
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
            file += '_' +self.config.zip
            ofile += '.txt'

            opf = open(ofile, 'w')
            opf.writelines('DATE,PLAYER,SOURCE,CHEST,SCORE,CLAN\n')

            source_line_count = 0
            parsed_line_count = 0

            while True:

                try:
                    chest = player = source = ""

                    line = fp.readline()
                    if not line:
                        break

                    chest = line.strip()
                    source_line_count += 1

                    line = fp.readline()
                    if not line:
                        break

                    splitter = ":"

                    player = line.strip()
                    split_player = player.split(splitter, 1)
                    player = split_player[1].strip()

                    source_line_count += 1

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
                            print("Processing ({}/{}): {},{},{},{},{},{}".format( parsed_line_count, source_line_count, processing_date, player, source, chest, score, self.config.clan))

                        opf.writelines(processing_date+','+player+','+source+','+chest+','+score+','+self.config.clan+'\n')
                    else:
                        print("*** ERROR: Failed to parse chest ({}/{}): {}, From: {}, Source: {}".format( parsed_line_count, source_line_count, chest, player, source))
                        success = False
                        break
                except:
                        print("*** EXCEPTION: Chest ({}/{}): {}, From: {}, Source: {}".format( parsed_line_count, source_line_count, chest, player, source))
                        success = False
                        break
               
            opf.close()

        if parsed_line_count != source_line_count / 3:
            print("*** ERROR Mismatch between procseed line count and source line count: {} != {} / 3".format(parsed_line_count,source_line_count))
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
            file_pattern += "_TB_Chests_" + self.config.clan + "_FINAL_" + self.config.zip + ".txt"
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
                file_pattern += "_TB_Chests_" + self.config.clan + "_FINAL_" + self.config.zip + ".txt"

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
        file += "_FINAL_" + self.config.zip + ".txt"

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
            clip                    = self.config.zip
            savefile                = f"../{var2}/{processing_date}_{var3}_{var5}_FINAL_{clip}.txt"
            
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
            file_pattern += "_*_FINAL_" + self.config.zip + ".txt"
    
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
                file_pattern += "_" + processing_date + "_FINAL_" + self.config.zip + ".txt"
    
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
        file += self.zip
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
# ============================================================================
# ARGUMENT PARSER - TBChestCounter
# ============================================================================

if __name__ == "__main__":
    
    # ========================================================================
    # ARGUMENTOS DE LÍNEA DE COMANDOS
    # ========================================================================
    
    parser = argparse.ArgumentParser(
        description="Total Battle Chest Counter - Multi-mode OCR system",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # ========================================================================
    # MODOS DE OPERACIÓN
    # ========================================================================
    
    parser.add_argument(
        "--calibrate", 
        action="store_true", 
        help="Run calibration mode to set screen coordinates"
    )
    
    parser.add_argument(
        "--capture", 
        action="store_true", 
        help="Run capture mode to record chest openings"
    )
    
    parser.add_argument(
        "--process", 
        action="store_true", 
        help="Run processing mode to analyze captured data"
    )
    
    # ========================================================================
    # ARGUMENTOS DE CONFIGURACIÓN
    # ========================================================================
    
    parser.add_argument(
        "--config", 
        default="config/config.cfg",
        help="Path to configuration file (default: config/config.cfg)"
    )
    
    parser.add_argument(
        "--language", 
        default="en",
        help="OCR language code (default: en)"
    )
    
    parser.add_argument(
        "--clickWait", 
        type=int, 
        default=250,
        help="Milliseconds to wait between auto-clicks (default: 250)"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging for debugging"
    )

    # ========================================================================
    # ARGUMENTOS DE PROCESAMIENTO
    # ========================================================================
    
    parser.add_argument(
        "--date", 
        help="Processing date in YYYY-MM-DD format (default: today)"
    )
    
    parser.add_argument(
        "--start_date", 
        help="Start date for batch processing (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--end_date", 
        help="End date for batch processing (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--eod", 
        action="store_true", 
        help="Run end-of-day processing"
    )
    
    parser.add_argument(
        "--summary", 
        action="store_true", 
        help="Generate player summary from processed files"
    )
    
    parser.add_argument(
        "--citadels", 
        action="store_true", 
        help="Generate citadel-only summary"
    )
    
    parser.add_argument(
        "--skip_empty", 
        action="store_true", 
        help="Skip players with 0 chests in summaries"
    )

    # ========================================================================
    # PARSEAR ARGUMENTOS
    # ========================================================================
    
    args = parser.parse_args()
    
    # ========================================================================
    # VALIDACIÓN DE ARGUMENTOS
    # ========================================================================
    
    # Verificar que se especificó al menos un modo
    if not any([args.calibrate, args.capture, args.process]):
        parser.error("You must specify at least one mode: --calibrate, --capture, or --process")
    
    # Validar fechas si se especificaron
    if args.start_date or args.end_date:
        if not (args.start_date and args.end_date):
            parser.error("Both --start_date and --end_date must be specified together")
        
        try:
            from datetime import datetime
            start = datetime.strptime(args.start_date, "%Y-%m-%d")
            end = datetime.strptime(args.end_date, "%Y-%m-%d")
            if start > end:
                parser.error("--start_date cannot be after --end_date")
        except ValueError:
            parser.error("Dates must be in YYYY-MM-DD format")
    
    # ========================================================================
    # CARGAR CONFIGURACIÓN
    # ========================================================================
    
    print("\n" + "="*70)
    print("TOTAL BATTLE CHEST COUNTER")
    print("="*70)
    print(f"Mode      : {'Calibrate' if args.calibrate else 'Capture' if args.capture else 'Process'}")
    print(f"Config    : {args.config}")
    print(f"Language  : {args.language}")
    print(f"Verbose   : {args.verbose}")
    print("="*70 + "\n")
    
    config = TBConfig(args.config, args.clickWait)

    # ========================================================================
    # DATABASE INITIALIZATION
    # ========================================================================
    
    if DATABASE_AVAILABLE:
        try:
            print("\n" + "="*70)
            print("DATABASE INITIALIZATION")
            print("="*70)
            
            db_path = os.path.join('..', 'data', 'databases', 'TB_chests_clans.db')
            db_path_abs = os.path.abspath(db_path)
            print(f"### [DB] Database path: {db_path}")
            print(f"### [DB] Absolute path: {db_path_abs}")
            
            # ✅ FIXED: Pass language parameter to TBDatabaseManager
            # This is the key fix - now language is passed to the constructor
            db = TBDatabaseManager(db_path=db_path, language=args.language)
            
            # ✅ FIXED: Language can also be updated during initialization
            # The initialize method now accepts an optional language parameter
            db.initialize(language=args.language)
            
            print("✅ Database initialized successfully")
            print(f"✅ Database configured for language: {args.language}")
            
            # ✅ FIXED: Set database reference in language manager
            language_manager.set_database(db)
            
            # Get or create clan
            print(f"### [CLAN] Active clan zip: '{config.zip}'")
            print(f"### [CLAN] Clan name: '{config.active_clan_name}'")
            print(f"### [CLAN] Abbreviation: '{config.clan}'")
            
            clan_id = db.get_or_create_clan(config.active_clan_name, config.clan)
            print(f"✅ Clan loaded: {config.active_clan_name} (ID: {clan_id})")
            
            # Load players from CSV
            if os.path.exists(config.player_file):
                player_count = db.load_players_from_csv_batch(config.player_file, clan_id)
                print(f"✅ Loaded {player_count} players from {config.player_file}")
            else:
                print(f"⚠️  Player file not found: {config.player_file}")
            
            # Load chest definitions
            if os.path.exists(config.score_file):
                print(f"📊 Loading chest definitions from: {config.score_file}")
                score_count = db.load_chest_scores_from_csv(config.score_file)
                print(f"✅ Loaded {score_count} chest definitions")
            
            print("="*70 + "\n")
            
        except Exception as e:
            print(f"\n⚠️  DATABASE INITIALIZATION FAILED: {str(e)}")
            print("⚠️  Continuing in TXT-only mode\n")
            import traceback
            traceback.print_exc()
            DATABASE_AVAILABLE = False
            db = None
    else:
        print("\n⚠️  Database module not available - running in TXT-only mode\n")
        db = None

    # ========================================================================
    # EJECUTAR MODO SELECCIONADO
    # ========================================================================
    
    if args.calibrate:
        app1 = TBCalibration()
        app1.run(config)
        
    elif args.capture:
        app2 = TBCapture(config, args)
        app2.run()
        
    elif args.process:
        app3 = TBProcess(config, args)
        app3.run()

    # ========================================================================
    # REGRESAR A POWERSHELL GUI
    # ========================================================================
    
    # ✅ FIXED: Added check for clan variables before using them
    # These variables need to be defined in the config or elsewhere
    try:
        clan1 = config.clangui if hasattr(config, 'clangui') else 'Clan 1'
        clan2 = config.clangui2 if hasattr(config, 'clangui2') else 'Clan 2'
        clan3 = config.clangui3 if hasattr(config, 'clangui3') else 'Clan 3'
        clan4 = config.clangui4 if hasattr(config, 'clangui4') else 'Clan 4'
        
        pshellpath1 = config.pshellpath1 if hasattr(config, 'pshellpath1') else ''
        pshellpath2 = config.pshellpath2 if hasattr(config, 'pshellpath2') else ''
        pshellpath3 = config.pshellpath3 if hasattr(config, 'pshellpath3') else ''
        pshellpath4 = config.pshellpath4 if hasattr(config, 'pshellpath4') else ''
    except AttributeError:
        print("\n⚠️  Warning: PowerShell GUI configuration not found")
        clan1 = clan2 = clan3 = clan4 = 'Not configured'
        pshellpath1 = pshellpath2 = pshellpath3 = pshellpath4 = ''
    
    while True: 
        print("\n")
        print(">>> Back to PowerShell GUI?")
        print(">>> 1 : Clan {}".format(clan1))
        print(">>> 2 : Clan {}".format(clan2))
        print(">>> 3 : Clan {}".format(clan3))
        print(">>> 4 : Clan {}".format(clan4))
        print(">>> all other keys for Exit \n")
        
        import subprocess
        choice = input("[1] - [2] - [3] - [4] or [eXit] ? ")
        
        if choice.lower() == "1" and pshellpath1:
            command = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"{pshellpath1}\""
            result = subprocess.run(command)
            break
        elif choice.lower() == "2" and pshellpath2:
            command = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"{pshellpath2}\""
            result = subprocess.run(command)
            break
        elif choice.lower() == "3" and pshellpath3:
            command = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"{pshellpath3}\""
            result = subprocess.run(command)
            break
        elif choice.lower() == "4" and pshellpath4:
            command = f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"{pshellpath4}\""
            result = subprocess.run(command)
            break
        else:
            print("\nEXIT\n")
            break