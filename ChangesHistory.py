import requests
import pyodbc
import os
from dotenv import load_dotenv
import datetime

def fetch_and_update_latest_publication_sql_server():
    """
    Programa que consume la API de OFAC y guarda la información en la tabla ChangesHistory (solo para SDN List).
    """
    current_year = datetime.datetime.now().year
    url = f"https://sanctionslistservice.ofac.treas.gov/changes/history/{current_year}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        publications = response.json()

        load_dotenv()

        server = os.getenv("SQL_SERVER")
        database = os.getenv("SQL_DATABASE")
        username = os.getenv("SQL_USERNAME")
        password = os.getenv("SQL_PASSWORD")

        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Verificar si la tabla ChangesHistory existe y crearla si no existe
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'ChangesHistory')
            BEGIN
                CREATE TABLE ChangesHistory (
                    publicationID INTEGER PRIMARY KEY,
                    datePublished TEXT,
                    typeList INT
                );
            END
        """)

        # Obtener el Id de la SDN List
        cursor.execute("SELECT Id FROM SanctionList WHERE listName = 'SDN List'")
        sdn_list_id = cursor.fetchone()[0]

        if publications:
            latest_publication = publications[-1]

            # Insertar o actualizar el registro para la SDN List
            cursor.execute("""
                IF EXISTS (SELECT 1 FROM ChangesHistory WHERE publicationID = ?)
                BEGIN
                    UPDATE ChangesHistory SET datePublished = ?, typeList = ? WHERE publicationID = ?
                END
                ELSE
                BEGIN
                    INSERT INTO ChangesHistory (publicationID, datePublished, typeList) VALUES (?, ?, ?);
                END
            """, (latest_publication["publicationID"], latest_publication["datePublished"], sdn_list_id, latest_publication["publicationID"],
                  latest_publication["publicationID"], latest_publication["datePublished"], sdn_list_id))

            conn.commit()
            conn.close()
            print("Último registro de publicación insertado/actualizado correctamente en SQL Server (SDN List).")
        else:
            print(f"No se encontraron registros de publicación para el año {current_year} en la API.")

    except requests.exceptions.HTTPError as http_err:
        print(f"Error HTTP al obtener los datos de la API: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Error de conexión al obtener los datos de la API: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Tiempo de espera agotado al obtener los datos de la API: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Error general al obtener los datos de la API: {req_err}")
    except pyodbc.Error as db_err:
        print(f"Error al interactuar con la base de datos SQL Server: {db_err}")
    except Exception as e:
        print(f"Error inesperado: {e}")

fetch_and_update_latest_publication_sql_server()