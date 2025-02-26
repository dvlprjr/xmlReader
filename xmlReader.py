import requests
import xmltodict
import pandas as pd
from datetime import datetime
import os

def fetch_sanctions_list():
    print(" Comenzando ejecución...")

    url = "https://sanctionslistservice.ofac.treas.gov/entities?list=SDN LIST"
    print(f"Solicitando datos de: {url}")

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener los datos: {e}")
        return

    print("✅ Datos recibidos, procesando XML...")

    try:
        data = xmltodict.parse(response.text)
    except Exception as e:
        print(f"❌ Error al procesar el XML: {e}")
        return

    sanctions_data = data.get("sanctionsData", {})
    entities_data = sanctions_data.get("entities", {})

    if not entities_data:
        print("⚠ No se encontraron datos en 'entities'.")
        return

    entity_list = entities_data.get("entity", [])

    if not entity_list:
        print("⚠ No se encontraron entidades en 'entities'.")
        return

    if isinstance(entity_list, dict):
        entity_list = [entity_list]

    rows = []
    print(f" Se encontraron {len(entity_list)} entidades. Procesando...")

    for i, entity in enumerate(entity_list, start=1):
        entity_id = entity.get("@id", "N/A")
        first_name = "N/A"
        last_name = "N/A"
        full_name = "N/A"
        title = "N/A"
        citizenship = "N/A"
        birthdate = "N/A"
        sanctions_program = "N/A"

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
        title = general_info.get("title", "N/A")

        features = entity.get("features", {}).get("feature", [])
        if isinstance(features, list):
            for feature in features:
                if isinstance(feature, dict) and feature.get("type", {}).get("#text") == "Birthdate":
                    birthdate = feature.get("value", "N/A")
                if isinstance(feature, dict) and feature.get("type", {}).get("#text") == "Citizenship Country":
                    citizenship = feature.get("value", "N/A")

        sanctions_programs_data = entity.get("sanctionsProgram", [])
        if isinstance(sanctions_programs_data, list):
            sanctions_program = ", ".join([program.get("#text", "N/A") for program in sanctions_programs_data])
        elif isinstance(sanctions_programs_data, dict) and sanctions_programs_data.get("#text"):
            sanctions_program = sanctions_programs_data.get("#text", "N/A")

        rows.append([entity_id, first_name, last_name, full_name, title, citizenship, birthdate, sanctions_program])

        if i % 10 == 0:
            print(f"✅ Procesadas {i} de {len(entity_list)} entidades...")

    df = pd.DataFrame(rows, columns=["ID", "FirstName", "LastName", "FullName", "Title", "Citizenship", "BirthDate", "SanctionsPrograms"])
    print(f"✅ Procesamiento completo. Se han procesado {len(rows)} entidades.")

    now = datetime.now()
    file_name = f"C:\\xmlReader\\Sanctions_list_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"

    try:
        df.to_excel(file_name, index=False)
        print(f"✅ Archivo Excel generado correctamente en: {file_name}")
    except Exception as e:
        print(f"❌ Error al guardar el archivo Excel: {e}")
        print(f"Directorio actual: {os.getcwd()}")
        print(f"Ruta del archivo: {file_name}")

    print(" Ejecución finalizada.")

fetch_sanctions_list()