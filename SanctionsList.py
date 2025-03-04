# Programa que consume una API de OFAC y este guarda la informacion a una tabla (SanctionList) en la Bd OFAC

import requests
import pyodbc
import os
#from dotenv import load_dotenv

def fetch_and_store_sanctions_lists():
    url = "https://sanctionslistservice.ofac.treas.gov/sanctions-lists"

    try:
        response = requests.get(url)
        response.raise_for_status()
        sanctions_lists = response.json()

#      load_dotenv()

        # Conexión a la base de datos
        server = os.getenv("SQL_SERVER_OFACPY")
        database = os.getenv("SQL_DATABASE_OFACPY")
        username = os.getenv("SQL_USERNAME_OFACPY")
        password = os.getenv("SQL_PASSWORD_OFACPY")

        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Verificar si la tabla existe
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'SanctionList')
            BEGIN
                CREATE TABLE SanctionList (
                    Id INT IDENTITY(1,1) PRIMARY KEY,
                    listName VARCHAR(255) UNIQUE
                );
            END
        """)

        for list_name in sanctions_lists:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM SanctionList WHERE listName = ?)
                BEGIN
                    INSERT INTO SanctionList (listName) VALUES (?);
                END
            """, (list_name, list_name))

        conn.commit()
        conn.close()
        print("Datos de listas de sanciones insertados/actualizados correctamente en SQL Server.")

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener los datos de la API: {e}")
    except pyodbc.Error as e:
        print(f"Error al interactuar con la base de datos SQL Server: {e}")

fetch_and_store_sanctions_lists()