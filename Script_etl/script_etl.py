import pandas as pd
from pymongo import MongoClient
import sys

MONGO_URI = "mongodb+srv://<jhonfuentesjt_db_user>:<t0QjAgjXjceeV0l8>@cluster0.mdxlpdv.mongodb.net/"
DB_NAME = "analitica_de_precios"
COLLECTION_NAME = "products_catalogo"

# Nombre del archivo CSV que subiste
CSV_FILE_PATH = "dataset/shein-products.csv"


def extract_and_clean_data(file_path):
    """
    Función que lee el archivo CSV y limpia los datos con Pandas.
    """
    print("1. Iniciando extracción de datos desde el CSV...")
    try:
        # Leemos el CSV
        df = pd.read_csv(file_path)
        print(f"   -> Se leyeron {len(df)} registros originales.")
        
        # Seleccionamos solo las columnas relevantes para nuestro esquema analítico
        columnas_relevantes = [
            'product_id', 'product_name', 'category', 'brand', 
            'initial_price', 'final_price', 'currency', 
            'in_stock', 'reviews_count', 'rating'
        ]
        
        # Validamos que las columnas existan, si falta alguna la ignoramos para evitar errores
        columnas_existentes = [col for col in columnas_relevantes if col in df.columns]
        df = df[columnas_existentes]
        
        print("2. Iniciando proceso de limpieza (Transformación)...")
        
        # a) Eliminar filas donde el 'product_id' esté vacío
        if 'product_id' in df.columns:
            df = df.dropna(subset=['product_id'])
            # Aseguramos que el ID sea string
            df['product_id'] = df['product_id'].astype(str)
        
        # b) Limpieza de precios (convertir a Float y llenar nulos con 0.0)
        for col in ['initial_price', 'final_price']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
        # c) Limpieza de métricas numéricas (rating y reviews)
        if 'rating' in df.columns:
            df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0.0)
        if 'reviews_count' in df.columns:
            df['reviews_count'] = pd.to_numeric(df['reviews_count'], errors='coerce').fillna(0).astype(int)
            
        # d) Limpieza del estado de stock (convertir a booleano real de Python)
        if 'in_stock' in df.columns:
            # Si viene como string 'true'/'false' lo mapeamos, si ya es bool, lo dejamos
            df['in_stock'] = df['in_stock'].astype(str).str.lower().map({'true': True, '1': True, 'false': False, '0': False})
            df['in_stock'] = df['in_stock'].fillna(False) # Si hay nulos asumimos que no hay stock
            
        # e) Limpieza de textos básicos
        text_cols = ['product_name', 'category', 'brand', 'currency']
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].fillna("Unknown").astype(str)
                
        print(f"   -> Limpieza completada. Quedan {len(df)} registros listos para subir.")
        
        # Convertimos el DataFrame a una lista de diccionarios (Formato JSON/BSON para MongoDB)
        # Orient='records' crea un diccionario por cada fila
        records = df.to_dict(orient='records')
        return records

    except Exception as e:
        print(f"❌ Error durante la extracción/limpieza: {e}")
        sys.exit(1)

def load_data_to_mongodb(records):
    """
    Función que conecta a MongoDB Atlas y sube los documentos.
    """
    print("3. Conectando a MongoDB Atlas...")
    try:
        # Crear la conexión
        client = MongoClient(MONGO_URI)
        
        # Hacemos un ping para verificar que la conexión sea exitosa
        client.admin.command('ping')
        print("   -> ¡Conexión exitosa a MongoDB Atlas!")
        
        # Seleccionamos la base de datos y la colección
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Opcional: Limpiar la colección antes de subir nuevos datos (para no duplicar en pruebas)
        print("   -> Limpiando colección anterior...")
        collection.delete_many({})
        
        print(f"4. Insertando {len(records)} documentos en la colección '{COLLECTION_NAME}'...")
        # Inserción masiva (Mucho más rápido que insertar uno por uno)
        result = collection.insert_many(records)
        
        print(f"✅ Proceso ETL Finalizado con Éxito. Se insertaron {len(result.inserted_ids)} documentos.")
        
    except Exception as e:
        print(f"❌ Error al conectar o insertar en MongoDB: {e}")
    finally:
        # Siempre cerramos la conexión al terminar
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    # Ejecutamos el flujo
    cleaned_data = extract_and_clean_data(CSV_FILE_PATH)
    if cleaned_data:
        load_data_to_mongodb(cleaned_data)