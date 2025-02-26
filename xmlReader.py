import requests
import xmltodict
import pandas as pd
from datetime import datetime

def fetch_sanctions_list():
    # Mensaje de inicio
    print(" Comenzando ejecución...")

    # URL de la lista de sanciones de la OFAC
    url = "https://sanctionslistservice.ofac.treas.gov/entities?list=SDN LIST"
    print(f"Solicitando datos de: {url}")

    # Realizar la solicitud HTTP GET
    response = requests.get(url)

    # Verificar si la solicitud fue exitosa
    if response.status_code != 200:
        print("❌ Error al obtener los datos. Status code:", response.status_code)
        return

    print("✅ Datos recibidos, procesando XML...")

    # Procesar el XML recibido
    try:
        data = xmltodict.parse(response.text)
    except Exception as e:
        print(f"❌ Error al procesar el XML: {e}")
        return

    # Navegar por la estructura del diccionario XML
    sanctions_data = data.get("sanctionsData", {})
    entities_data = sanctions_data.get("entities", {})

    # Verificar si se encontraron datos de entidades
    if not entities_data:
        print("⚠ No se encontraron datos en 'entities'.")
        return

    # Obtener la lista de entidades
    entity_list = entities_data.get("entity", [])

    # Verificar si se encontraron entidades
    if not entity_list:
        print("⚠ No se encontraron entidades en 'entities'.")
        return

    # Asegurar que entity_list sea una lista
    if isinstance(entity_list, dict):
        entity_list = [entity_list]

    # Lista para almacenar los datos de cada entidad
    rows = []
    print(f" Se encontraron {len(entity_list)} entidades. Procesando...")

    # Iterar sobre cada entidad
    for i, entity in enumerate(entity_list, start=1):
        # Obtener el ID de la entidad
        entity_id = entity.get("@id", "N/A")
        # Valor predeterminado para el nombre
        name_str = "N/A"

        # Obtener los datos de los nombres
        names_data = entity.get("names", {}).get("name", [])

        # Manejar el caso donde names_data es una lista
        if isinstance(names_data, list):
            # Iterar sobre cada nombre en la lista
            for name_item in names_data:
                # Verificar si el nombre es primario
                if isinstance(name_item, dict) and name_item.get("isPrimary") == "true":
                    # Obtener las traducciones del nombre
                    translations = name_item.get("translations", {}).get("translation", [])
                    # Manejar el caso donde translations es una lista
                    if isinstance(translations, list):
                        # Iterar sobre cada traducción
                        for translation in translations:
                            # Verificar si la traducción es primaria
                            if isinstance(translation, dict) and translation.get("isPrimary") == "true":
                                # Obtener el nombre completo formateado
                                name_str = translation.get("formattedFullName", "N/A")
                                # Salir del bucle interno
                                break
                        # Salir del bucle externo si se encontró un nombre
                        if name_str != "N/A":
                            break
                    # Manejar el caso donde translations es un diccionario
                    elif isinstance(translations, dict) and translations.get("isPrimary") == "true":
                        name_str = translations.get("formattedFullName", "N/A")
                        break
        # Manejar el caso donde names_data es un diccionario
        elif isinstance(names_data, dict) and names_data.get("isPrimary") == "true":
            translations = names_data.get("translations", {}).get("translation", [])
            if isinstance(translations, list):
                for translation in translations:
                    if isinstance(translation, dict) and translation.get("isPrimary") == "true":
                        name_str = translation.get("formattedFullName", "N/A")
                        break
            elif isinstance(translations, dict) and translations.get("isPrimary") == "true":
                name_str = translations.get("formattedFullName", "N/A")

        # Agregar los datos de la entidad a la lista rows
        rows.append([entity_id, name_str])

        # Mostrar mensaje de progreso cada 10 entidades
        if i % 10 == 0:
            print(f"✅ Procesadas {i} de {len(entity_list)} entidades...")

    # Crear el DataFrame con los datos extraídos
    df = pd.DataFrame(rows, columns=["ID", "Nombres"])
    print(f"✅ Procesamiento completo. Se han procesado {len(rows)} entidades.")

    # Generar el nombre del archivo con fecha y hora
    now = datetime.now()
    file_name = f"C:\\xmlReader\\Sanctions_list_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"

    # Guardar el DataFrame en un archivo Excel
    try:
        df.to_excel(file_name, index=False)
        print(f"✅ Archivo Excel generado correctamente en: {file_name}")
    except Exception as e:
        print(f"❌ Error al guardar el archivo Excel: {e}")

    print(" Ejecución finalizada.")

# Llamar a la función principal
fetch_sanctions_list()