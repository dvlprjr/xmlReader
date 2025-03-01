#Programa que consume una API de OFAC que muestra iformacion de personas o 
# entidades y se transforma de xml a una tabla en excel y tambien subir 
# los datos a SdnList
import requests
import xmltodict
import pandas as pd
from datetime import datetime
import os

def fetch_sanctions_list():
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
        entity_id = entity.get("@id", "N/A")
        first_name = "N/A"
        last_name = "N/A"
        full_name = "N/A"
        description = "N/A"
        citizenship = "N/A"
        birthdate = "N/A"
        document_number = "N/A"

        names_data = entity.get("names", {}).get("name", [])
        if isinstance(names_data, list):
            for name_item in names_data:
                if isinstance(name_item, dict) and name_item.get("isPrimary") == "true":
                    translations = name_item.get("translations", {}).get("translation", [])
                    if isinstance(translations, list):
                        for translation in translations:
                            if isinstance(translation, dict) and translation.get("isPrimary") == "true":
                                full_name = f"{translation.get('formattedFirstName', 'N/A')} {translation.get('formattedLastName', 'N/A')}"
                                first_name = translation.get("formattedFirstName", "N/A")
                                last_name = translation.get("formattedLastName", "N/A")
                                break
                        if full_name != "N/A":
                            break
                    elif isinstance(translations, dict) and translations.get("isPrimary") == "true":
                        full_name = f"{translations.get('formattedFirstName', 'N/A')} {translations.get('formattedLastName', 'N/A')}"
                        first_name = translations.get("formattedFirstName", "N/A")
                        last_name = translations.get("formattedLastName", "N/A")
                        break
        elif isinstance(names_data, dict) and names_data.get("isPrimary") == "true":
            translations = names_data.get("translations", {}).get("translation", [])
            if isinstance(translations, list):
                for translation in translations:
                    if isinstance(translation, dict) and translation.get("isPrimary") == "true":
                        full_name = f"{translation.get('formattedFirstName', 'N/A')} {translation.get('formattedLastName', 'N/A')}"
                        first_name = translation.get("formattedFirstName", "N/A")
                        last_name = translation.get("formattedLastName", "N/A")
                        break
                    elif isinstance(translations, dict) and translations.get("isPrimary") == "true":
                        full_name = f"{translations.get('formattedFirstName', 'N/A')} {translations.get('formattedLastName', 'N/A')}"
                        first_name = translations.get("formattedFirstName", "N/A")
                        last_name = translations.get("formattedLastName", "N/A")

        general_info = entity.get("generalInfo", {})
        description = general_info.get("title", "N/A")

        features = entity.get("features", {}).get("feature", [])
        if isinstance(features, list):
            for feature in features:
                if isinstance(feature, dict) and feature.get("type", {}).get("#text") == "Birthdate":
                    birthdate = feature.get("value", "N/A")
                if isinstance(feature, dict) and feature.get("type", {}).get("#text") == "Citizenship Country":
                    citizenship = feature.get("value", "N/A")

        identity_documents = entity.get("identityDocuments", {})
        if identity_documents is not None:
            identity_document_list = identity_documents.get("identityDocument", [])
            if isinstance(identity_document_list, list):
                for doc in identity_document_list:
                    if isinstance(doc, dict) and doc.get("documentNumber"):
                        document_number = doc.get("documentNumber", "N/A")
                        break
            elif isinstance(identity_document_list, dict) and identity_document_list.get("documentNumber"):
                document_number = identity_document_list.get("documentNumber", "N/A")

        # Imprimir datos extraídos antes de agregarlos a la fila
        print(f"Entidad {i}: ID={entity_id}, FullName={full_name}, Desc={description}, DocNum={document_number}")

        rows.append([entity_id, first_name, last_name, full_name, description, citizenship, birthdate, document_number])

        if i % 10 == 0:
            print(f"Procesadas {i} de {len(entity_list)} entidades...")

    df = pd.DataFrame(rows, columns=["ID", "FirstName", "LastName", "FullName", "Description", "Citizenship", "BirthDate", "DocumentNumber"])
    print(f"Procesamiento completo. Se han procesado {len(rows)} entidades.")

    now = datetime.now()
    file_name = f"C:\\xmlReader\\xlsx\\Sanctions_list_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"

    try:
        df.to_excel(file_name, index=False)
        print(f"Archivo Excel generado correctamente en: {file_name}")
    except Exception as e:
        print(f"Error al guardar el archivo Excel: {e}")
        print(f"Directorio actual: {os.getcwd()}")
        print(f"Ruta del archivo: {file_name}")

    print("Ejecución finalizada.")

fetch_sanctions_list()