import requests
import xmltodict
import pandas as pd

def fetch_sanctions_list():
    print(" Comenzando ejecución...")

    url = "https://sanctionslistservice.ofac.treas.gov/entities?list=SDN LIST"
    print(f"Solicitando datos de: {url}")

    response = requests.get(url)
    if response.status_code != 200:
        print("❌ Error al obtener los datos. Status code:", response.status_code)
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
        name_str = "N/A"  # Valor predeterminado

        names_data = entity.get("names", {}).get("name", [])
        if isinstance(names_data, list):
            for name in names_data:
                if isinstance(name, dict) and name.get("isPrimary") == "true":
                    translation = name.get("translations", {}).get("translation", {})
                    if isinstance(translation, dict):
                        name_str = translation.get("formattedFullName", "N/A")
                        break  # Tomar el primer nombre primario
        elif isinstance(names_data, dict) and names_data.get("isPrimary") == "true":
            translation = names_data.get("translations", {}).get("translation", {})
            if isinstance(translation, dict):
                name_str = translation.get("formattedFullName", "N/A")

        rows.append([entity_id, name_str])

        if i % 10 == 0:
            print(f"✅ Procesadas {i} de {len(entity_list)} entidades...")

    df = pd.DataFrame(rows, columns=["ID", "Nombres"])
    print(f"✅ Procesamiento completo. Se han procesado {len(rows)} entidades.")

    file_name = r"C:\xmlReader\sanctions_list.xlsx"
    try:
        df.to_excel(file_name, index=False)
        print(f"✅ Archivo Excel generado correctamente en: {file_name}")
    except Exception as e:
        print(f"❌ Error al guardar el archivo Excel: {e}")

    print(" Ejecución finalizada.")

fetch_sanctions_list()