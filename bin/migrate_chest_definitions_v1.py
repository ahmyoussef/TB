"""
migrate_chest_definitions.py

Migración de datos de chest_definitions (tabla antigua monolítica)
a chest_score + chest_def_translations (nuevo diseño multiidioma)

Autor: TB Team
Fecha: 2026-01-26
"""

import sys
import os
import re
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from TBDatabase_manager import TBDatabaseManager

# ============================================================================
# FUNCIONES HELPER
# ============================================================================

def generate_code_chest(chest_name, chest_source):
    """
    Generar code_chest basado ÚNICAMENTE en el source_chest.
    
    REGLAS SIMPLES:
    1. Tomar el source_chest
    2. Convertir a minúsculas
    3. Reemplazar espacios por guiones bajos "_"
    4. Si tiene "Level X" o "lvl X", remover la palabra y poner el número al final
    
    Ejemplos:
        "Level 20 Citadel" → "citadel_20"
        "Level 25 cursed Citadel" → "cursed_citadel_25"
        "Level 10-14 Crypt" → "crypt_10-14"
        "Level 10-14 Vault of the Ancients" → "vault_of_the_ancients_10-14"
        "Bank" → "bank"
        "Hermes' Store" → "hermes_store"
        "Pumpkin" → "pumpkin"
        "Level 5 Monster" → "monster_5"
        "Clash for the Throne tournament" → "clash_for_the_throne_tournament"
    """
    
    # Tomar el source y convertir a minúsculas
    code = chest_source.lower().strip()
    
    # ========================================================================
    # PASO 1: Extraer nivel si existe
    # ========================================================================
    level = None
    
    # Buscar patrones: "level X", "level X-Y", "lvl X", "lvl. X"
    level_patterns = [
        r'level\s+(\d+(?:-\d+)?)',   # "level 20" o "level 10-14"
        r'lvl\.?\s+(\d+(?:-\d+)?)',  # "lvl 20" o "lvl. 10-14"
    ]
    
    for pattern in level_patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            level = match.group(1)
            # Remover "level X" o "lvl X" del texto
            code = re.sub(pattern, '', code, flags=re.IGNORECASE).strip()
            break
    
    # ========================================================================
    # PASO 2: Limpiar caracteres especiales
    # ========================================================================
    
    # Remover apóstrofes y comillas
    code = code.replace("'", "").replace("'", "").replace('"', '')
    
    # Remover otros caracteres especiales, dejar solo letras, números, espacios y guiones
    code = re.sub(r'[^\w\s\-]', '', code)
    
    # ========================================================================
    # PASO 3: Convertir espacios a guiones bajos
    # ========================================================================
    
    code = code.replace(' ', '_')
    
    # ========================================================================
    # PASO 4: Limpiar guiones bajos múltiples
    # ========================================================================
    
    code = re.sub(r'_+', '_', code)  # Múltiples _ → uno solo
    code = code.strip('_')           # Remover _ al inicio/fin
    
    # ========================================================================
    # PASO 5: Agregar nivel al final si existe
    # ========================================================================
    
    if level:
        code = f"{code}_{level}"
    
    return code
def test_code_generation():
    """Tests para verificar generación de códigos"""
    
    test_cases = [
        # (chest_name, chest_source, expected_code)
        ("Elven Citadel Chest", "Level 20 Citadel", "elven_citadel_20"),
        ("Cursed Citadel Chest", "Level 25 cursed Citadel", "cursed_citadel_25"),
        ("Crypt Chest", "Level 10-14 Crypt", "crypt_10-14"),
        ("Vault Chest", "Level 10-14 Vault of the Ancients", "vault_of_the_ancients_10-14"),
        ("Bank Chest", "Bank", "bank"),
        ("Clash for the Throne Chest", "Clash for the Throne tournament", "clash_for_the_throne"),
        ("Hermes Chest", "Hermes' Store", "hermes_store"),
        ("Epic Jack Reaper Chest", "Pumpkin", "epic_chest"),
        ("Monster Chest", "Level 5 Monster", "chest_5"),
    ]
    
    print("\n" + "="*80)
    print("TESTING CODE GENERATION")
    print("="*80 + "\n")
    
    passed = 0
    failed = 0
    
    for chest_name, chest_source, expected in test_cases:
        result = generate_code_chest(chest_name, chest_source)
        
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        print(f"{status}")
        print(f"  Name  : {chest_name}")
        print(f"  Source: {chest_source}")
        print(f"  Got   : {result}")
        if result != expected:
            print(f"  Expect: {expected}")
        print()
        
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print(f"{'='*80}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    print(f"{'='*80}\n")
    
    return failed == 0


# ============================================================================
# MIGRACIÓN PRINCIPAL
# ============================================================================

def migrate_chest_definitions(db_path='../data/databases/TB_chests_clans.db', dry_run=True):
    """
    Migrar datos de chest_definitions a chest_score + chest_def_translations
    
    Args:
        db_path: Ruta a la base de datos
        dry_run: Si True, solo muestra lo que haría sin modificar BD
    """
    
    print("\n" + "="*80)
    print("CHEST DEFINITIONS MIGRATION")
    print("="*80)
    print(f"Database : {db_path}")
    print(f"Mode     : {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print("="*80 + "\n")
    
    # Conectar a BD
    db = TBDatabaseManager(db_path=db_path)
    db.initialize()
    
    # ========================================================================
    # PASO 1: Verificar que existen las tablas necesarias
    # ========================================================================
    
    print("### [STEP 1] Checking tables...\n")
    
    # Verificar chest_definitions existe
    old_table_check = db.execute_raw_query("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='chest_definitions'
    """)
    
    if not old_table_check:
        print("❌ ERROR: Table 'chest_definitions' does not exist!")
        print("   Nothing to migrate.")
        return False
    
    print("✅ Found table: chest_definitions")
    
    # Verificar nuevas tablas existen
    new_tables = ['chest_score', 'chest_def_translations', 'supported_languages']
    
    for table in new_tables:
        check = db.execute_raw_query(f"""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='{table}'
        """)
        
        if not check:
            print(f"❌ ERROR: Table '{table}' does not exist!")
            print(f"   Please run database initialization first.")
            return False
        
        print(f"✅ Found table: {table}")
    
    print()
    
    # ========================================================================
    # PASO 2: Obtener ID del idioma inglés (default)
    # ========================================================================
    
    print("### [STEP 2] Getting language IDs...\n")
    
    en_lang = db.execute_raw_query("""
        SELECT id_language FROM supported_languages 
        WHERE code_language = 'en'
    """)
    
    if not en_lang:
        print("❌ ERROR: English language not found in supported_languages!")
        print("   Please insert it first:")
        print("   INSERT INTO supported_languages (code_language, name_language, is_default)")
        print("   VALUES ('en', 'English', 1);")
        return False
    
    id_language_en = en_lang[0]['id_language']
    print(f"✅ English language ID: {id_language_en}")
    print()
    
    # ========================================================================
    # PASO 3: Leer datos de chest_definitions
    # ========================================================================
    
    print("### [STEP 3] Reading chest_definitions...\n")
    
    old_chests = db.execute_raw_query("""
        SELECT * FROM chest_definitions 
        ORDER BY id_chest_def
    """)
    
    print(f"✅ Found {len(old_chests)} chest definitions to migrate")
    print()
    
    # ========================================================================
    # PASO 4: Migrar datos
    # ========================================================================
    
    print("### [STEP 4] Migrating data...\n")
    
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    migration_log = []
    
    for i, chest in enumerate(old_chests, 1):
        id_chest_def = chest['id_chest_def']
        chest_type = chest['chest_type']
        chest_name = chest['chest_name']
        chest_source = chest['chest_source']
        point_value = chest['point_value']
        
        print(f"[{i}/{len(old_chests)}] Processing: {chest_name} | {chest_source} ({point_value} pts)")
        
        try:
            # Generar code_chest
            code_chest = generate_code_chest(chest_name, chest_source)
            print(f"    Generated code: {code_chest}")
            
            if dry_run:
                # Solo mostrar lo que haría
                print(f"    [DRY RUN] Would insert into chest_score:")
                print(f"              code_chest={code_chest}, points={point_value}")
                print(f"    [DRY RUN] Would insert into chest_def_translations:")
                print(f"              name={chest_name}, source={chest_source}")
                
                migration_log.append({
                    'id_old': id_chest_def,
                    'code_chest': code_chest,
                    'name': chest_name,
                    'source': chest_source,
                    'points': point_value,
                    'status': 'would_migrate'
                })
                
                migrated_count += 1
                
            else:
                # Migración real
                conn = db.pool.get_connection()
                cursor = conn.cursor()
                
                try:
                    # Insertar en chest_score
                    cursor.execute("""
                        INSERT OR IGNORE INTO chest_score 
                        (code_chest, base_point_value, is_active, created_at, last_updated)
                        VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (code_chest, point_value))
                    
                    # Obtener id_score
                    cursor.execute("""
                        SELECT id_score FROM chest_score WHERE code_chest = ?
                    """, (code_chest,))
                    
                    score_row = cursor.fetchone()
                    id_score = score_row['id_score']
                    
                    # Insertar traducción en inglés
                    cursor.execute("""
                        INSERT OR IGNORE INTO chest_def_translations 
                        (id_score, id_language, name_chest, source_chest, created_at, last_updated)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (id_score, id_language_en, chest_name, chest_source))
                    
                    conn.commit()
                    
                    print(f"    ✅ Migrated successfully (id_score={id_score})")
                    
                    migration_log.append({
                        'id_old': id_chest_def,
                        'id_score': id_score,
                        'code_chest': code_chest,
                        'name': chest_name,
                        'source': chest_source,
                        'points': point_value,
                        'status': 'migrated'
                    })
                    
                    migrated_count += 1
                    
                except sqlite3.IntegrityError as e:
                    conn.rollback()
                    print(f"    ⚠️  Skipped (already exists): {e}")
                    
                    migration_log.append({
                        'id_old': id_chest_def,
                        'code_chest': code_chest,
                        'name': chest_name,
                        'source': chest_source,
                        'points': point_value,
                        'status': 'skipped',
                        'error': str(e)
                    })
                    
                    skipped_count += 1
                    
                finally:
                    db.pool.return_connection(conn)
        
        except Exception as e:
            print(f"    ❌ ERROR: {e}")
            
            migration_log.append({
                'id_old': id_chest_def,
                'name': chest_name,
                'source': chest_source,
                'status': 'error',
                'error': str(e)
            })
            
            error_count += 1
        
        print()
    
    # ========================================================================
    # PASO 5: Resumen
    # ========================================================================
    
    print("\n" + "="*80)
    print("MIGRATION SUMMARY")
    print("="*80)
    print(f"Total chests processed : {len(old_chests)}")
    print(f"Successfully migrated  : {migrated_count}")
    print(f"Skipped (duplicates)   : {skipped_count}")
    print(f"Errors                 : {error_count}")
    print("="*80 + "\n")
    
    # Guardar log
    if not dry_run:
        log_file = f"migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("CHEST DEFINITIONS MIGRATION LOG\n")
            f.write("="*80 + "\n")
            f.write(f"Date: {datetime.now()}\n")
            f.write(f"Total: {len(old_chests)}\n")
            f.write(f"Migrated: {migrated_count}\n")
            f.write(f"Skipped: {skipped_count}\n")
            f.write(f"Errors: {error_count}\n")
            f.write("="*80 + "\n\n")
            
            for entry in migration_log:
                f.write(f"ID: {entry.get('id_old')}\n")
                f.write(f"  Code    : {entry.get('code_chest', 'N/A')}\n")
                f.write(f"  Name    : {entry.get('name', 'N/A')}\n")
                f.write(f"  Source  : {entry.get('source', 'N/A')}\n")
                f.write(f"  Points  : {entry.get('points', 'N/A')}\n")
                f.write(f"  Status  : {entry.get('status')}\n")
                if 'error' in entry:
                    f.write(f"  Error   : {entry['error']}\n")
                f.write("\n")
        
        print(f"✅ Migration log saved to: {log_file}")
    
    return error_count == 0


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate chest_definitions to new multilingual schema')
    parser.add_argument('--db', default='../data/databases/TB_chests_clans.db', help='Database path')
    parser.add_argument('--test', action='store_true', help='Run code generation tests')
    parser.add_argument('--live', action='store_true', help='Execute migration (default is dry-run)')
    
    args = parser.parse_args()
    
    if args.test:
        # Ejecutar tests
        success = test_code_generation()
        sys.exit(0 if success else 1)
    else:
        # Ejecutar migración
        dry_run = not args.live
        
        if dry_run:
            print("\n⚠️  DRY RUN MODE - No changes will be made")
            print("    Run with --live to execute migration\n")
        else:
            print("\n⚠️  LIVE MODE - Database will be modified!")
            response = input("    Continue? [y/N]: ")
            if response.lower() != 'y':
                print("    Aborted.")
                sys.exit(0)
        
        success = migrate_chest_definitions(args.db, dry_run=dry_run)
        sys.exit(0 if success else 1)