import sqlite3
import re
import os

# Configuración
DB_PATH = '../data/databases/TB_chests_clans.db'
EN_CSV_PATH = '../config/scores-hlo_en.csv'  # Archivo inglés para referencia
ES_CSV_PATH = '../config/scores-hlo_es.csv'
ID_LANGUAGE_SPANISH = 2

def normalize_source_for_matching(source):
    """Normaliza source para matching (quita niveles)"""
    norm = source.lower().strip()
    
    # Remover información de nivel
    norm = re.sub(r'(?:level|lvl|nivel)\s+\d+(?:-\d+)?', '', norm, flags=re.IGNORECASE)
    
    # Limpiar
    norm = re.sub(r'[^\w\s]', '', norm)
    norm = ' '.join(norm.split())  # Normalizar espacios
    return norm

def generate_code_chest_from_english(source_en):
    """Genera code_chest a partir del source en inglés"""
    code = source_en.lower().strip()
    
    # Extraer nivel
    level_match = re.search(r'(?:level|lvl)\s+(\d+(?:-\d+)?)', code, re.IGNORECASE)
    if level_match:
        level = level_match.group(1)
        code = re.sub(r'(?:level|lvl)\s+\d+(?:-\d+)?', '', code, flags=re.IGNORECASE)
    
    # Limpiar
    code = code.strip()
    code = code.replace("'", "").replace('"', '')
    code = re.sub(r'[^\w\s\-]', '', code)
    code = code.replace(' ', '_')
    code = re.sub(r'_+', '_', code)
    code = code.strip('_')
    
    if level_match:
        code = f"{code}_{level}"
    
    return code

def read_csv_as_dict(filepath, is_spanish=False):
    """Lee CSV y crea un diccionario con clave compuesta"""
    records = []
    key_to_record = {}
    
    if not os.path.exists(filepath):
        print(f"ERROR: Archivo no encontrado: {filepath}")
        return records, key_to_record
    
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        header_skipped = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Saltar encabezado
            if not header_skipped:
                header_skipped = True
                continue
            
            # Manejar líneas con comas en el source
            parts = []
            in_quotes = False
            current_part = []
            
            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    parts.append(''.join(current_part).strip())
                    current_part = []
                else:
                    current_part.append(char)
            
            parts.append(''.join(current_part).strip())
            
            # Limpiar comillas
            parts = [p.replace('"', '') for p in parts]
            
            if len(parts) >= 4:
                record = {
                    'Type': parts[0],
                    'Name': parts[1],
                    'Source': parts[2],
                    'Points': parts[3]
                }
                records.append(record)
                
                # Crear clave única
                # Para español: Tipo + Nombre + Source normalizado
                # Para inglés: Tipo + Name + Source normalizado
                norm_source = normalize_source_for_matching(parts[2])
                key = f"{parts[0]}_{parts[1]}_{norm_source}_{parts[3]}"
                key_to_record[key] = record
    
    except Exception as e:
        print(f"Error leyendo {filepath}: {e}")
        # Método simple de respaldo
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines[1:], start=1):
                line = line.strip()
                if line:
                    # Método simple: dividir por la última coma para puntos
                    if line.count(',') >= 3:
                        # Encontrar la última coma para separar puntos
                        last_comma = line.rfind(',')
                        points = line[last_comma+1:].strip()
                        rest = line[:last_comma]
                        
                        # Encontrar penúltima coma para separar source
                        second_last = rest.rfind(',')
                        if second_last != -1:
                            source = rest[second_last+1:].strip()
                            name_type = rest[:second_last]
                            
                            # Primera coma para separar tipo y nombre
                            first_comma = name_type.find(',')
                            if first_comma != -1:
                                tipo = name_type[:first_comma].strip()
                                nombre = name_type[first_comma+1:].strip()
                                
                                record = {
                                    'Type': tipo,
                                    'Name': nombre,
                                    'Source': source,
                                    'Points': points
                                }
                                records.append(record)
        except Exception as e2:
            print(f"Error también con método simple: {e2}")
    
    return records, key_to_record

def main():
    print("=== INSERCIÓN CON MATCHING MEJORADO ===\n")
    
    # 1. Leer ambos archivos
    print("Leyendo archivos CSV...")
    records_en, en_dict = read_csv_as_dict(EN_CSV_PATH, is_spanish=False)
    records_es, es_dict = read_csv_as_dict(ES_CSV_PATH, is_spanish=True)
    
    print(f"Registros inglés: {len(records_en)}")
    print(f"Registros español: {len(records_es)}")
    print(f"Claves únicas inglés: {len(en_dict)}")
    print(f"Claves únicas español: {len(es_dict)}")
    
    # 2. Crear mapa para matching
    # Estrategia: crear una clave normalizada para cada registro
    en_by_normalized_key = {}
    for rec in records_en:
        # Crear clave normalizada: Type + Name (normalizado) + Source (sin nivel) + Points
        norm_name = rec['Name'].lower().replace('*', '').strip()
        norm_source = normalize_source_for_matching(rec['Source'])
        key = f"{rec['Type']}_{norm_name}_{norm_source}_{rec['Points']}"
        en_by_normalized_key[key] = rec
    
    # 3. Conectar a BD
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 4. Para cada español, buscar equivalente en inglés
    inserted = 0
    not_found = []
    matched = 0
    
    print(f"\nProcesando {len(records_es)} registros español...")
    
    for i, rec_es in enumerate(records_es):
        # Crear clave normalizada similar
        norm_name_es = rec_es['Name'].lower().replace('*', '').strip()
        norm_source_es = normalize_source_for_matching(rec_es['Source'])
        key_es = f"{rec_es['Type']}_{norm_name_es}_{norm_source_es}_{rec_es['Points']}"
        
        # Buscar en inglés
        rec_en = en_by_normalized_key.get(key_es)
        
        if rec_en:
            matched += 1
            
            # Generar code_chest desde inglés
            code_chest = generate_code_chest_from_english(rec_en['Source'])
            
            # Buscar en BD
            cursor.execute("SELECT id_score FROM chest_score WHERE code_chest = ?", (code_chest,))
            result = cursor.fetchone()
            
            if result:
                # Insertar traducción
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO chest_def_translations 
                        (id_score, id_language, name_chest, source_chest)
                        VALUES (?, ?, ?, ?)
                    """, (result[0], ID_LANGUAGE_SPANISH, rec_es['Name'], rec_es['Source']))
                    
                    if cursor.rowcount > 0:
                        inserted += 1
                        
                except sqlite3.IntegrityError as e:
                    # Ya existe
                    pass
            else:
                not_found.append(f"No BD para: {code_chest}")
        else:
            # Intentar matching alternativo
            not_found.append(f"No match inglés para: {rec_es['Name']} ({rec_es['Points']} pts)")
        
        if (i + 1) % 50 == 0:
            print(f"  Procesados {i+1}/{len(records_es)}...")
    
    conn.commit()
    
    # 5. Resultados
    cursor.execute("SELECT COUNT(*) FROM chest_def_translations WHERE id_language = ?", 
                   (ID_LANGUAGE_SPANISH,))
    total_in_db = cursor.fetchone()[0]
    
    print(f"\n=== RESULTADOS ===")
    print(f"Registros español: {len(records_es)}")
    print(f"Matches encontrados: {matched}")
    print(f"Traducciones insertadas (nuevas): {inserted}")
    print(f"Total traducciones español en BD: {total_in_db}")
    
    # 6. Si faltan muchos, intentar método directo
    if inserted < len(records_es) * 0.5:  # Menos del 50%
        print(f"\n=== INTENTANDO MÉTODO DIRECTO ===")
        
        # Obtener todos los code_chest de la BD
        cursor.execute("SELECT code_chest, id_score FROM chest_score")
        all_codes = cursor.fetchall()
        code_to_id = {code: id_score for code, id_score in all_codes}
        
        print(f"Code chests en BD: {len(code_to_id)}")
        
        # Para cada español, generar todos los code_chest posibles
        additional_inserted = 0
        
        for rec_es in records_es:
            # Intentar generar code_chest de varias formas
            
            # 1. Desde source español directo (podría coincidir con algunos)
            source_for_code = rec_es['Source']
            
            # Convertir "nivel" a "level" para matching
            source_for_code = re.sub(r'nivel', 'level', source_for_code, flags=re.IGNORECASE)
            
            code = generate_code_chest_from_english(source_for_code)
            
            if code in code_to_id:
                # Intentar insertar
                cursor.execute("""
                    INSERT OR IGNORE INTO chest_def_translations 
                    (id_score, id_language, name_chest, source_chest)
                    VALUES (?, ?, ?, ?)
                """, (code_to_id[code], ID_LANGUAGE_SPANISH, rec_es['Name'], rec_es['Source']))
                
                if cursor.rowcount > 0:
                    additional_inserted += 1
        
        conn.commit()
        
        if additional_inserted > 0:
            print(f"Inserciones adicionales por método directo: {additional_inserted}")
            
            # Contar total final
            cursor.execute("SELECT COUNT(*) FROM chest_def_translations WHERE id_language = ?", 
                           (ID_LANGUAGE_SPANISH,))
            final_total = cursor.fetchone()[0]
            print(f"Total final en BD: {final_total}")
    
    # 7. Mostrar estadísticas
    print(f"\n=== ESTADÍSTICAS FINALES ===")
    print(f"Porcentaje insertado: {inserted/len(records_es)*100:.1f}%")
    
    # Mostrar algunos ejemplos
    cursor.execute("""
        SELECT dt.name_chest, cs.code_chest, dt.source_chest
        FROM chest_def_translations dt
        JOIN chest_score cs ON dt.id_score = cs.id_score
        WHERE dt.id_language = ?
        ORDER BY RANDOM()
        LIMIT 5
    """, (ID_LANGUAGE_SPANISH,))
    
    print("\n=== EJEMPLOS ALEATORIOS EN BD ===")
    for name, code, source in cursor.fetchall():
        print(f"• {code}")
        print(f"  Nombre: {name}")
        print(f"  Fuente: {source[:60]}..." if len(source) > 60 else f"  Fuente: {source}")
        print()
    
    if not_found:
        print(f"\n=== NO ENCONTRADOS ({len(not_found)}) ===")
        for i, nf in enumerate(not_found[:20]):
            print(f"{i+1}. {nf}")
    
    conn.close()
    print("\n✅ Proceso completado.")

if __name__ == "__main__":
    main()