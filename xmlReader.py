import requests
import xmltodict
import pyodbc
import os
from dotenv import load_dotenv

def fetch_sanctions_list():
    """
    Obtiene entidades de la lista SDN de la API de OFAC y las almacena en la tabla SDN_LIST de SQL Server.
    """
    print("Comenzando ejecución...")

    url = "https://sanctionslistservice.ofac.treas.gov/entities?list=SDN LIST"
    print(f"Solicitando datos de: {url}")

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener los datos: {e}")
        return

    print("Datos recibidos, procesando XML...")

    try:
        data = xmltodict.parse(response.text)
    except Exception as e:
        print(f"Error al procesar el XML: {e}")
        return

    sanctions_data = data.get("sanctionsData", {})
    entities_data = sanctions_data.get("entities", {})

    if not entities_data:
        print("No se encontraron datos en 'entities'.")
        return

    entity_list = entities_data.get("entity", [])

    if not entity_list:
        print("No se encontraron entidades en 'entities'.")
        return

    if isinstance(entity_list, dict):
        entity_list = [entity_list]

    rows = []
    print(f"Se encontraron {len(entity_list)} entidades. Procesando...")

    for i, entity in enumerate(entity_list, start=1):
        entity_id = entity.get("@id", None)
        first_name = None
        last_name = None
        full_name = None
        description = None
        birthdate = None
        id_type = None
        id_number = None
        id_country = None

        names_data = entity.get("names", {}).get("name", [])
        if isinstance(names_data, list):
            for name_item in names_data:
                if isinstance(name_item, dict) and name_item.get("isPrimary") == "true":
                    translations = name_item.get("translations", {}).get("translation", [])
                    if isinstance(translations, list):
                        for translation in translations:
                            if isinstance(translation, dict) and translation.get("isPrimary") == "true":
                                full_name = f"{translation.get('formattedFirstName', '')} {translation.get('formattedLastName', '')}"
                                first_name = translation.get("formattedFirstName", None)
                                last_name = translation.get("formattedLastName", None)
                                break
                    elif isinstance(translations, dict) and translations.get("isPrimary") == "true":
                        full_name = f"{translations.get('formattedFirstName', '')} {translations.get('formattedLastName', '')}"
                        first_name = translations.get("formattedFirstName", None)
                        last_name = translations.get("formattedLastName", None)
        elif isinstance(names_data, dict) and names_data.get("isPrimary") == "true":
            translations = names_data.get("translations", {}).get("translation", [])
            if isinstance(translations, list):
                for translation in translations:
                    if isinstance(translation, dict) and translation.get("isPrimary") == "true":
                        full_name = f"{translation.get('formattedFirstName', '')} {translation.get('formattedLastName', '')}"
                        first_name = translation.get("formattedFirstName", None)
                        last_name = translation.get("formattedLastName", None)
                        break
            elif isinstance(translations, dict) and translations.get("isPrimary") == "true":
                full_name = f"{translations.get('formattedFirstName', '')} {translations.get('formattedLastName', '')}"
                first_name = translations.get("formattedFirstName", None)
                last_name = translations.get("formattedLastName", None)

        general_info = entity.get("generalInfo", {})
        description = general_info.get("title", None)

        features = entity.get("features", {}).get("feature", [])
        if isinstance(features, list):
            for feature in features:
                if isinstance(feature, dict) and feature.get("type", {}).get("#text") == "Birthdate":
                    birthdate = feature.get("value", None)
                if isinstance(feature, dict) and feature.get("type", {}).get("#text") == "Place of Birth":
                    id_country = feature.get("value", None)

        identity_documents = entity.get("identityDocuments", {})
        if identity_documents is not None:
            identity_document_list = identity_documents.get("identityDocument", [])
            if isinstance(identity_document_list, list):
                for doc in identity_document_list:
                    if isinstance(doc, dict) and doc.get("documentNumber"):
                        id_number = doc.get("documentNumber", None)
                        id_type = doc.get("type", None)
                        if id_type:
                            id_type = id_type.get("#text", None)
                        break
            elif isinstance(identity_document_list, dict) and identity_document_list.get("documentNumber"):
                id_number = identity_document_list.get("documentNumber", None)
                id_type = identity_document_list.get("type", None)
                if id_type:
                    id_type = id_type.get("#text", None)

        # Imprimir datos extraídos antes de agregarlos a la fila
        print(f"Entidad {i}: ID={entity_id}, FullName={full_name}, Desc={description}, DocNum={id_number}, IdType={id_type}, IdCountry={id_country}")

        rows.append([entity_id, first_name, last_name, full_name, description, birthdate, id_type, id_number, id_country])

        if i % 10 == 0:
            print(f"Procesadas {i} de {len(entity_list)} entidades...")

    # Conexión a la base de datos
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

    # Crear la tabla SDN_LIST si no existe
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'SDN_LIST')
        BEGIN
            CREATE TABLE SDN_LIST (
                Id NVARCHAR(255) PRIMARY KEY,
                FirstName NVARCHAR(255),
                LastName NVARCHAR(255),
                FullName NVARCHAR(255),
                Description TEXT,
                Birthdate NVARCHAR(255),
                IdType NVARCHAR(255),
                IdNumber NVARCHAR(255),
                IdCountry NVARCHAR(255)
            );
        END
    """)

    # Insertar o actualizar los datos en la tabla SDN_LIST
    for row in rows:
        try:
            # Verificar si el registro ya existe
            cursor.execute("SELECT 1 FROM SDN_LIST WHERE Id = ?", (row[0],))
            if cursor.fetchone():
                # Actualizar el registro existente
                cursor.execute("""
                    UPDATE SDN_LIST
                    SET FirstName = ?, LastName = ?, FullName = ?, Description = ?, Birthdate = ?, IdType = ?, IdNumber = ?, IdCountry = ?
                    WHERE Id = ?
                """, (row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[0]))
            else:
                # Insertar un nuevo registro
                cursor.execute("""
                    INSERT INTO SDN_LIST (Id, FirstName, LastName, FullName, Description, Birthdate, IdType, IdNumber, IdCountry)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row)
        except pyodbc.Error as e:
            print(f"Error inserting/updating data: {e}")

    conn.commit()
    conn.close()
    print(f"Procesamiento completo. Se han procesado {len(rows)} entidades.")
    print("Ejecución finalizada.")

fetch_sanctions_list()