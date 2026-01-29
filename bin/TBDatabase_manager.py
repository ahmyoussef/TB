"""
TBDatabase_manager.py - Production-Grade Database Layer for TB Chest Tracking System
Version: 1.1.0
Author: Total Battle OCR Team
Date: 2026-01-14

ARCHITECTURAL PRINCIPLES:
- ALL database logic isolated in this module
- tb.py calls ONLY high-level public methods
- Thread-safe singleton pattern
- Connection pooling for performance
- Comprehensive error handling
- Audit trail for all corrections
DATABASE FILE: data/databases/TB_chests_clans.db
"""

import os
import sqlite3
import logging
import threading
import atexit
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from queue import Queue


# ============================================================================
# CONNECTION POOL
# ============================================================================

class ConnectionPool:
    """Thread-safe SQLite connection pool with WAL mode optimization."""
    
    def __init__(self, db_path: str, pool_size: int = 5, max_overflow: int = 10):
        self.db_path = db_path
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._pool = Queue(maxsize=pool_size)
        self._overflow = 0
        self._lock = threading.RLock()
        self._connections_created = 0
        
        # Initialize pool
        for _ in range(pool_size):
            conn = self._create_connection()
            self._pool.put(conn)
        
        atexit.register(self.close_all)
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create optimized SQLite connection."""
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        # SQLite optimizations
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -10000")  # 10MB cache
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA temp_store = MEMORY")
        
        self._connections_created += 1
        return conn
    
    def get_connection(self) -> sqlite3.Connection:
        """Get connection from pool."""
        try:
            return self._pool.get_nowait()
        except:
            with self._lock:
                if self._overflow < self.max_overflow:
                    self._overflow += 1
                    return self._create_connection()
                else:
                    return self._pool.get(timeout=5.0)
    
    def return_connection(self, conn: sqlite3.Connection) -> None:
        """Return connection to pool."""
        try:
            conn.rollback()  # Reset state
            self._pool.put_nowait(conn)
        except:
            try:
                conn.close()
            except:
                pass
            with self._lock:
                if self._overflow > 0:
                    self._overflow -= 1
    
    def close_all(self) -> None:
        """Close all pooled connections."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except:
                pass


# ============================================================================
# MAIN DATABASE MANAGER
# ============================================================================

class TBDatabaseManager:
    """
    Production-grade database manager for TB Chest Tracking System.
    Singleton pattern ensures single instance per application.
    
    Usage:
        db = TBDatabaseManager(db_path='data/databases/TB_chests_clans.db')
        db.initialize()
        
        clan_id = db.get_or_create_clan('HALO', 'HLO')
        session_id = db.create_session(clan_id)
        chest_id = db.save_chest({...})
    """
    
    _instance = None
    _initialized = False
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = None, language: str = 'en'):
        """Singleton pattern with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TBDatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: str = 'data/databases/TB_chests_clans.db', language: str = 'en'):
        """
        Initialize database manager (only once).
        
        Args:
            db_path: Path to the SQLite database file
            language: Language code for chest translations (e.g., 'en', 'es', 'de')
        """
        if not self._initialized:
            self.logger = logging.getLogger(__name__)
            self.db_path = db_path
            self.language = language  # ✅ Store language parameter
            self.pool = None
            self._cache = {}
            self._cache_lock = threading.RLock()
            self._initialized = True
            
            # Log initialization
            self.logger.info(f"TBDatabaseManager initialized with language: {language}")
    
    # ========================================================================
    # INITIALIZATION & SCHEMA
    # ========================================================================
    
    def initialize(self, language: str = None) -> None:
        """
        Initialize database connection and create schema.
        
        Args:
            language: Optional language override. If provided, updates the instance language.
        """
        try:
            # Update language if provided
            if language is not None:
                self.language = language
                self.logger.info(f"Language updated to: {language}")
            
            # Create database directory
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
            
            # Create connection pool
            self.pool = ConnectionPool(self.db_path, pool_size=5, max_overflow=10)
            
            # Create tables
            self.create_tables()
            
            # Warm cache
            self._warmup_cache()
            
            self.logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
            raise
    
    def create_tables(self) -> None:
        """Create all required tables in correct order."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. capture_sessions - historial de las ejecuciones del programa tb.py
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS capture_sessions (
                    id_session INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_clan INTEGER NOT NULL,
                    id_user INTEGER,
                    ocr_language TEXT DEFAULT 'en',
                    total_chests_captured INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled', 'error')),
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_clan) REFERENCES clans(id_clan) ON DELETE CASCADE,
                    FOREIGN KEY (id_user) REFERENCES players(id_player) ON DELETE SET NULL
                )
            """)
            
            # 2. clans - listado de los clanes que se gestionan
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clans (
                    id_clan INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_clan TEXT NOT NULL,
                    abbreviation_clan TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name_clan, abbreviation_clan)
                )
            """)
            
            # 3. players - listado detallado de los jugadores
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id_player INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_clan INTEGER NOT NULL,
                    name_player TEXT NOT NULL,
                    member_role TEXT,
                    hero_level INTEGER DEFAULT 10,
                    guards_level INTEGER DEFAULT 1,
                    monsters_level INTEGER DEFAULT 1,
                    specialists_level INTEGER DEFAULT 1,
                    engineers_corps_level INTEGER DEFAULT 1,
                    gold_pass BOOLEAN DEFAULT 0,
                    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
                    joined_date DATE DEFAULT CURRENT_DATE,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_clan) REFERENCES clans(id_clan) ON DELETE CASCADE,
                    UNIQUE(id_clan, name_player)
                )
            """)
            
            # 4. player_aliases - listado de las aliases de los jugadores detectado por OCR
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_aliases (
                    id_alias INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_player INTEGER NOT NULL,
                    alias_text TEXT NOT NULL,
                    is_primary BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_player) REFERENCES players(id_player) ON DELETE CASCADE,
                    UNIQUE(id_player, alias_text)
                )
            """)
            
            # 5. player_alias_audit - auditoria de los cambios sobre la tabla player_aliases
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_alias_audit (
                    id_player_audit INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_player INTEGER NOT NULL,
                    old_alias TEXT,
                    new_alias TEXT,
                    changed_by TEXT DEFAULT 'system',
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_player) REFERENCES players(id_player) ON DELETE CASCADE
                )
            """)
            
            # 6. supported_languages - Lenguages suportados por la aplicacion
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS supported_languages (
                    id_language INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_language TEXT NOT NULL UNIQUE,
                    name_language TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CHECK (length(code_language) = 2)
                )
            """)
            
            # 7. chest_score - definicion de las puntuaciones de los cofres, sin idioma
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chest_score (
                    id_score INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_chest TEXT NOT NULL UNIQUE,
                    base_point_value INTEGER NOT NULL CHECK(base_point_value >= 0),
                    is_active BOOLEAN DEFAULT 1,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 8. chest_def_translations - traduccion de los diferentes cofres
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chest_def_translations (
                    id_translation INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_score INTEGER NOT NULL,
                    id_language INTEGER NOT NULL,
                    name_chest TEXT NOT NULL,
                    source_chest TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_score) REFERENCES chest_score(id_score) ON DELETE CASCADE,
                    FOREIGN KEY (id_language) REFERENCES supported_languages(id_language),
                    UNIQUE(id_language, name_chest, source_chest)
                )
            """)
            
            # 9. chest_score_changes - auditoria de la puntuacion de los cofres
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chest_score_changes (
                    id_score_change INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_score INTEGER NOT NULL,
                    old_point_value INTEGER NOT NULL,
                    new_point_value INTEGER NOT NULL,
                    changed_by TEXT DEFAULT 'system',
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_score) REFERENCES chest_score(id_score) ON DELETE CASCADE
                )
            """)
            
            # 10. chest_registers - historial o inventario de los cofres generados por los jugadores
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chest_registers (
                    id_register INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_clan	INTEGER NOT NULL,
                    id_player INTEGER NOT NULL,
                    id_chest_def INTEGER NOT NULL,
                    time_left TEXT DEFAULT '19h : 59m : 59s',
                    obtained_at DATETIME,
                    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    id_session	INTEGER,
                    ocr_language_used TEXT,
                    points_awarded INTEGER,
                    FOREIGN KEY (id_player) REFERENCES players(id_player) ON DELETE RESTRICT,
                    FOREIGN KEY("id_clan") REFERENCES "clans"("id_clan") ON DELETE CASCADE,
                    FOREIGN KEY (id_chest_def) REFERENCES chest_score(id_score) ON DELETE RESTRICT,
                    FOREIGN KEY (id_session) REFERENCES capture_sessions(id_session) ON DELETE SET NULL
                )
            """)
            
            # 11. reward_captures - Captura de los premios por cada registro de los cofres
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reward_captures (
                    id_capture INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_register INTEGER NOT NULL,
                    image_path TEXT NOT NULL,
                    capture_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed INTEGER DEFAULT 0,
                    FOREIGN KEY (id_register) REFERENCES chest_registers(id_register) ON DELETE CASCADE
                )
            """)
            
            # 12. reward_categories - categorias base de recompensas (sin idioma)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reward_categories (
                    id_category INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_category TEXT NOT NULL UNIQUE,
                    icon_reference TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 13. reward_category_translations - Traduccion de las categorias
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reward_category_translations (
                    id__cat_translation INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_category INTEGER NOT NULL,
                    id_language TEXT NOT NULL,
                    name_category TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_category) REFERENCES reward_categories(id_category) ON DELETE CASCADE,
                    FOREIGN KEY (id_language) REFERENCES supported_languages(id_language),
                    UNIQUE(id_language, name_category)
                )
            """)
            
            # 14. reward_types - Tipos base de recompensas (Sin idioma)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reward_types (
                    id_type INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_type TEXT NOT NULL UNIQUE,
                    icon_reference TEXT,
                    is_chest BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 15. reward_type_translations - Traduccion de los tipos de recompensas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reward_type_translations (
                    id_type_translation INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_type INTEGER NOT NULL,
                    id_language INTEGER NOT NULL,
                    name_type TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_type) REFERENCES reward_types(id_type) ON DELETE CASCADE,
                    FOREIGN KEY (id_language) REFERENCES supported_languages(id_language),
                    UNIQUE(name_type, id_language)
                )
            """)
            
            # 16. reward_definitions - Definiciones o relacion categoria-tipo de recompensas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reward_definitions (
                    id_reward_def INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_category INTEGER NOT NULL,
                    id_type INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_category) REFERENCES reward_categories(id_category),
                    FOREIGN KEY (id_type) REFERENCES reward_types(id_type),
                    UNIQUE(id_category, id_type)
                )
            """)
            
            # 17. ml_ocr_prediction_reward - Predicciones ML de los premios ganados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ml_ocr_prediction_reward (
                    id_prediction INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_reward_capture INTEGER NOT NULL,
                    id_reward_def INTEGER,
                    ml_icon_prediction TEXT,
                    ml_icon_confidence REAL DEFAULT 0.0,
                    ocr_upper_text TEXT,
                    ocr_upper_confidence REAL DEFAULT 0.0,
                    ocr_lower_text TEXT,
                    ocr_lower_confidence REAL DEFAULT 0.0,
                    final_decision TEXT,
                    is_validated BOOLEAN DEFAULT 0,
                    validated_by TEXT,
                    validated_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_reward_capture) REFERENCES reward_captures(id_capture) ON DELETE CASCADE,
                    FOREIGN KEY (id_reward_def) REFERENCES reward_definitions(id_reward_def) ON DELETE SET NULL
                )
            """)
            
            # 18. ocr_language_patterns - patrones de los texto detectados por el ocr
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ocr_language_patterns (
                    id_pattern INTEGER PRIMARY KEY AUTOINCREMENT,
                    language_code TEXT NOT NULL,
                    language_name TEXT NOT NULL,
                    keyword_type TEXT NOT NULL,
                    keyword_variations TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(language_code, keyword_type),
                    CHECK (json_valid(keyword_variations))
                )
            """)
            
            conn.commit()
            self.logger.info("Database schema created successfully")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Schema creation failed: {str(e)}")
            raise
        finally:
            self.pool.return_connection(conn)
    
    def insert_default_data(self) -> None:
        """Insert default languages and patterns."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            
            # Insert default languages
            cursor.execute("""
                INSERT OR IGNORE INTO supported_languages 
                (code_language, name_language, is_default) 
                VALUES 
                    ('en', 'English', 1),
                    ('es', 'Español', 0),
                    ('fr', 'Français', 0),
                    ('de', 'Deutsch', 0)
            """)
            
            # Insert default OCR patterns
            default_patterns = [
                ('en', 'English', 'from', '["From", "Fr om", "F rom"]'),
                ('en', 'English', 'source', '["Source", "S ource", "ource"]'),
                ('en', 'English', 'time_left', '["Time left", "Time Left", "Time Left:"]'),
                ('es', 'Español', 'from', '["De", "Desde", "Jugador"]'),
                ('es', 'Español', 'source', '["Fuente", "Origen", "Procedencia"]'),
                ('es', 'Español', 'time_left', '["Tiempo restante", "Tiempo Restante", "Tiempo:"]')
            ]
            
            for pattern in default_patterns:
                cursor.execute("""
                    INSERT OR IGNORE INTO ocr_language_patterns 
                    (language_code, language_name, keyword_type, keyword_variations) 
                    VALUES (?, ?, ?, ?)
                """, pattern)
            
            conn.commit()
            self.logger.info("Default data inserted")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Default data insertion failed: {str(e)}")
        finally:
            self.pool.return_connection(conn)

    # ========================================================================
    # CLAN MANAGEMENT
    # ========================================================================                
    def get_clan_by_abbr(self, abbr: str) -> Optional[Dict]:
        """Get clan by abbreviation - SOLO PARA CONSULTAS, NO PARA CREACIÓN."""
        if not abbr:
            return None
        
        abbr_clean = abbr.strip().upper()
        
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM clans WHERE name_abbreviation = ?",
                (abbr_clean,)
            )
            row = cursor.fetchone()
            
            return dict(row) if row else None
                
        finally:
            self.pool.return_connection(conn)
    
    def get_or_create_clan(self, name: str, abbr: str) -> int:
        """
        Get existing clan BY NAME or create new one.
        BUSCA POR NOMBRE, NO POR ABREVIATURA.
        
        Args:
            name: Nombre completo del clan (ej: 'LUNA')
            abbr: Abreviatura deseada (ej: 'LUN')
        
        Returns:
            id_clan
        """
        print(f"\n### [CLAN] Buscando/creando clan: '{name}' (abbr deseada: '{abbr}')")
        
        # Limpiar inputs
        name_clean = name.strip()
        abbr_clean = abbr.strip().upper() if abbr else ""
        
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            
            # PASO 1: BUSCAR POR NOMBRE EXACTO (sin importar mayúsculas/minúsculas)
            cursor.execute(
                "SELECT id_clan, name_abbreviation FROM clans WHERE UPPER(name_clan) = UPPER(?)",
                (name_clean,)
            )
            row = cursor.fetchone()
            
            if row:
                # ¡CLAN ENCONTRADO POR NOMBRE!
                clan_id = row['id_clan']
                current_abbr = row['name_abbreviation']
                
                print(f"✅ [CLAN] Encontrado clan '{name_clean}': ID {clan_id}")
                print(f"### [CLAN] Abreviatura actual: '{current_abbr}'")
                
                # Verificar si la abreviatura actual es la correcta
                if current_abbr != abbr_clean and abbr_clean:
                    print(f"🔄 [CLAN] Actualizando abreviatura: '{current_abbr}' → '{abbr_clean}'")
                    
                    # Verificar si la nueva abreviatura ya está usada por OTRO clan
                    cursor.execute(
                        "SELECT id_clan FROM clans WHERE name_abbreviation = ? AND id_clan != ?",
                        (abbr_clean, clan_id)
                    )
                    abbr_used_by_other = cursor.fetchone()
                    
                    if abbr_used_by_other:
                        print(f"⚠️ [CLAN] Abreviatura '{abbr_clean}' ya usada por otro clan (ID: {abbr_used_by_other['id_clan']})")
                        print(f"⚠️ [CLAN] Manteniendo abreviatura actual: '{current_abbr}'")
                    else:
                        # Actualizar abreviatura
                        cursor.execute(
                            "UPDATE clans SET name_abbreviation = ? WHERE id_clan = ?",
                            (abbr_clean, clan_id)
                        )
                        conn.commit()
                        print(f"✅ [CLAN] Abreviatura actualizada correctamente")
                
                return clan_id
            
            # PASO 2: CLAN NO EXISTE - CREAR NUEVO
            print(f"➕ [CLAN] Clan '{name_clean}' no existe, creando nuevo...")
            
            # Verificar si la abreviatura deseada ya está usada
            if abbr_clean:
                cursor.execute(
                    "SELECT id_clan, name_clan FROM clans WHERE name_abbreviation = ?",
                    (abbr_clean,)
                )
                abbr_exists = cursor.fetchone()
                
                if abbr_exists:
                    print(f"⚠️ [CLAN] Abreviatura '{abbr_clean}' ya usada por clan '{abbr_exists['name_clan']}' (ID: {abbr_exists['id_clan']})")
                    print(f"❓ [CLAN] ¿Qué hacer? Opciones:")
                    print(f"   1. Usar el clan existente '{abbr_exists['name_clan']}'")
                    print(f"   2. Crear nuevo clan con abreviatura diferente")
                    
                    # Por defecto: Crear con abreviatura temporal
                    import time
                    timestamp = int(time.time()) % 1000
                    temp_abbr = f"{abbr_clean}_{timestamp}"
                    print(f"### [CLAN] Creando con abreviatura temporal: '{temp_abbr}'")
                    
                    cursor.execute(
                        "INSERT INTO clans (name_clan, name_abbreviation) VALUES (?, ?)",
                        (name_clean, temp_abbr)
                    )
                else:
                    # Abreviatura libre, usar la deseada
                    cursor.execute(
                        "INSERT INTO clans (name_clan, name_abbreviation) VALUES (?, ?)",
                        (name_clean, abbr_clean)
                    )
            else:
                # Sin abreviatura, usar primeras 3 letras del nombre
                default_abbr = name_clean[:3].upper()
                cursor.execute(
                    "INSERT INTO clans (name_clan, name_abbreviation) VALUES (?, ?)",
                    (name_clean, default_abbr)
                )
            
            conn.commit()
            clan_id = cursor.lastrowid
            print(f"✅ [CLAN] Creado nuevo clan ID: {clan_id}")
            
            return clan_id
            
        except sqlite3.IntegrityError as e:
            conn.rollback()
            print(f"❌ [CLAN] Error de integridad: {str(e)}")
            
            # Último intento: buscar de nuevo por si se creó en paralelo
            cursor.execute(
                "SELECT id_clan FROM clans WHERE UPPER(name_clan) = UPPER(?)",
                (name_clean,)
            )
            row = cursor.fetchone()
            if row:
                return row['id_clan']
            else:
                raise
        finally:
            self.pool.return_connection(conn)
    # ========================================================================
    # PLAYER MANAGEMENT
    # ========================================================================
    
    def get_player_by_name(self, name: str, id_clan: int) -> Optional[Dict]:
        """Get player by exact name match."""
        cache_key = f"player_{id_clan}_{name.lower()}"
        
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM players 
                   WHERE id_clan = ? AND name_player = ? AND status = 'active'""",
                (id_clan, name)
            )
            print(f"### get_player_by_name: ID CLAN {id_clan} - NAME {name}")
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                with self._cache_lock:
                    self._cache[cache_key] = result
                return result
            return None
            
        finally:
            self.pool.return_connection(conn)
    
    def get_player_by_alias(self, alias: str, id_clan: int) -> Optional[Dict]:
        """Search player by alias (checks all 8 alias columns)."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            
            # Build dynamic query for all alias columns
            print(f"### get_player_by_alias: ID CLAN {id_clan} - ALIAS {alias}")
            cursor.execute(
                """SELECT p.* FROM players p
                   JOIN player_aliases pa ON p.id_player = pa.id_player
                   WHERE p.id_clan = ? AND p.status = 'active' 
                   AND pa.alias_text = ?""",
                (id_clan, alias)
            )
            row = cursor.fetchone()
            
            return dict(row) if row else None
            
        finally:
            self.pool.return_connection(conn)
    
    def create_player(self, name: str, id_clan: int) -> int:
        """Create new player. Returns id_player."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO players 
                   (id_clan, name_player) 
                   VALUES (?, ?)""",
                (id_clan, name)
            )
            conn.commit()
            player_id = cursor.lastrowid
            
            self.logger.info(f"Created new player: {name} (ID {player_id}) in clan {id_clan}")
            
            # Clear cache
            with self._cache_lock:
                self._cache.pop(f"player_{id_clan}_{name.lower()}", None)
            
            return player_id
            
        except sqlite3.IntegrityError as e:
            conn.rollback()
            self.logger.error(f"Player creation failed: {str(e)}")
            raise
        finally:
            self.pool.return_connection(conn)
    
    def add_player_alias(self, id_player: int, alias_value: str) -> bool:
        """Add alias to player."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute(
                """INSERT INTO player_aliases (id_player, alias_text) 
                   VALUES (?, ?)""",
                (id_player, alias_value)
            )
            
            # Log audit trail
            cursor.execute(
                """INSERT INTO player_alias_audit 
                   (id_player, new_alias, changed_by) 
                   VALUES (?, ?, 'system')""",
                (id_player, alias_value)
            )
            
            conn.commit()
            return True
            
        except sqlite3.IntegrityError:
            conn.rollback()
            return False
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Alias addition failed: {str(e)}")
            return False
        finally:
            self.pool.return_connection(conn)
    
    def load_players_from_csv_batch(self, csv_path: str, id_clan: int) -> int:
        """Load players from CSV using batch inserts for better performance."""
        import time
        start_time = time.time()
        
        players_created = 0
        aliases_created = 0
        conn = self.pool.get_connection()
        
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            # Leer todo el archivo primero
            with open(csv_path, 'r', encoding='utf-8') as fp:
                lines = fp.readlines()
            
            print(f"### Processing {len(lines)} lines from {csv_path}")
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                parts = [part.strip() for part in line.split(",")]
                if not parts:
                    continue
                    
                player_name = parts[0]
                aliases = parts[1:] if len(parts) > 1 else []
                
                # ============================================
                # 1. INSERTAR JUGADOR (INSERT OR IGNORE)
                # ============================================
                cursor.execute("""
                    INSERT OR IGNORE INTO players (id_clan, name_player, status) 
                    VALUES (?, ?, 'active')
                """, (id_clan, player_name))
                
                if cursor.rowcount > 0:
                    players_created += 1
                
                # Obtener ID del jugador (creado o existente)
                cursor.execute("""
                    SELECT id_player FROM players 
                    WHERE id_clan = ? AND name_player = ?
                """, (id_clan, player_name))
                
                result = cursor.fetchone()
                if not result:
                    continue  # Should not happen
                    
                player_id = result['id_player']
                
                # ============================================
                # 2. INSERTAR ALIASES (INSERT OR IGNORE)
                # ============================================
                for alias_num, alias in enumerate(aliases, 1):
                    alias_clean = alias.strip()
                    if not alias_clean:
                        continue
                    
                    # Insertar alias
                    cursor.execute("""
                        INSERT OR IGNORE INTO player_aliases 
                        (id_player, alias_text, is_primary)
                        VALUES (?, ?, ?)
                    """, (player_id, alias_clean, 1 if alias_num == 1 else 0))
                    
                    if cursor.rowcount > 0:
                        aliases_created += 1
                        
                        # Registrar en auditoría solo si se insertó nuevo alias
                        cursor.execute("""
                            INSERT INTO player_alias_audit 
                            (id_player, new_alias, changed_by)
                            VALUES (?, ?, 'csv_import')
                        """, (player_id, alias_clean))
                
                # Mostrar progreso cada 10 jugadores
                if line_num % 10 == 0:
                    print(f"### Processed {line_num}/{len(lines)} lines...")
            
            conn.commit()
            
            elapsed = time.time() - start_time
            
            # ============================================
            # 3. GENERAR REPORTE
            # ============================================
            # Obtener estadísticas finales
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT p.id_player) as total_players,
                    COUNT(DISTINCT pa.id_alias) as total_aliases
                FROM players p
                LEFT JOIN player_aliases pa ON p.id_player = pa.id_player
                WHERE p.id_clan = ? AND p.status = 'active'
            """, (id_clan,))
            
            stats = cursor.fetchone()
            
            print(f"\n{'='*70}")
            print(f"BATCH CSV IMPORT COMPLETE")
            print(f"{'='*70}")
            print(f"Clan ID: {id_clan}")
            print(f"Time elapsed: {elapsed:.2f} seconds")
            print(f"Lines processed: {len(lines)}")
            print(f"New players created: {players_created}")
            print(f"New aliases created: {aliases_created}")
            print(f"Total players in clan: {stats['total_players']}")
            print(f"Total aliases in clan: {stats['total_aliases']}")
            print(f"{'='*70}")
            
            self.logger.info(
                f"Loaded {players_created} players and {aliases_created} aliases "
                f"from {csv_path} in {elapsed:.2f}s"
            )
            
            # Limpiar caché
            self.clear_cache()
            
            return players_created
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Batch CSV load failed: {str(e)}")
            raise
        finally:
            self.pool.return_connection(conn)
    
    # ========================================================================
    # CHEST DEFINITION MANAGEMENT
    # ========================================================================
    
    def get_chest_score_by_code(self, code_chest: str) -> Optional[Dict]:
        """Get chest score by internal code."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            print(f"### get_chest_score_by_code: CODE_CHEST {code_chest}")
            cursor.execute(
                "SELECT * FROM chest_score WHERE code_chest = ? AND is_active = 1",
                (code_chest,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            self.pool.return_connection(conn)
    
    def get_chest_by_translation(self, name: str, source: str, language: str = 'en') -> Optional[Dict]:
        """Get chest by name/source in specific language with fallback."""
        print(f"### get_chest_by_translation INICIO: ID LANG {language} - CHEST NAME {name} - SOURCE  {source}")
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            
            # Get language ID
            print(f"### get_chest_by_translation: CODE LANG {language}")
            cursor.execute(
                "SELECT id_language FROM supported_languages WHERE code_language = ?",
                (language,)
            )
            lang_row = cursor.fetchone()
            
            # Si no existe el idioma, usar inglés
            if not lang_row:
                print(f"### get_chest_by_translation: USA TRADUCCIONES EN INGLES")
                cursor.execute(
                    "SELECT id_language FROM supported_languages WHERE code_language = 'en'"
                )
                lang_row = cursor.fetchone()
            
            if not lang_row:
                return None
            
            id_language = lang_row['id_language']

            print(f"### get_chest_by_translation: ID LANG {id_language} - CHEST NAME %{name}% - SOURCE %{source}%")
            
            # ESTRATEGIA 1: Buscar coincidencia exacta o muy cercana
            cursor.execute("""
                SELECT cs.*, cdt.name_chest, cdt.source_chest 
                FROM chest_score cs
                JOIN chest_def_translations cdt ON cs.id_score = cdt.id_score
                WHERE cdt.id_language = ? 
                AND (
                    (cdt.name_chest LIKE ?)
                    AND (cdt.source_chest LIKE ?)
                )
                LIMIT 1
            """, (id_language, f"%{name}%", f"%{source}%"))
            
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                # Añadir campos para compatibilidad
                result['id_chest_def'] = result['id_score']
                result['chest_name'] = result['name_chest']
                result['chest_source'] = result['source_chest']
                result['point_value'] = result['base_point_value']
                return result
            
            # # ESTRATEGIA 2: Buscar solo por nombre (cofre conocido)
            # cursor.execute("""
            #     SELECT cs.*, cdt.name_chest, cdt.source_chest 
            #     FROM chest_score cs
            #     JOIN chest_def_translations cdt ON cs.id_score = cdt.id_score
            #     WHERE cdt.id_language = ? 
            #     AND (cdt.name_chest = ? OR cdt.name_chest LIKE ?)
            #     LIMIT 1
            # """, (id_language, name, f"%{name}%"))
            
            # row = cursor.fetchone()
            
            # if row:
            #     result = dict(row)
            #     result['id_chest_def'] = result['id_score']
            #     result['chest_name'] = result['name_chest']
            #     result['chest_source'] = result['source_chest']
            #     result['point_value'] = result['base_point_value']
            #     return result
            
            # ESTRATEGIA 3: Buscar solo por fuente (fuente conocida)
            cursor.execute("""
                SELECT cs.*, cdt.name_chest, cdt.source_chest 
                FROM chest_score cs
                JOIN chest_def_translations cdt ON cs.id_score = cdt.id_score
                WHERE cdt.id_language = ? 
                AND (cdt.source_chest = ? OR cdt.source_chest LIKE ?)
                LIMIT 1
            """, (id_language, source, f"%{source}%"))
            
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                result['id_chest_def'] = result['id_score']
                result['chest_name'] = result['name_chest']
                result['chest_source'] = result['source_chest']
                result['point_value'] = result['base_point_value']
                return result
            
            # ESTRATEGIA 4: Fallback a inglés si no es inglés
            if language != 'en':
                cursor.execute("""
                    SELECT id_language FROM supported_languages 
                    WHERE code_language = 'en' AND is_active = 1
                """)
                en_lang = cursor.fetchone()
                
                if en_lang:
                    cursor.execute("""
                        SELECT cs.*, cdt.name_chest, cdt.source_chest 
                        FROM chest_score cs
                        JOIN chest_def_translations cdt ON cs.id_score = cdt.id_score
                        WHERE cdt.id_language = ? 
                        AND (
                            (cdt.name_chest = ? OR cdt.name_chest LIKE ?)
                            OR (cdt.source_chest = ? OR cdt.source_chest LIKE ?)
                        )
                        LIMIT 1
                    """, (en_lang['id_language'], name, f"%{name}%", source, f"%{source}%"))
                    
                    row = cursor.fetchone()
                    
                    if row:
                        result = dict(row)
                        result['id_chest_def'] = result['id_score']
                        result['chest_name'] = result['name_chest']
                        result['chest_source'] = result['source_chest']
                        result['point_value'] = result['base_point_value']
                        return result
            
            return None
            
        finally:
            self.pool.return_connection(conn)
    def create_chest_score(self, code_chest: str, points: int) -> int:
        """Create new chest score definition."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO chest_score (code_chest, base_point_value) 
                   VALUES (?, ?)""",
                (code_chest, points)
            )
            conn.commit()
            return cursor.lastrowid
            
        except sqlite3.IntegrityError:
            conn.rollback()
            # Already exists, fetch it
            cursor.execute(
                "SELECT id_score FROM chest_score WHERE code_chest = ?",
                (code_chest,)
            )
            return cursor.fetchone()['id_score']
        finally:
            self.pool.return_connection(conn)
    
    def add_chest_translation(self, id_score: int, language_code: str, 
                             name_chest: str, source_chest: str) -> bool:
        """Add translation for a chest."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            
            # Get language ID
            cursor.execute(
                "SELECT id_language FROM supported_languages WHERE code_language = ?",
                (language_code,)
            )
            lang_row = cursor.fetchone()
            if not lang_row:
                return False
            
            id_language = lang_row['id_language']
            
            cursor.execute("""
                INSERT OR REPLACE INTO chest_def_translations 
                (id_score, id_language, name_chest, source_chest) 
                VALUES (?, ?, ?, ?)
            """, (id_score, id_language, name_chest, source_chest))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to add chest translation: {str(e)}")
            return False
        finally:
            self.pool.return_connection(conn)
    
    def load_chest_scores_from_csv(self, csv_path: str) -> int:
        """Load chest scores from CSV file."""
        count = 0
        conn = self.pool.get_connection()
        
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            with open(csv_path, 'r', encoding='utf-8') as fp:
                lines = fp.readlines()
                
                # Detect format
                first_line = lines[0].strip().lower()
                has_header = any(x in first_line for x in ['type', 'name', 'source', 'points'])
                start_line = 1 if has_header else 0
                
                for line_num, line in enumerate(lines[start_line:], start=start_line+1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = [p.strip() for p in line.split(",")]
                    
                    try:
                        if len(parts) >= 4:
                            # New format: type, name, source, points
                            chest_type = parts[0]
                            chest_name = parts[1]
                            chest_source = parts[2]
                            points_match = re.search(r'(\d+)', parts[3])
                            points = int(points_match.group(1)) if points_match else 0
                            
                            # Generate code_chest
                            code_chest = f"{chest_type.lower()}_{chest_name.lower().replace(' ', '_')}_{chest_source.lower().replace(' ', '_')}"
                            
                        elif len(parts) >= 2:
                            # Old format: source, points
                            chest_source = parts[0]
                            points_match = re.search(r'(\d+)', parts[1])
                            points = int(points_match.group(1)) if points_match else 0
                            
                            # Use source as name
                            chest_name = chest_source
                            chest_type = "Crypt" if "crypt" in chest_source.lower() else "Citadel" if "citadel" in chest_source.lower() else "Other"
                            code_chest = chest_source.lower().replace(' ', '_')
                        
                        # Create or update chest score
                        cursor.execute("""
                            INSERT OR REPLACE INTO chest_score 
                            (code_chest, base_point_value, last_updated) 
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                        """, (code_chest, points))
                        
                        # Get id_score
                        if cursor.lastrowid:
                            id_score = cursor.lastrowid
                        else:
                            cursor.execute(
                                "SELECT id_score FROM chest_score WHERE code_chest = ?",
                                (code_chest,)
                            )
                            id_score = cursor.fetchone()['id_score']
                        
                        # Add English translation
                        cursor.execute("""
                            INSERT OR REPLACE INTO chest_def_translations 
                            (id_score, id_language, name_chest, source_chest) 
                            SELECT ?, id_language, ?, ?
                            FROM supported_languages 
                            WHERE code_language = 'en'
                        """, (id_score, chest_name, chest_source))
                        
                        count += 1
                        
                    except Exception as e:
                        self.logger.warning(f"Line {line_num}: Error {str(e)}")
                        continue
            
            conn.commit()
            self.logger.info(f"Loaded {count} chest scores from {csv_path}")
            return count
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to load chest scores: {str(e)}")
            raise
        finally:
            self.pool.return_connection(conn)
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    def create_session(self, id_clan: int, id_user: Optional[int] = None) -> int:
        """Create new capture session. Returns id_session."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO capture_sessions 
                   (id_clan, id_user, status, started_at)
                   VALUES (?, ?, 'active', ?)""",
                (id_clan, id_user, datetime.now())
            )
            conn.commit()
            session_id = cursor.lastrowid
            
            self.logger.info(f"Created session {session_id} for clan {id_clan}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to create session for clan {id_clan}: {str(e)}")
            raise
        finally:
            self.pool.return_connection(conn)
    
    def update_session_counter(self, id_session: int, increment: int = 1) -> None:
        """Increment chest counter for session."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE capture_sessions 
                   SET total_chests_captured = total_chests_captured + ?
                   WHERE id_session = ?""",
                (increment, id_session)
            )
            conn.commit()
        finally:
            self.pool.return_connection(conn)
    
    def close_session(self, id_session: int, status: str = 'completed', 
                    started_at: str = None, ended_at: str = None) -> None:
        """Close capture session with optional timestamps."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE capture_sessions 
                   SET status = ?, started_at = ?, ended_at = ?
                   WHERE id_session = ?""",
                (status, started_at, ended_at, id_session)
            )
            conn.commit()
            self.logger.info(f"Session {id_session} closed with status: {status}")
        finally:
            self.pool.return_connection(conn)
    
    def get_active_session(self, id_clan: int) -> Optional[Dict]:
        """Get active session for clan (if any)."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM capture_sessions 
                   WHERE id_clan = ? AND status = 'active'
                   ORDER BY session_date DESC LIMIT 1""",
                (id_clan,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            self.pool.return_connection(conn)
    
    # ========================================================================
    # CHEST REGISTRY (PRIMARY DATA)
    # ========================================================================
    
    def save_chest(self, language_code: str, chest_data: Dict[str, Any]) -> int:
        """
        Save chest record to database.
        
        Args:
            chest_data: {
                'id_clan': int,
                'id_player': int,
                'id_chest_def': int,  # id_score from chest_score
                'time_left': str,
                'obtained_at': Optional[datetime],
                'ocr_language_used': Optional[str],
                'id_session': Optional[int]
            }
        """
        conn = self.pool.get_connection()
        
        try:
            cursor = conn.cursor()
            
            # VERIFY ALL FOREIGN KEYS BEFORE INSERT
            errors = []
            
            # Check player exists
            cursor.execute("SELECT id_player FROM players WHERE id_player = ?", 
                        (chest_data['id_player'],))
            if not cursor.fetchone():
                errors.append(f"Player ID {chest_data['id_player']} not found in players table")
            
            # Check clan exists
            cursor.execute("SELECT id_clan FROM clans WHERE id_clan = ?", 
                        (chest_data['id_clan'],))
            if not cursor.fetchone():
                errors.append(f"Clan ID {chest_data['id_clan']} not found in clans table")
            
            # Check chest definition exists
            cursor.execute("SELECT id_score FROM chest_score WHERE id_score = ?", 
                        (chest_data['id_chest_def'],))
            if not cursor.fetchone():
                errors.append(f"Chest def ID {chest_data['id_chest_def']} not found in chest_score table")
            
            # Check session exists (if provided)
            if chest_data.get('id_session'):
                cursor.execute("SELECT id_session FROM capture_sessions WHERE id_session = ?", 
                            (chest_data['id_session'],))
                if not cursor.fetchone():
                    errors.append(f"Session ID {chest_data['id_session']} not found in capture_sessions table")
            
            if errors:
                error_msg = "Foreign key validation failed:\n" + "\n".join(errors)
                self.logger.error(error_msg)
                print(f"❌ [DB] {error_msg}")
                raise ValueError(error_msg)
            
            # Get points from chest_score
            cursor.execute(
                "SELECT base_point_value FROM chest_score WHERE id_score = ?",
                (chest_data['id_chest_def'],)
            )
            points_row = cursor.fetchone()
            points_awarded = points_row['base_point_value'] if points_row else 0
            
            # Now do the insert
            cursor.execute("""
                INSERT INTO chest_registers 
                (id_clan, id_player, id_chest_def, time_left, obtained_at, 
                ocr_language_used, points_awarded, id_session) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chest_data['id_clan'],
                chest_data['id_player'],
                chest_data['id_chest_def'],
                chest_data.get('time_left'),
                chest_data.get('obtained_at'),
                language_code,
                points_awarded,
                chest_data.get('id_session')
            ))
            
            conn.commit()
            chest_id = cursor.lastrowid
            
            # Update session counter
            if chest_data.get('id_session'):
                self.update_session_counter(chest_data['id_session'], 1)
            
            return chest_id
            
        except sqlite3.IntegrityError as e:
            conn.rollback()
            self.logger.error(f"IntegrityError during chest save: {str(e)}")
            # Print detailed info
            print(f"❌ [DB] IntegrityError: {e}")
            print(f"❌ [DB] Chest data attempted: {chest_data}")
            raise
        finally:
            self.pool.return_connection(conn)
        
    def bulk_insert_chests(self, chests: List[Dict]) -> int:
        """Bulk insert chest records (faster than individual inserts)."""
        if not chests:
            return 0
        
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            
            records = [
                (
                    c['id_clan'],
                    c['id_player'],
                    c['id_chest_def'],
                    c.get('time_left'),
                    c.get('obtained_at'),
                    c.get('id_session')
                )
                for c in chests
            ]
            
            cursor.executemany(
                """INSERT INTO chest_registers 
                   (id_clan, id_player, id_chest_def, time_left, obtained_at, id_session)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                records
            )
            conn.commit()
            
            count = len(chests)
            self.logger.info(f"Bulk inserted {count} chests")
            return count
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Bulk insert failed: {str(e)}")
            raise
        finally:
            self.pool.return_connection(conn)
    
    def get_chests_by_date(self, date: str, id_clan: int) -> List[Dict]:
        """Get all chests for specific date and clan."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT 
                    cr.*,
                    p.name_player,
                    cd.chest_name,
                    cd.chest_source,
                    cd.point_value
                   FROM chest_registers cr
                   JOIN players p ON cr.id_player = p.id_player
                   JOIN chest_score cd ON cr.id_chest_def = cd.id_score
                   WHERE date(cr.opened_at) = ? AND cr.id_clan = ?
                   ORDER BY cr.opened_at""",
                (date, id_clan)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            self.pool.return_connection(conn)
    
    def get_chests_by_session(self, id_session: int) -> List[Dict]:
        """Get all chests for specific session."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT 
                    cr.*,
                    p.name_player,
                    cd.chest_name,
                    cd.chest_source,
                    cd.point_value
                   FROM chest_registers cr
                   JOIN players p ON cr.id_player = p.id_player
                   JOIN chest_score cd ON cr.id_chest_def = cd.id_score
                   WHERE cr.id_session = ?
                   ORDER BY cr.opened_at""",
                (id_session,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            self.pool.return_connection(conn)
    # ========================================================================
    # OCR LANGUAGE PATTERNS
    # ========================================================================
    
    def get_ocr_patterns(self, language_code: str, keyword_type: str = None) -> List[Dict]:
        """Get OCR patterns for a language."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            
            if keyword_type:
                cursor.execute("""
                    SELECT * FROM ocr_language_patterns 
                    WHERE language_code = ? AND keyword_type = ?
                """, (language_code, keyword_type))
            else:
                cursor.execute("""
                    SELECT * FROM ocr_language_patterns 
                    WHERE language_code = ?
                """, (language_code,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            self.pool.return_connection(conn)
                
    # ========================================================================
    # OCR CORRECTION LOGGING
    # ========================================================================
    
    def log_correction(
        self,
        field_type: str,
        ocr_value: str,
        corrected_value: str,
        correction_source: str,
        id_session: Optional[int] = None
    ) -> int:
        """
        Log OCR correction for audit trail.
        
        Args:
            field_type: 'player' / 'chest' / 'source' / 'time'
            ocr_value: Raw OCR output
            corrected_value: Final validated value
            correction_source: 'fuzzy_match' / 'user_input' / 'alias' / 'heuristic'
            id_session: Optional session ID
        
        Returns:
            id_correction
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO ocr_corrections_history 
                   (id_session, field_type, ocr_value, corrected_value, correction_source)
                   VALUES (?, ?, ?, ?, ?)""",
                (id_session, field_type, ocr_value, corrected_value, correction_source)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            self.pool.return_connection(conn)
    
    # ========================================================================
    # REPORTING (READ-ONLY)
    # ========================================================================
    
    def generate_eod_report(self, date: str, id_clan: int) -> List[Dict]:
        """
        Generate end-of-day report (equivalent to FINAL.txt).
        
        Returns: [
            {'date': str, 'player': str, 'source': str, 'chest': str, 'score': int, 'clan': str},
            ...
        ]
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT 
                    date(cr.opened_at) AS date,
                    p.name_player AS player,
                    cd.chest_source AS source,
                    cd.chest_name AS chest,
                    cd.point_value AS score,
                    c.name_abbreviation AS clan
                   FROM chest_registers cr
                   JOIN players p ON cr.id_player = p.id_player
                   JOIN chest_score cd ON cr.id_chest_def = cd.id_score
                   JOIN clans c ON cr.id_clan = c.id_clan
                   WHERE date(cr.opened_at) = ? AND cr.id_clan = ?
                   ORDER BY cr.opened_at""",
                (date, id_clan)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            self.pool.return_connection(conn)
    
    def generate_player_summary(self, date: str, id_clan: int) -> List[Dict]:
        """
        Generate player summary report.
        
        Returns: [
            {'player': str, 'total_score': int, 'total_chests': int},
            ...
        ]
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT 
                    p.name_player AS player,
                    SUM(cd.point_value) AS total_score,
                    COUNT(*) AS total_chests
                   FROM chest_registers cr
                   JOIN players p ON cr.id_player = p.id_player
                   JOIN chest_score cd ON cr.id_chest_def = cd.id_score
                   WHERE date(cr.opened_at) = ? AND cr.id_clan = ?
                   GROUP BY p.name_player
                   ORDER BY total_score DESC""",
                (date, id_clan)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            self.pool.return_connection(conn)
    
    def generate_citadel_summary(
        self,
        start_date: str,
        end_date: str,
        id_clan: int
    ) -> List[Dict]:
        """
        Generate citadel summary report.
        
        Returns: [
            {'player': str, 'L10': int, 'L15': int, 'L20': int, 'L25': int, 
             'L30': int, 'Cursed_L20': int, 'Cursed_L25': int, 'total': int},
            ...
        ]
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT 
                    p.name_player AS player,
                    SUM(CASE WHEN cd.chest_source = 'Level 10 Citadel' THEN 1 ELSE 0 END) AS L10,
                    SUM(CASE WHEN cd.chest_source = 'Level 15 Citadel' THEN 1 ELSE 0 END) AS L15,
                    SUM(CASE WHEN cd.chest_source = 'Level 20 Citadel' THEN 1 ELSE 0 END) AS L20,
                    SUM(CASE WHEN cd.chest_source = 'Level 25 Citadel' THEN 1 ELSE 0 END) AS L25,
                    SUM(CASE WHEN cd.chest_source = 'Level 30 Citadel' THEN 1 ELSE 0 END) AS L30,
                    SUM(CASE WHEN cd.chest_source = 'Level 20 cursed Citadel' THEN 1 ELSE 0 END) AS Cursed_L20,
                    SUM(CASE WHEN cd.chest_source = 'Level 25 cursed Citadel' THEN 1 ELSE 0 END) AS Cursed_L25,
                    COUNT(*) AS total
                   FROM chest_registers cr
                   JOIN players p ON cr.id_player = p.id_player
                   JOIN chest_score cd ON cr.id_chest_def = cd.id_score
                   WHERE date(cr.opened_at) BETWEEN ? AND ?
                     AND cr.id_clan = ?
                     AND cd.chest_source LIKE '%Citadel%'
                   GROUP BY p.name_player
                   ORDER BY total DESC""",
                (start_date, end_date, id_clan)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            self.pool.return_connection(conn)
    
    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================
    
    def _warmup_cache(self) -> None:
        """
        Preload frequently accessed data into cache.
        
        Now filters chest_def_translations by the instance's language setting.
        """
        try:
            # Cache all clans
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clans")
            for row in cursor.fetchall():
                clan = dict(row)
                self._cache[f"clan_abbr_{clan['name_abbreviation']}"] = clan
            
            # Cache active chest scores
            cursor.execute("SELECT * FROM chest_score WHERE is_active = 1")
            for row in cursor.fetchall():
                chest = dict(row)
                self._cache[f"chest_code_{chest['code_chest']}"] = chest
            
            # ✅ NEW: Cache chest translations filtered by language
            # This implements the requested feature
            try:
                cursor.execute("""
                    SELECT *
                    FROM chest_def_translations
                    WHERE id_language = (
                        SELECT id_language 
                        FROM supported_languages 
                        WHERE code_language = ?
                    )
                """, (self.language,))
                
                translation_count = 0
                for row in cursor.fetchall():
                    translation = dict(row)
                    cache_key = f"translation_{translation['chest_name']}_{translation['chest_source']}_{self.language}"
                    self._cache[cache_key] = translation
                    translation_count += 1
                
                print(f"### [DB] Loaded {translation_count} translations for language: {self.language}")
            except Exception as trans_error:
                print(f"### [DB] Warning: Could not load translations: {trans_error}")
            
            self.pool.return_connection(conn)
            print(f"### [DB] Cache warmed: {len(self._cache)} entries")
            self.logger.info(f"Cache warmed with {len(self._cache)} entries")
        except Exception as e:
            self.logger.warning(f"Cache warmup failed: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        with self._cache_lock:
            self._cache.clear()
        self._warmup_cache()
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def execute_raw_query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute raw SQL query (use with caution)."""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            self.pool.return_connection(conn)
    
    def backup_database(self, backup_path: str) -> bool:
        """Create backup of database file."""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}")
            return False
    
    def close(self) -> None:
        """Close all database connections."""
        if self.pool:
            self.pool.close_all()
            self.logger.info("Database connections closed")


# ============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ============================================================================

def get_database_instance(
    db_path: str = 'data/databases/TB_chests_clans.db',
    language: str = 'en'
) -> TBDatabaseManager:
    """
    Get singleton database instance.
    
    Usage:
        from TBDatabase_manager import get_database_instance
        
        db = get_database_instance(language='es')
        db.initialize()
    
    Args:
        db_path: Path to the SQLite database file
        language: Language code for chest translations (default: 'en')
    """
    return TBDatabaseManager(db_path, language)