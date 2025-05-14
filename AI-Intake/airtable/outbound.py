
import requests
import json
import os
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv() 

FILE_ID = "PL0003"

AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY') 
BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
TABLE_NAME = os.environ.get('FILES_TABLE_NAME')
PERSONS_TABLE_NAME = os.environ.get('PERSONS_TABLE_NAME')
REALTORS_TABLE_NAME = os.environ.get('REALTORS_TABLE_NAME')
MORTGAGE_AGENTS_TABLE_NAME = os.environ.get('MORTGAGE_AGENTS_TABLE_NAME')
INSURANCE_AGENTS_TABLE_NAME = os.environ.get('INSURANCE_AGENTS_TABLE_NAME')


VIEW_NAME = "Intake View"
ID_FIELD_NAME = "File Number"
FIELDS = [
    "File Number",
    "Main Applicant",
    "Second Applicant",
    "Third Applicant",
    "Fourth Applicant",
    "Transaction Type",
    "Full Address",
    "Pre Con?",
    "Property Type",
    "Intent of Use",
    "Holding Title As",
    "Current Address",
    "Closing Date",
    "Mortgage Agent",
    "Realtor",
    "Insurance Agent",
    "pre-auth token"
]
PERSONS_FIELDS = [
    "Full Name",
    "Date of Birth",
    "First-time buyer",
    "Canadian Citizen/PR",
    "Capable of making decisions?",
    "Marital Status",
    "Percentage of Ownership"
]
REALTORS_FIELDS = [
    "Full Name",
    "Email",
    "Phone",
    "Real Estate Brokerage"
]
MORTGAGE_AGENTS_FIELDS = [
    "Full Name",
    "Email",
    "Phone",
    "Mortgage Brokerage",
    "Lender"
]
INSURANCE_AGENTS_FIELDS = [
    "Full Name",
    "Email",
    "Phone",
    "Insurance Company"
]


def airtable_to_json(api_key, base_id, table_name, selected_fields, identifier_field=None, identifier_value=None, resolve_lookups=True, view_name=None):
    """
    Extracts data from an Airtable table, handling field selection and lookups.

    Args:
        api_key (str): Airtable API key.
        base_id (str): Airtable base ID.
        table_name (str): Table name to extract from.
        selected_fields (list): Fields to include in JSON.
        identifier_field (str, optional): Field to identify a single record.
        identifier_value (str, optional): Value to match against identifier_field.
        resolve_lookups (bool, optional): Resolve lookup fields.
        view_name (str, optional): Airtable view name.

    Returns:
        dict: Extracted data (single record or all records), or None on error/no match.

    Raises:
        ValueError: Missing/invalid arguments.
        requests.exceptions.RequestException: HTTP request error.
        json.JSONDecodeError: Invalid JSON response.
    """
    if not api_key:
        raise ValueError("API key is required.")
    if not base_id:
        raise ValueError("Base ID is required.")
    if not table_name:
        raise ValueError("Table name is required.")
    if not selected_fields:
        raise ValueError("Selected fields list is required.")

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        if identifier_field and identifier_value:
            # Fetch a single record based on identifier field and value
            filter_by_formula = f"{{{identifier_field}}}='{identifier_value}'"
            url = f"https://api.airtable.com/v0/{base_id}/{table_name}?filterByFormula={quote(filter_by_formula)}"
            if view_name:
                url += f"&view={view_name}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            records = data.get("records", [])
            if len(records) == 1:
                record = records[0].get("fields", {})
                processed_fields = {}
                for field_name in selected_fields:
                    if field_name in record:
                        field_value = record[field_name]
                        if isinstance(field_value, list) and resolve_lookups:
                            lookup_values = []
                            for linked_record_id in field_value:
                                if field_name in ["Main Applicant", "Second Applicant", "Third Applicant", "Fourth Applicant"]:
                                    linked_fields = PERSONS_FIELDS
                                    linked_table = PERSONS_TABLE_NAME
                                elif field_name == "Realtor":
                                    linked_fields = REALTORS_FIELDS
                                    linked_table = REALTORS_TABLE_NAME
                                elif field_name == "Mortgage Agent":
                                    linked_fields = MORTGAGE_AGENTS_FIELDS
                                    linked_table = MORTGAGE_AGENTS_TABLE_NAME
                                elif field_name == "Insurance Agent":
                                    linked_fields = INSURANCE_AGENTS_FIELDS
                                    linked_table = INSURANCE_AGENTS_TABLE_NAME
                                else:
                                    linked_fields = None 
                                    linked_table = None
                                if linked_fields and linked_table:
                                    linked_record_data = get_linked_record(api_key, base_id, linked_table, linked_record_id, linked_fields)
                                    if linked_record_data:
                                        lookup_values.append(linked_record_data)
                                    else:
                                        lookup_values.append(
                                            {"id": linked_record_id, "error": "Could not retrieve linked record"})
                                else:
                                    # If no specific fields are defined, get all fields
                                    linked_record_data = get_linked_record(api_key, base_id, linked_table, linked_record_id) 
                                    if linked_record_data:
                                        lookup_values.append(linked_record_data)
                                    else:
                                        lookup_values.append({"id": linked_record_id, "error": "Could not retrieve linked record"})
                            processed_fields[field_name] = lookup_values
                        else:
                            processed_fields[field_name] = field_value
                    else:
                        processed_fields[field_name] = None
                return processed_fields  # Return the fields directly for a single record
            elif len(records) == 0:
                print(f"No record found with {identifier_field} = {identifier_value}")
                return None  # Or raise an exception if you want to enforce that a record is found
            else:
                print(f"Multiple records found with {identifier_field} = {identifier_value}.  Please use record_id.")
                return None # Or raise exception
        else:
            print("No record found.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Airtable: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from Airtable.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def get_linked_record(api_key, base_id, table_name, record_id, fields_to_include=None):
    """
    Retrieves a single record from Airtable.  Used to resolve lookup fields.

    Args:
        api_key (str): Your Airtable API key.
        base_id (str): The ID of the Airtable base.
        table_name (str): The name of the table containing the record.
        record_id (str): The ID of the record to retrieve.

    Returns:
        dict: The data for the linked record, or None on error.
    """
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}/{record_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        record_fields = data.get("fields", {})
        if fields_to_include:
            # Filter the fields to include
            filtered_fields = {field_name: record_fields.get(field_name, None) for field_name in fields_to_include}
            return filtered_fields
        else:
            # Ensure all fields are included, even if empty, and set empty fields to None
            all_fields_data = {field_name: record_fields.get(field_name, None) for field_name in record_fields}
            return all_fields_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching linked record {record_id}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON response for linked record {record_id}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while fetching linked record: {e}")
        return None


def write_json_file(data, filename="output.json"):
    """
    Writes the extracted data to a JSON file.

    Args:
        data (dict): The data to write to the JSON file.
        filename (str, optional): The name of the output file. Defaults to "output.json".
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Data successfully written to {filename}")
    except Exception as e:
        print(f"Error writing to JSON file: {e}")



if __name__ == "__main__":
    api_key = AIRTABLE_API_KEY 
    base_id = BASE_ID  
    table_name = TABLE_NAME  
    view_name = VIEW_NAME 
    selected_fields = FIELDS 
    record_id_to_fetch = None  
    identifier_field_name = ID_FIELD_NAME  #  The field to use for identification
    identifier_value_to_fetch = FILE_ID   # The value to match

    try:
        data = airtable_to_json(api_key, base_id, table_name, selected_fields, identifier_field_name, identifier_value_to_fetch, view_name=view_name)
        if data:
            write_json_file(data, f"{identifier_value_to_fetch}.json")
        else:
            print("Failed to retrieve data from Airtable.")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
