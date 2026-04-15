import logging
import math
import requests
from collections import defaultdict
from config import GRIST_SERVER, GRIST_DOC_ID, GRIST_API_KEY
from library.classes import *
from typing import List


def demand_curve(y, dc_parameter_a, dc_parameter_b):
    return min(math.exp((y - dc_parameter_a) / -dc_parameter_b), 0.95)


def fetch_grist_data(sql_query):
    """Fetches data from the Grist SQL API and returns a list of dictionaries."""
    url = f"{GRIST_SERVER}/api/docs/{GRIST_DOC_ID}/sql"
    headers = {"Authorization": f"Bearer {GRIST_API_KEY}"}
    params = {"q": sql_query}

    try:
        response = requests.get(url, headers=headers, params=params,
                                verify=True)  # `verify=False` for self-signed certs
        response.raise_for_status()
        data = response.json()

        # Extract only the 'fields' values from each record
        return [record["fields"] for record in data.get("records", [])]

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []


def get_countries():
    # Country data from ISO 3166-1
    query_name = "countries"
    sql_query = "SELECT name, iso_3 FROM countries"

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        # Reformat the data
        iso_dict = {item["name"]: item["iso_3"] for item in data}
        return iso_dict
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_languages():
    # Adding languages to the app requires both an additional column in the text table, and setting
    # the comment to active in the iso_639_3 for the cooresponding language code.
    query_name = "languages"
    sql_query = "select part1 as lang, ref_name as lang_name from iso_639_3 where comment == 'active'"

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return {item["lang"]: item["lang_name"] for item in data}
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_country_ids(iso_3):
    # Country data from ISO 3166-1
    query_name = "country_ids"
    sql_query = f"SELECT iso_3, iso_2, iso_code, name FROM countries WHERE iso_3 = '{iso_3}'"
    try:
        data = fetch_grist_data(sql_query)
        if data and isinstance(data, list):
            first_result = data[0]  # Extract first matching row
            iso_3 = first_result["iso_3"]
            iso_2 = first_result["iso_2"]
            iso_code = first_result["iso_code"]
            name = first_result["name"]
            return iso_3, iso_2, iso_code, name
        # If no result found, return None
        return None, None
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_centroid(iso_2):
    # Country centroid data pre-populated from python described
    # https://docs.google.com/document/d/1s-CT71YEr-IjxI5kVPR_17aRddWWf0M540q9fxrxK5U/edit?usp=sharing
    query_name = "centroid"
    sql_query = "SELECT latitude, longitude FROM solarstats WHERE iso_2 = '{0}'".format(iso_2)
    # Fetch Data
    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)

        # Ensure we have results
        if data and isinstance(data, list):
            first_result = data[0]  # Extract first matching row
            latitude = float(first_result["latitude"])
            longitude = float(first_result["longitude"])
            return latitude, longitude  # Return as tuple

        # If no result found, return None
        return None, None
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_frequencies():
    # Finds all frequencies in use in the manually populated technologies table
    query_name = "frequencies"
    sql_query = """
                 SELECT DISTINCT frequency, min(frequency_name) as frequency_name 
                 FROM technology 
                 WHERE frequency > 0
                 GROUP BY frequency
                 """

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_terrain():
    query_name = "terrain"
    sql_query = "SELECT name, element, value FROM terrain"

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")

def get_power():
    query_name = "power"
    sql_query = "SELECT element, description FROM power"

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")

def get_vegetation():
    query_name = "vegetation"
    sql_query = "SELECT name, element, value FROM vegetation"

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_backhaul():
    query_name = "backhaul"
    sql_query = """
    SELECT name, type, speed_mbps, power_watts, 
           capital_cost_usd, cost_base, cost_mbps, element
    FROM backhaul
    """

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_midhaul():
    query_name = "midhaul"
    sql_query = "SELECT name, speed_mbps, power_watts, capital_cost_usd, element FROM midhaul"

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_defaults():
    query_name = "defaults"
    sql_query = """SELECT variable, value, min, max, step, unit, seq, variable as element, category, alt
                 FROM defaults where category != 'na' order by seq"""

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_paf_facilities_charge():
    query_name = "paf_facilities_charge"
    sql_query = """SELECT value from defaults where variable == 'paf_facilities_charge'"""
    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        logging.info(data)
        # Extract just the value from the data structure
        if data and len(data) > 0 and "value" in data[0]:
            thevalue = float(data[0]["value"])
            logging.info(thevalue)
            return thevalue
        else:
            # Return a default value or handle the case when data is not found
            return 0  # or raise an exception if this is a critical value
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_towers():
    query_name = "towers"
    sql_query = "SELECT variable, element, value, min, max, step FROM tower"

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_tech_data():
    query_name = "tech_data"
    sql_query = "SELECT * from technology"

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_text():
    query_name = "text"
    sql_query = "SELECT element, en, es FROM text"

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_site_text_by_language(lang: str):
    """
    Return a dictionary mapping element -> text for the requested two-letter language code.
    Falls back to English ("en") if the requested language text is missing for an element.
    """
    if not isinstance(lang, str):
        raise ValueError("Language code must be a string")
    lang = lang.strip().lower()
    if len(lang) != 2 or not lang.isalpha():
        raise ValueError("Language code must be a two-letter ISO code")

    rows = get_text()  # [{"element": "banner", "en": "...", "es": "..."}, ...]
    result = {}
    for row in rows:
        element = row.get("element")
        if not element:
            continue
        value = row.get(lang)
        if value is None or value == "":
            value = row.get("en", "")
        if value is None:
            value = ""
        result[element] = value
    return result


def get_non_users(iso_3):
    # Checks population distribution data to determine the percent of the population younger than ten years
    # or older than eighty years so we can exclude them from the population of potential network users.
    query_name = "get_non_users"
    age_cats = [7, 71, 61, 65, 74, 70, 59]
    sql_query = f"""
    SELECT Location, SUM(CASE WHEN AgeId IN ({', '.join(map(str, age_cats))}) THEN Value ELSE 0 END) * 100.0 / SUM(Value) AS non_users 
    FROM unpop_2024 
    WHERE iso_3 = '{iso_3}' 
    GROUP BY Location
    """.replace("\n", " ").strip()

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        # Ensure data is not empty and extract the first non_users field
        if data and data[0].get("non_users") is not None:
            return round(data[0]["non_users"], 1), False  # Return only the non_users percentage
        else:
            data = 10
            logging.error(f"No data found for {query_name} with iso_3: {iso_3}")
            return data, True

    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_hh_size(iso_code):
    query_name = "get_hh_size"
    iso_code = int(iso_code)
    sql_query = f"""
    SELECT avg_size FROM un_hh_size WHERE iso_code = '{iso_code}' 
    AND ref_date = (SELECT MAX(ref_date) FROM un_hh_size WHERE iso_code = '{iso_code}')
    """.replace("\n", " ").strip()

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        # Ensure data is not empty and extract the first non_users field
        logging.info(data)
        if data and data[0].get("avg_size") is not None:
            return round(data[0]["avg_size"], 1), False  # Return only the avg hh size
        else:
            data = 1
            logging.error(f"No data found for {query_name} with iso code: {iso_code}")
            return data, True

    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_gdp_cap(iso_3):
    query_name = "get_gdp_cap"
    sql_query = f"""
    SELECT country, COALESCE(cy2023, cy2022, cy2021, cy2020) AS gdp_per_cap FROM wb_gdp_cap WHERE iso_3 = '{iso_3}'
    """
    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        # Ensure data is not empty and extract the first non_users field
        logging.info(data)
        if data and data[0].get("gdp_per_cap") is not None:
            theData = round(data[0]["gdp_per_cap"], 1)  # Return only the gdp per capita
            return theData, False
        else:
            data = 10000
            logging.error(f"No data found for {query_name} with iso_3: {iso_3}")
            return data, True

    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_inflation(iso_3):
    query_name = "get_inflation"
    sql_query = f"""
    SELECT country, COALESCE(cy2024, cy2023, cy2022, cy2021, cy2020, cy2019) AS inflation FROM imf_inf_2024 WHERE iso_3 = '{iso_3}'
    """
    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        # Ensure data is not empty and extract the first non_users field
        logging.info(data)
        if data and data[0].get("inflation") is not None:
            theData = round(data[0]["inflation"], 2)  # Return only the Inflation
            return theData, False
        else:
            data = 10
            logging.error(f"No data found for {query_name} with iso_3: {iso_3}")
            return data, True

    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")

def get_labour_share(iso_code):
    query_name = "get_labour_share"
    sql_query = f"""
    SELECT cy2024 as labour_share_pct from undesa_labour_share_gdp where GeoAreaCode = '{iso_code}'
    """
    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        # Ensure data is not empty and extract the first non_users field
        logging.info(data)
        if data and data[0].get("labour_share_pct") is not None:
            theData = round(data[0]["labour_share_pct"], 1)  # Return only the Labour Share
            return theData, False
        else:
            data = 50
            logging.error(f"No data found for {query_name} with iso_code: {iso_code}")
            return data, True

    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_corp_tax(iso_3):
    query_name = "get_corp_tax"
    sql_query = f"SELECT corp_tax_rate FROM damodaran_risk WHERE iso_3 = '{iso_3}'"
    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        # Ensure data is not empty and extract the corp_tax_rate field
        logging.info(data)
        if data and data[0].get("corp_tax_rate") is not None:
            theData = round(data[0]["corp_tax_rate"], 2)  # Return only the corp tax rate
            return theData, False
        else:
            data = 0
            logging.error(f"No data found for {query_name} with iso_3: {iso_3}")
            return data, True

    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")




def get_pop_growth_rate(iso_3):
    query_name = "get_pop_growth_rate"
    sql_query = f"""
    SELECT country, COALESCE(cy2023, cy2022, cy2021, cy2020) AS pop_growth_rate FROM wb_pop_growth WHERE iso_3 = '{iso_3}'
    """
    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        # Ensure data is not empty and extract the first non_users field
        logging.info(data)
        if data and data[0].get("pop_growth_rate") is not None:
            theData = round(data[0]["pop_growth_rate"], 1)  # Return only the pop growth rate
            return theData, False
        else:
            data = 0.1
            logging.error(f"No data found for {query_name} with iso_3: {iso_3}")
            return data, True

    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_power_price(iso_3):
    query_name = "get_power_price"
    sql_query = f"""
    SELECT country, COALESCE(cy2019, cy2018, cy2017, cy2016, cy2015, cy2014) AS power_price FROM wb_power_price WHERE iso_3 = '{iso_3}'
    """
    theData = 2  # Default to 2 dollars per kwh
    no_default = True
    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        # Ensure data is not empty and extract the first non_users field
        if data and data[0].get("power_price") is not None:
            theData = round((data[0]["power_price"])/100, 1)  # Return only the power price in dollars
            no_default = False
        else:
            logging.error(f"No data found for {query_name} with iso_3: {iso_3}")

    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")

    return theData, no_default


def get_power_install(iso_3):
    # Return a likely power installation cost based on WB.DB.45 and GDP per Capita
    query_name = "get_power_install"
    sql_query = f"""
    SELECT country, COALESCE(cy2019, cy2018, cy2017, cy2016, cy2015, cy2014, cy2013, cy2012, cy2011, cy2010, cy2009) AS power_install FROM wb_power_install WHERE iso_3 = '{iso_3}'
    """
    theData = 285.3  # Default value based on median of WB data available for power installation cost
    no_default = True
    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        # Ensure data is not empty and extract the first non_users field
        logging.info(data)
        if data and data[0].get("power_install") is not None:
            theData = round(data[0]["power_install"], 1)  # Return only the power install multiplier
            no_default = False
        else:
            logging.error(f"No data found for {query_name} with iso_3: {iso_3}")

    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")

    multiplier = theData/300  # Assume it's a third of the cost of a warehouse installation
    logging.info(f"multiplier is {multiplier}")
    gdp_cap, gdp_no_default = get_gdp_cap(iso_3)
    logging.info(f"gdp_cap is {gdp_cap}")
    install_cost = gdp_cap * multiplier
    logging.info(f"install_cost is {install_cost}")
    return int(install_cost), (no_default or gdp_no_default)


def get_technologies():
    query_name = "get_technology_names"
    sql_query = "SELECT distinct(technology), element as technology_name FROM technology WHERE technology != 'None'"
    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_network_types():
    query_name = "get_network_types"
    sql_query = "SELECT distinct(network_type), frequency, technology FROM technology where frequency > 0 order by network_type"
    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_networks():
    query_name = "networks"
    sql_query = "SELECT DISTINCT(network_type) from technology where frequency > 0 order by network_type"
    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        # Extract just the network_type values from the response
        return [record["network_type"] for record in data if "network_type" in record]
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def filter_technologies(data: FrequencyData) -> List[FrequencyResponse]:
    query_name = "filter_technologies"
    sql_query = """
        select frequency, network_type from technology where frequency in ({}) and technology in ({})
    """.format(
        ", ".join(map(str, data.frequencies)),  # Convert frequencies to a comma-separated string
        ", ".join(f"'{t}'" for t in data.technologies)  # Wrap strings in single quotes
    )
    try:
        grouped_data = defaultdict(list)
        records = fetch_grist_data(sql_query)
        for record in records:
            grouped_data[record["frequency"]].append(record["network_type"])
        return [FrequencyResponse(frequency=freq, network_types=types) for freq, types in grouped_data.items()]
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def get_solarstats():
    query_name = "solarstats"
    sql_query = """
    SELECT
    location, iso_2, latitude, longitude, min_sun, max_no_sun_days, annual_no_sun_days, avg_temp, min_temp, max_temp
    FROM solarstats
    """

    # Fetch Data
    try:
        data = fetch_grist_data(sql_query)
        return data
    except Exception as e:
        raise Exception(f"Failed to load {query_name} data: {str(e)}")


def safe_value(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return 0.0
    return float(val)


def build_keyed_row(label: str, base_key: str, data_dict: dict) -> dict:
    return {
        "label": label,
        **{
            f"y{year}": safe_value(data_dict.get(f"{base_key}_y{year}"))
            for year in range(1, 11)
        }
    }


def calculate_characteristics(iso_3: str):
    """
    Calculates and returns country-specific characteristics.
    """
    iso_3 = iso_3.upper()
    country_ids = get_country_ids(iso_3)
    if not country_ids or country_ids[0] is None:
        return None

    iso_3, iso_2, iso_code, country_name = country_ids

    # Fetch the defaults data
    defaults_data = get_defaults()

    # Calculate the new updated values with country specific data
    hh_size, hh_size_no_default = get_hh_size(iso_code)
    non_users_pct, non_users_pct_no_default = get_non_users(iso_3)
    non_users_pct = round(non_users_pct, 2)
    non_users = round((non_users_pct / 100 * hh_size), 1)
    non_users_no_default = hh_size_no_default or non_users_pct_no_default
    users_per_household = round(hh_size - non_users, 1)
    users_per_household_no_default = hh_size_no_default or non_users_no_default
    gdp_cap, gdp_cap_no_default = get_gdp_cap(iso_3)
    pop_growth_rate, pop_growth_rate_no_default = get_pop_growth_rate(iso_3)
    power_price, power_price_no_default = get_power_price(iso_3)
    power_install, power_install_no_default = get_power_install(iso_3)
    labour_share, labour_share_no_default = get_labour_share(iso_code)
    labour_share_pct = labour_share/100
    hh_income_week = round((gdp_cap * labour_share_pct * hh_size) / 52, 1)
    hh_income_week_no_default = (
            gdp_cap_no_default
            and hh_size_no_default
            and labour_share_no_default
    )
    paf_facilities_charge = get_paf_facilities_charge()
    labour_cost = round(((hh_income_week / 80) * 1.5), 1)
    labour_cost_no_default = hh_income_week_no_default
    paf_usd_hour = round(hh_income_week * (paf_facilities_charge / 100), 1)
    paf_usd_hour_no_default = hh_income_week_no_default
    inflation, inflation_no_default = get_inflation(iso_3)
    corp_tax_raw, corp_tax_no_default = get_corp_tax(iso_3)
    corp_tax = corp_tax_raw * 100
    logging.info("Default characteristics calculations complete")

    # Map of variables to their new values and noDefault status
    updates = {
        "hh_size": (hh_size, hh_size_no_default),
        "non_users_pct": (non_users_pct, non_users_pct_no_default),
        "non_users": (non_users, non_users_no_default),
        "users_per_household": (users_per_household, users_per_household_no_default),
        "gdp_cap": (gdp_cap, gdp_cap_no_default),
        "pop_growth_rate": (pop_growth_rate, pop_growth_rate_no_default),
        "power_price": (power_price, power_price_no_default),
        "power_install": (power_install, power_install_no_default),
        "hh_income_week": (hh_income_week, hh_income_week_no_default),
        "labour_cost": (labour_cost, labour_cost_no_default),
        "paf_usd_hour": (paf_usd_hour, paf_usd_hour_no_default),
        "inflation": (inflation, inflation_no_default)
    }
    logging.info(f"{updates}")

    # Update the values in defaults_data
    for item in defaults_data:
        variable = item.get("variable")
        if variable in updates:
            value, no_default = updates[variable]
            item["value"] = value
            if no_default:
                item["noDefault"] = True
        # Special handling for corp_tax: update "alt" instead of "value"
        elif variable == "corp_tax":
            item["alt"] = corp_tax
            if corp_tax_no_default:
                item["noDefault"] = True

    return defaults_data
