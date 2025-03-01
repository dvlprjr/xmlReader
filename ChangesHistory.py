import requests
import pyodbc
import os
from dotenv import load_dotenv
import datetime
import xml.etree.ElementTree as ET
import uuid

def process_entity_update(list_name, sanction_id, cursor):
    """
    Procesa el endpoint de entidades y registra la actualización en ChangesHistory.
    """
    entity_url = f"https://sanctionslistservice.ofac.treas.gov/entities?list={{{list_name}}}"
    entity_response = requests.get(entity_url)
    entity_response.raise_for_status()

    root = ET.fromstring(entity_response.content)
    data_as_of = root.find(".//{https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ENHANCED_XML}dataAsOf").text

    try:
        publication_id = uuid.uuid4().int & (1<<31)-1
    except Exception as e:
        print(f"Error generating publication ID: {e}")
        return

    cursor.execute("""
        IF EXISTS (SELECT 1 FROM ChangesHistory WHERE typeList = ? AND datePublished = ?)
        BEGIN
            UPDATE ChangesHistory SET publicationID = ?, datePublished = ? WHERE typeList = ?
        END
        ELSE
        BEGIN
            INSERT INTO ChangesHistory (publicationID, datePublished, typeList) VALUES (?, ?, ?);
        END
    """, (sanction_id, data_as_of, publication_id, data_as_of, sanction_id, publication_id, data_as_of, sanction_id))

def fetch_and_update_latest_publication_sql_server():
    """
    Programa que consume la API de OFAC y guarda la información en la tabla ChangesHistory.
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
                    datePublished NVARCHAR(255), -- Cambio a NVARCHAR(255)
                    typeList INT
                );
            END
        """)

        if publications:  # Verificar si la lista no está vacía
            latest_publication = publications[-1]  # Obtener el último elemento de la lista

            # Obtener el Id y listName de la tabla SanctionList
            cursor.execute("SELECT Id, listName FROM SanctionList")
            sanction_lists = cursor.fetchall()

            for sanction_id, list_type in sanction_lists:
                cursor.execute("""
                    IF EXISTS (SELECT 1 FROM ChangesHistory WHERE publicationID = ?)
                    BEGIN
                        UPDATE ChangesHistory SET datePublished = ?, typeList = ? WHERE publicationID = ?
                    END
                    ELSE
                    BEGIN
                        INSERT INTO ChangesHistory (publicationID, datePublished, typeList) VALUES (?, ?, ?);
                    END
                """, (latest_publication["publicationID"], latest_publication["datePublished"], sanction_id, latest_publication["publicationID"],
                      latest_publication["publicationID"], latest_publication["datePublished"], sanction_id))

                # Procesar el endpoint de entidades
                process_entity_update(list_type, sanction_id, cursor)

            conn.commit()
            conn.close()
            print("Último registro de publicación insertado/actualizado correctamente en SQL Server.")
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