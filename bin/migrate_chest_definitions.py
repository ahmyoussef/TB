"""
migrate_multilingual_chests.py

Migración de datos desde archivos CSV a chest_score + chest_def_translations
Inserta tanto inglés como español en una sola ejecución

Autor: TB Team
Fecha: 2026-01-27
"""

import sys
import os
import re
import csv
import sqlite3
from datetime import datetime
from pathlib import Path

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

DB_PATH = '../data/databases/TB_chests_clans.db'
EN_CSV_PATH = '../config/scores-hlo_en.csv'
ES_CSV_PATH = '../config/scores-hlo_es.csv'

# IDs de idiomas (deben existir en supported_languages)
ID_LANGUAGE_EN = 1  # Inglés
ID_LANGUAGE_ES = 2  # Español

# ============================================================================
# FUNCIONES HELPER
# ============================================================================

def generate_code_chest(chest_source):
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

def parse_csv_line(line):
    """
    Parsea una línea CSV que puede tener comas dentro del campo source.
    """
    line = line.strip()
    if not line:
        return None
    
    # Caso simple: 3 comas exactas
    if line.count(',') == 3:
        parts = line.split(',', 3)
        return {
            'Type': parts[0].strip(),
            'Name': parts[1].strip(),
            'Source': parts[2].strip(),
            'Points': parts[3].strip()
        }
    
    # Caso complejo: source tiene comas
    # Buscar última coma (puntos)
    last_comma = line.rfind(',')
    if last_comma == -1:
        return None
    
    points = line[last_comma + 1:].strip()
    
    # Encontrar primera coma
    first_comma = line.find(',')
    if first_comma == -1:
        return None
    
    tipo = line[:first_comma].strip()
    
    # Encontrar segunda coma
    rest = line[first_comma + 1:last_comma]
    second_comma = rest.find(',')
    if second_comma == -1:
        return None
    
    nombre = rest[:second_comma].strip()
    source = rest[second_comma + 1:].strip()
    
    return {
        'Type': tipo,
        'Name': nombre,
        'Source': source,
        'Points': points
    }

def read_csv_file(filepath):
    """Lee un archivo CSV y devuelve los registros."""
    records = []
    
    if not os.path.exists(filepath):
        print(f"❌ ERROR: Archivo no encontrado: {filepath}")
        return records
    
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        print(f"📖 Leyendo {os.path.basename(filepath)}: {len(lines)} líneas")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or i == 0:  # Saltar encabezado
                continue
            
            record = parse_csv_line(line)
            if record:
                records.append(record)
    
    except Exception as e:
        print(f"❌ Error leyendo {filepath}: {e}")
    
    return records

# ============================================================================
# MIGRACIÓN PRINCIPAL (FUNCIÓN ACTUALIZADA)
# ============================================================================

def migrate_multilingual_chests(db_path='../data/databases/TB_chests_clans.db', 
                               en_csv_path='../config/scores-hlo_en.csv',
                               es_csv_path='../config/scores-hlo_es.csv',
                               dry_run=True):
    """
    Migra datos desde archivos CSV a chest_score + chest_def_translations.
    Inserta tanto inglés como español.
    """
    
    print("\n" + "="*80)
    print("MULTILINGUAL CHEST MIGRATION")
    print("="*80)
    print(f"Database    : {db_path}")
    print(f"English CSV : {en_csv_path}")
    print(f"Spanish CSV : {es_csv_path}")
    print(f"Mode        : {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    print("="*80 + "\n")
    
    # ========================================================================
    # PASO 1: Leer archivos CSV
    # ========================================================================
    
    print("### [STEP 1] Reading CSV files...\n")
    
    records_en = read_csv_file(en_csv_path)
    records_es = read_csv_file(es_csv_path)
    
    if not records_en or not records_es:
        print("❌ No se pudieron leer los archivos CSV")
        return False
    
    print(f"✅ Registros inglés: {len(records_en)}")
    print(f"✅ Registros español: {len(records_es)}")
    
    min_records = min(len(records_en), len(records_es))
    if len(records_en) != len(records_es):
        print(f"⚠️  ADVERTENCIA: Diferente número de registros")
        print(f"   Procesando {min_records} registros coincidentes")
    
    print()
    
    # ========================================================================
    # PASO 2: Conectar a base de datos
    # ========================================================================
    
    print("### [STEP 2] Connecting to database...\n")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        print("✅ Conexión establecida")
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {e}")
        return False
    
    # Verificar tablas
    required_tables = ['chest_score', 'chest_def_translations', 'supported_languages']
    for table in required_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone():
            print(f"❌ ERROR: Tabla '{table}' no encontrada")
            conn.close()
            return False
        print(f"✅ Tabla encontrada: {table}")
    
    # Verificar IDs de idioma
    print("\n🔍 Verificando IDs de idioma...")
    cursor.execute("SELECT id_language FROM supported_languages WHERE id_language IN (?, ?)", 
                   (ID_LANGUAGE_EN, ID_LANGUAGE_ES))
    langs = cursor.fetchall()
    if len(langs) != 2:
        print(f"❌ ERROR: Idiomas no encontrados (esperados ID 1 y 2)")
        conn.close()
        return False
    print(f"✅ Idiomas verificados: Inglés (ID={ID_LANGUAGE_EN}), Español (ID={ID_LANGUAGE_ES})")
    
    print()
    
    # ========================================================================
    # PASO 3: Procesar registros
    # ========================================================================
    
    print("### [STEP 3] Processing records...\n")
    
    stats = {
        'chest_score_created': 0,
        'chest_score_existing': 0,
        'translations_en': 0,
        'translations_es': 0,
        'errors': 0
    }
    
    for i in range(min_records):
        rec_en = records_en[i]
        rec_es = records_es[i]
        
        chest_name_en = rec_en['Name']
        chest_source_en = rec_en['Source']
        chest_points = rec_en['Points']
        
        chest_name_es = rec_es['Name']
        chest_source_es = rec_es['Source']
        
        print(f"[{i+1}/{min_records}] {chest_name_en[:30]}...")
        
        try:
            # Generar code_chest desde source inglés
            code_chest = generate_code_chest(chest_source_en)
            print(f"    Code: {code_chest}")
            
            if dry_run:
                # Solo mostrar
                print(f"    [DRY RUN] chest_score: {code_chest} ({chest_points} pts)")
                print(f"    [DRY RUN] EN: '{chest_name_en[:30]}...'")
                print(f"    [DRY RUN] ES: '{chest_name_es[:30]}...'")
                
                stats['chest_score_created'] += 1
                stats['translations_en'] += 1
                stats['translations_es'] += 1
                
            else:
                # Modo real
                # 1. Insertar o obtener chest_score
                cursor.execute("SELECT id_score FROM chest_score WHERE code_chest = ?", (code_chest,))
                result = cursor.fetchone()
                
                if result:
                    id_score = result['id_score']
                    stats['chest_score_existing'] += 1
                else:
                    cursor.execute("""
                        INSERT INTO chest_score 
                        (code_chest, base_point_value, is_active, created_at, last_updated)
                        VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (code_chest, int(chest_points)))
                    id_score = cursor.lastrowid
                    stats['chest_score_created'] += 1
                
                # 2. Insertar traducción inglés
                try:
                    cursor.execute("""
                        INSERT INTO chest_def_translations 
                        (id_score, id_language, name_chest, source_chest, created_at, last_updated)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (id_score, ID_LANGUAGE_EN, chest_name_en, chest_source_en))
                    stats['translations_en'] += 1
                    print(f"    ✅ EN insertado")
                except sqlite3.IntegrityError:
                    print(f"    ⚠️  EN ya existe")
                
                # 3. Insertar traducción español
                try:
                    cursor.execute("""
                        INSERT INTO chest_def_translations 
                        (id_score, id_language, name_chest, source_chest, created_at, last_updated)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (id_score, ID_LANGUAGE_ES, chest_name_es, chest_source_es))
                    stats['translations_es'] += 1
                    print(f"    ✅ ES insertado")
                except sqlite3.IntegrityError:
                    print(f"    ⚠️  ES ya existe")
        
        except Exception as e:
            print(f"    ❌ ERROR: {e}")
            stats['errors'] += 1
        
        print()
    
    # ========================================================================
    # PASO 4: Guardar y mostrar resultados
    # ========================================================================
    
    if not dry_run:
        try:
            conn.commit()
            print("✅ Cambios guardados en la base de datos")
        except Exception as e:
            print(f"❌ Error guardando cambios: {e}")
            conn.rollback()
    
    conn.close()
    
    # Resumen
    print("\n" + "="*80)
    print("MIGRATION SUMMARY")
    print("="*80)
    print(f"Registros procesados      : {min_records}")
    print(f"Chest_score nuevos        : {stats['chest_score_created']}")
    print(f"Chest_score existentes    : {stats['chest_score_existing']}")
    print(f"Traducciones inglés       : {stats['translations_en']}")
    print(f"Traducciones español      : {stats['translations_es']}")
    print(f"Errores                   : {stats['errors']}")
    print("="*80 + "\n")
    
    # Guardar log
    log_file = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Fecha: {datetime.now()}\n")
        f.write(f"Base de datos: {db_path}\n")
        f.write(f"Registros: {min_records}\n")
        f.write(f"Errores: {stats['errors']}\n")
        f.write(f"Log guardado en: {log_file}\n")
    
    print(f"✅ Log guardado en: {log_file}")
    
    return stats['errors'] == 0

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def test_code_generation():
    """Tests para verificar generación de códigos"""
    
    test_cases = [
        ("Level 20 Citadel", "citadel_20"),
        ("Level 25 cursed Citadel", "cursed_citadel_25"),
        ("Level 10-14 Crypt", "crypt_10-14"),
        ("Level 10-14 Vault of the Ancients", "vault_of_the_ancients_10-14"),
        ("Bank", "bank"),
        ("Clash for the Throne tournament", "clash_for_the_throne_tournament"),
        ("Hermes' Store", "hermes_store"),
        ("Pumpkin", "pumpkin"),
        ("Level 5 Monster", "monster_5"),
    ]
    
    print("\n" + "="*80)
    print("CODE GENERATION TESTS")
    print("="*80 + "\n")
    
    passed = 0
    failed = 0
    
    for chest_source, expected in test_cases:
        result = generate_code_chest(chest_source)
        
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        print(f"{status}")
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

def check_csv_alignment(en_csv_path='../config/scores-hlo_en.csv', 
                       es_csv_path='../config/scores-hlo_es.csv'):
    """
    Verifica que los archivos CSV estén alineados (mismo orden).
    """
    print("\n" + "="*80)
    print("CSV ALIGNMENT CHECK")
    print("="*80 + "\n")
    
    records_en = read_csv_file(en_csv_path)
    records_es = read_csv_file(es_csv_path)
    
    if not records_en or not records_es:
        return False
    
    min_len = min(len(records_en), len(records_es))
    print(f"Verificando primeros {min_len} registros...\n")
    
    mismatches = 0
    for i in range(min(10, min_len)):  # Solo primeros 10
        rec_en = records_en[i]
        rec_es = records_es[i]
        
        if rec_en['Points'] != rec_es['Points']:
            print(f"❌ MISMATCH #{i+1}:")
            print(f"   EN: {rec_en['Name'][:30]}... ({rec_en['Points']} pts)")
            print(f"   ES: {rec_es['Name'][:30]}... ({rec_es['Points']} pts)")
            mismatches += 1
    
    if mismatches > 0:
        print(f"\n⚠️  Encontrados {mismatches} desajustes")
        return False
    else:
        print("✅ Los archivos CSV están alineados correctamente")
        return True

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migrate chest data from CSV files to multilingual schema'
    )
    
    parser.add_argument('--test', action='store_true', 
                       help='Run code generation tests')
    parser.add_argument('--check', action='store_true',
                       help='Check CSV file alignment')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Dry run mode (default)')
    parser.add_argument('--live', action='store_false', dest='dry_run',
                       help='Live mode (execute migration)')
    parser.add_argument('--db', default='../data/databases/TB_chests_clans.db',
                       help='Database path')
    parser.add_argument('--en-csv', default='../config/scores-hlo_en.csv',
                       help='English CSV path')
    parser.add_argument('--es-csv', default='../config/scores-hlo_es.csv',
                       help='Spanish CSV path')
    
    args = parser.parse_args()
    
    if args.test:
        # Ejecutar tests
        success = test_code_generation()
        sys.exit(0 if success else 1)
    
    elif args.check:
        # Verificar alineación de CSV
        success = check_csv_alignment(args.en_csv, args.es_csv)
        sys.exit(0 if success else 1)
    
    else:
        # Ejecutar migración
        if args.dry_run:
            print("\n⚠️  DRY RUN MODE - No changes will be made")
            print("    Run with --live to execute migration\n")
        else:
            print("\n⚠️  LIVE MODE - Database will be modified!")
            print("    Database:", args.db)
            print("    English CSV:", args.en_csv)
            print("    Spanish CSV:", args.es_csv)
            response = input("\n    Continue? [y/N]: ")
            if response.lower() != 'y':
                print("    Aborted.")
                sys.exit(0)
        
        # Llamar a la función con todos los argumentos
        success = migrate_multilingual_chests(
            db_path=args.db,
            en_csv_path=args.en_csv,
            es_csv_path=args.es_csv,
            dry_run=args.dry_run
        )
        sys.exit(0 if success else 1)
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migrate chest data from CSV files to multilingual schema'
    )
    
    parser.add_argument('--test', action='store_true', 
                       help='Run code generation tests')
    parser.add_argument('--check', action='store_true',
                       help='Check CSV file alignment')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Dry run mode (default)')
    parser.add_argument('--live', action='store_false', dest='dry_run',
                       help='Live mode (execute migration)')
    parser.add_argument('--db', default='../data/databases/TB_chests_clans.db',
                       help='Database path')
    parser.add_argument('--en-csv', default='../config/scores-hlo_en.csv',  # CORREGIDO
                       help='English CSV path')
    parser.add_argument('--es-csv', default='../config/scores-hlo_es.csv',  # CORREGIDO
                       help='Spanish CSV path')
    
    args = parser.parse_args()
    
    # Usar las rutas proporcionadas por argumentos
    DB_PATH = args.db
    EN_CSV_PATH = args.en_csv
    ES_CSV_PATH = args.es_csv
    
    if args.test:
        # Ejecutar tests
        success = test_code_generation()
        sys.exit(0 if success else 1)
    
    elif args.check:
        # Verificar alineación de CSV
        success = check_csv_alignment()
        sys.exit(0 if success else 1)
    
    else:
        # Ejecutar migración
        if args.dry_run:
            print("\n⚠️  DRY RUN MODE - No changes will be made")
            print("    Run with --live to execute migration\n")
        else:
            print("\n⚠️  LIVE MODE - Database will be modified!")
            print("    Database:", DB_PATH)
            print("    English CSV:", EN_CSV_PATH)
            print("    Spanish CSV:", ES_CSV_PATH)
            response = input("\n    Continue? [y/N]: ")
            if response.lower() != 'y':
                print("    Aborted.")
                sys.exit(0)
        
        # Pasar las rutas como argumentos a la función
        success = migrate_multilingual_chests(
            db_path=DB_PATH,
            en_csv_path=EN_CSV_PATH,
            es_csv_path=ES_CSV_PATH,
            dry_run=args.dry_run
        )
        sys.exit(0 if success else 1)