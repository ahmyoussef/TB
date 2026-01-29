"""
Script de Diagnóstico - Foreign Key Constraint Failed
Ejecuta este script para identificar qué foreign key está causando el problema
"""

import sqlite3
import sys

print("="*70)
print("DIAGNÓSTICO DE FOREIGN KEY - TB CHEST TRACKER")
print("="*70)

# Conectar a la base de datos
db_path = r'..\data\databases\TB_chests_clans.db'
print(f"\nConectando a: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    print("✅ Conexión exitosa\n")
except Exception as e:
    print(f"❌ Error al conectar: {e}")
    sys.exit(1)

# Obtener IDs del último intento fallido
# Basándonos en el log: Cofre bárbaro, Aulanim, Cripta de nivel 5

print("="*70)
print("VERIFICANDO DATOS DEL COFRE QUE FALLÓ")
print("="*70)
print("Cofre: 'Cofre bárbaro'")
print("Player: 'Aulanim'")
print("Source: 'Cripta de nivel 5'")
print("Clan ID: 1")
print("Session ID: 118")
print()

# 1. Verificar clan
print("1. VERIFICANDO CLAN (id_clan = 1)...")
cursor.execute("SELECT * FROM clans WHERE id_clan = 1")
clan = cursor.fetchone()
if clan:
    print(f"   ✅ Clan encontrado: {dict(clan)}")
else:
    print(f"   ❌ ERROR: Clan ID 1 NO existe")

# 2. Verificar jugador
print("\n2. VERIFICANDO JUGADOR (name = 'Aulanim')...")
cursor.execute("SELECT * FROM players WHERE name_player = 'Aulanim' AND id_clan = 1")
player = cursor.fetchone()
if player:
    print(f"   ✅ Jugador encontrado: ID {player['id_player']}, Name: {player['name_player']}")
    player_id = player['id_player']
else:
    print(f"   ❌ ERROR: Jugador 'Aulanim' NO existe en clan 1")
    player_id = None

# 3. Verificar chest definition (ID 21 del log)
print("\n3. VERIFICANDO CHEST DEFINITION (id_score = 21)...")
cursor.execute("SELECT * FROM chest_score WHERE id_score = 21")
chest_def = cursor.fetchone()
if chest_def:
    print(f"   ✅ Chest definition encontrado:")
    print(f"      ID: {chest_def['id_score']}")
    print(f"      Code: {chest_def['code_chest']}")
    print(f"      Points: {chest_def['base_point_value']}")
else:
    print(f"   ❌ ERROR: Chest definition ID 21 NO existe")

# 4. Verificar sesión
print("\n4. VERIFICANDO SESIÓN (id_session = 118)...")
cursor.execute("SELECT * FROM capture_sessions WHERE id_session = 118")
session = cursor.fetchone()
if session:
    print(f"   ✅ Sesión encontrada:")
    print(f"      ID: {session['id_session']}")
    print(f"      Clan: {session['id_clan']}")
    print(f"      Status: {session['status']}")
else:
    print(f"   ❌ ERROR: Sesión ID 118 NO existe")

# 5. Intentar hacer el INSERT manualmente
print("\n" + "="*70)
print("INTENTANDO INSERT MANUAL")
print("="*70)

if player:
    try:
        print("\nEjecutando INSERT con estos valores:")
        print(f"   id_clan: 1")
        print(f"   id_player: {player_id}")
        print(f"   id_chest_def: 21")
        print(f"   time_left: '0 h : 15 m'")
        print(f"   obtained_at: '2026-01-29 01:13:16'")
        print(f"   ocr_language_used: 'es'")
        print(f"   points_awarded: 1")
        print(f"   id_session: 118")
        
        cursor.execute("""
            INSERT INTO chest_registers 
            (id_clan, id_player, id_chest_def, time_left, obtained_at, 
             ocr_language_used, points_awarded, id_session) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (1, player_id, 21, '0 h : 15 m', '2026-01-29 01:13:16', 'es', 1, 118))
        
        print("\n   ✅ INSERT exitoso!")
        conn.rollback()  # No guardar, solo probar
        
    except sqlite3.IntegrityError as e:
        print(f"\n   ❌ INSERT falló con IntegrityError: {e}")
        print("\n   Diagnosticando cuál FK falló...")
        
        # Probar sin id_session
        try:
            cursor.execute("""
                INSERT INTO chest_registers 
                (id_clan, id_player, id_chest_def, time_left, obtained_at, 
                 ocr_language_used, points_awarded, id_session) 
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
            """, (1, player_id, 21, '0 h : 15 m', '2026-01-29 01:13:16', 'es', 1))
            print("      ✅ Sin id_session funciona → El problema es FK id_session")
            conn.rollback()
        except:
            print("      ❌ Sin id_session también falla")
            
            # Probar sin id_chest_def
            try:
                cursor.execute("""
                    INSERT INTO chest_registers 
                    (id_clan, id_player, id_chest_def, time_left, obtained_at, 
                     ocr_language_used, points_awarded, id_session) 
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?)
                """, (1, player_id, '0 h : 15 m', '2026-01-29 01:13:16', 'es', 1, 118))
                print("      ✅ Con id_chest_def=1 funciona → El problema es FK id_chest_def")
                conn.rollback()
            except:
                print("      ❌ El problema es otro FK")
                
    except Exception as e:
        print(f"\n   ❌ INSERT falló con otro error: {e}")

# 6. Verificar estructura de chest_registers
print("\n" + "="*70)
print("VERIFICANDO FOREIGN KEYS DE chest_registers")
print("="*70)

cursor.execute("PRAGMA foreign_key_list(chest_registers)")
fks = cursor.fetchall()

print(f"\nForeign Keys definidas: {len(fks)}")
for fk in fks:
    print(f"   - Column: {fk[3]:20} → Table: {fk[2]:20} (Column: {fk[4]})")

# 7. Verificar si hay chest_score con id_score = 21
print("\n" + "="*70)
print("VERIFICANDO CHEST_SCORE DETALLADAMENTE")
print("="*70)

cursor.execute("SELECT COUNT(*) as total FROM chest_score")
total = cursor.fetchone()['total']
print(f"\nTotal chest_score records: {total}")

cursor.execute("SELECT id_score FROM chest_score ORDER BY id_score")
all_ids = [row['id_score'] for row in cursor.fetchall()]
print(f"IDs disponibles: {all_ids[:20]}...")  # Primeros 20

if 21 in all_ids:
    print(f"\n✅ ID 21 existe en chest_score")
else:
    print(f"\n❌ ID 21 NO existe en chest_score")
    print(f"   IDs cercanos: {[x for x in all_ids if 15 <= x <= 30]}")

# 8. Resumen
print("\n" + "="*70)
print("RESUMEN")
print("="*70)

print("\nESTADO DE LAS FOREIGN KEYS:")
print(f"   id_clan (1): {'✅ OK' if clan else '❌ FALTA'}")
print(f"   id_player ({player_id if player else 'N/A'}): {'✅ OK' if player else '❌ FALTA'}")
print(f"   id_chest_def (21): {'✅ OK' if chest_def else '❌ FALTA'}")
print(f"   id_session (118): {'✅ OK' if session else '❌ FALTA'}")

conn.close()
print("\n" + "="*70)
