"""
JSON Utility Functions

This module provides functions for working with JSON data,
particularly for testing and data persistence.
"""

import os
import json
import uuid
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

# # TESTING ONLY: Directory for test JSON files
# TEST_JSON_DIR = "test-jsons"
# os.makedirs(TEST_JSON_DIR, exist_ok=True)

# # TESTING ONLY: Generate a unique session ID for this test run
# TEST_SESSION_ID = str(uuid.uuid4())
# TEST_START_TIME = datetime.now().strftime("%Y%m%d_%H%M%S")
# TEST_FILENAME = f"test_run_{TEST_START_TIME}.json"
# TEST_FILEPATH = os.path.join(TEST_JSON_DIR, TEST_FILENAME)

# # Final JSON path - now writing back to input_json.json
# FINAL_JSON_PATH = "input_json.json"

# # TESTING ONLY: Initialize test data structure with session info
# TEST_DATA = {
#     "session_id": TEST_SESSION_ID,
#     "start_time": TEST_START_TIME,
#     "form_data": {},
#     "extraction_history": []
# }

# # TESTING ONLY: Write initial test file
# with open(TEST_FILEPATH, 'w') as f:
#     json.dump(TEST_DATA, f, indent=2)


def load_input_json(filepath: str = "input_json.json") -> Dict[str, Any]:
    """
    Load data from the input JSON file.

    Args:
        filepath: Path to the input JSON file

    Returns:
        Dictionary containing the loaded data or an empty dict if file doesn't exist
    """
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def format_initial_form_data(json_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Convert the structured JSON into flat form data format used by the intake system.

    Args:
        json_data: The structured JSON data from input_json.json

    Returns:
        Dictionary with flattened form data
    """
    form_data = {}

    # Extract Main Applicant data
    if json_data.get("Main Applicant"):
        # Get first main applicant
        main_applicant = json_data["Main Applicant"][0]

        # Split full name into first/last name if present
        if main_applicant.get("Full Name"):
            name_parts = main_applicant["Full Name"].split()
            if len(name_parts) >= 2:
                form_data["applicant_first_name"] = name_parts[0]
                form_data["applicant_last_name"] = " ".join(name_parts[1:])
            else:
                form_data["applicant_first_name"] = main_applicant["Full Name"]

        # Map other main applicant fields
        if main_applicant.get("Date of Birth") is not None:
            form_data["applicant_dob"] = main_applicant["Date of Birth"]

        if main_applicant.get("First-time buyer") is not None:
            form_data["applicant_first_time_buyer"] = "yes" if main_applicant["First-time buyer"] else "no"

        if main_applicant.get("Canadian Citizen/PR") is not None:
            form_data["applicant_citizenship"] = "yes" if main_applicant["Canadian Citizen/PR"] else "no"

        if main_applicant.get("Capable of making decisions?") is not None:
            form_data["applicant_decision_making"] = "yes" if main_applicant["Capable of making decisions?"] else "no"

        if main_applicant.get("Marital Status") is not None:
            form_data["marital_status"] = main_applicant["Marital Status"]

        if main_applicant.get("Percentage of Ownership") is not None:
            form_data["primary_applicant_ownership_percentage"] = str(
                main_applicant["Percentage of Ownership"])

    # Extract Second Applicant (spouse) data
    if json_data.get("Second Applicant"):
        spouse = json_data["Second Applicant"][0]  # Get first spouse entry

        # Split full name into first/last name if present
        if spouse.get("Full Name"):
            name_parts = spouse["Full Name"].split()
            if len(name_parts) >= 2:
                form_data["spouse_first_name"] = name_parts[0]
                form_data["spouse_last_name"] = " ".join(name_parts[1:])
            else:
                form_data["spouse_first_name"] = spouse["Full Name"]

        # Map other spouse fields
        if spouse.get("Date of Birth") is not None:
            form_data["spouse_dob"] = spouse["Date of Birth"]

        if spouse.get("First-time buyer") is not None:
            form_data["spouse_first_time_buyer"] = "yes" if spouse["First-time buyer"] else "no"

        if spouse.get("Canadian Citizen/PR") is not None:
            form_data["spouse_citizenship"] = "yes" if spouse["Canadian Citizen/PR"] else "no"

    # Extract transaction details
    if json_data.get("Transaction Type") is not None:
        form_data["transaction_type"] = json_data["Transaction Type"]

    if json_data.get("Full Address") is not None:
        # Clean up the address by splitting on commas and rejoining with proper spacing
        address_parts = [part.strip()
                         for part in json_data["Full Address"].split(',')]
        address = ', '.join(address_parts)
        form_data["property_address"] = address

        # Extract postal code from address if available
        if len(address_parts) >= 3:
            last_part = address_parts[-1].strip()
            postal_code_patterns = [
                r'[A-Za-z][0-9][A-Za-z] ?[0-9][A-Za-z][0-9]',
                r'[0-9]{5}(-[0-9]{4})?'
            ]

            # Try to extract postal code from the last part
            postal_code = None
            for pattern in postal_code_patterns:
                match = re.search(pattern, last_part)
                if match:
                    postal_code = match.group(0)
                    form_data["property_postal_code"] = postal_code
                    break

            if not postal_code:
                # Check second-to-last part if the last part doesn't have a postal code
                if len(address_parts) >= 4:
                    second_last_part = address_parts[-2].strip()
                    for pattern in postal_code_patterns:
                        match = re.search(pattern, second_last_part)
                        if match:
                            postal_code = match.group(0)
                            form_data["property_postal_code"] = postal_code
                            break

    if json_data.get("Pre Con?") is not None:
        form_data["property_construction_status"] = "Pre-construction" if json_data["Pre Con?"] else "Built"

    if json_data.get("Property Type") is not None:
        form_data["property_type"] = json_data["Property Type"]

    if json_data.get("Closing Date") is not None:
        form_data["closing_date"] = json_data["Closing Date"]

    if json_data.get("Intent of Use") is not None:
        form_data["property_usage"] = json_data["Intent of Use"]

    if json_data.get("Holding Title As") is not None and json_data["Holding Title As"] != "Not Applicable":
        form_data["title_holding_question"] = json_data["Holding Title As"]

    if json_data.get("Current Address") is not None:
        form_data["client_living_address"] = json_data["Current Address"]

    # Extract professional data
    if json_data.get("Mortgage Agent"):
        mortgage_agent = json_data["Mortgage Agent"][0]
        agent_info = []

        if mortgage_agent.get("Full Name"):
            agent_info.append(mortgage_agent["Full Name"])

        if mortgage_agent.get("Mortgage Brokerage"):
            agent_info.append(mortgage_agent["Mortgage Brokerage"])

        if mortgage_agent.get("Lender"):
            agent_info.append(mortgage_agent["Lender"])

        if agent_info:
            form_data["mortgage_advisor"] = "|".join(agent_info)

    if json_data.get("Realtor"):
        realtor = json_data["Realtor"][0]
        realtor_info = []

        if realtor.get("Full Name"):
            realtor_info.append(realtor["Full Name"])

        if realtor.get("Real Estate Brokerage"):
            realtor_info.append(realtor["Real Estate Brokerage"])

        if realtor_info:
            form_data["real_estate_agent"] = "|".join(realtor_info)

    if json_data.get("Insurance Agent"):
        insurance_agent = json_data["Insurance Agent"][0]
        form_data["home_insurance"] = "yes"

        insurance_info = []
        if insurance_agent.get("Insurance Company"):
            insurance_info.append(insurance_agent["Insurance Company"])

        if insurance_agent.get("Full Name"):
            insurance_info.append(insurance_agent["Full Name"])

        if insurance_info:
            form_data["home_insurance_details"] = "|".join(insurance_info)

    return form_data


def update_test_json(form_data: Dict[str, Any], question_id: str, extracted_value: str) -> None:
    """
    TESTING ONLY: Update the test JSON file with the latest extraction.
    This maintains a single JSON file per test run, updated in real-time.

    Args:
        form_data: The current state of the form
        question_id: The ID of the question being answered
        extracted_value: The extracted value from the user's response
    """
    try:
        with open(TEST_FILEPATH, 'r') as f:
            test_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        test_data = {
            "session_id": TEST_SESSION_ID,
            "start_time": TEST_START_TIME,
            "form_data": {},
            "extraction_history": []
        }

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    extraction_entry = {
        "timestamp": timestamp,
        "question_id": question_id,
        "extracted_value": extracted_value
    }
    test_data["extraction_history"].append(extraction_entry)

    test_data["form_data"] = form_data

    with open(TEST_FILEPATH, 'w') as f:
        json.dump(test_data, f, indent=2)

    save_final_json(form_data)


def save_final_json(form_data: Dict[str, Any]) -> None:
    """
    Save the form data in the final structured format to input_json.json.

    Args:
        form_data: The current state of the form
    """
    try:
        with open(FINAL_JSON_PATH, 'r') as f:
            final_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        final_data = {
            "File Number": None,
            "Main Applicant": [{}],
            "Second Applicant": None,
            "Third Applicant": None,
            "Fourth Applicant": None,
            "Transaction Type": None,
            "Full Address": None,
            "Pre Con?": None,
            "Property Type": None,
            "Intent of Use": None,
            "Holding Title As": "Not Applicable",
            "Current Address": None,
            "Closing Date": None,
            "Mortgage Agent": None,
            "Realtor": None,
            "Insurance Agent": None
        }

    # Update main applicant data
    if "Main Applicant" not in final_data or not final_data["Main Applicant"]:
        final_data["Main Applicant"] = [{}]

    final_data["Main Applicant"][0]["Full Name"] = f"{form_data.get('applicant_first_name', '')} {form_data.get('applicant_last_name', '')}".strip(
    ) or final_data["Main Applicant"][0].get("Full Name")
    final_data["Main Applicant"][0]["Date of Birth"] = form_data.get(
        'applicant_dob') or final_data["Main Applicant"][0].get("Date of Birth")
    final_data["Main Applicant"][0]["First-time buyer"] = parse_boolean(form_data.get(
        'applicant_first_time_buyer')) if 'applicant_first_time_buyer' in form_data else final_data["Main Applicant"][0].get("First-time buyer")
    final_data["Main Applicant"][0]["Canadian Citizen/PR"] = parse_boolean(form_data.get(
        'applicant_citizenship')) if 'applicant_citizenship' in form_data else final_data["Main Applicant"][0].get("Canadian Citizen/PR")
    final_data["Main Applicant"][0]["Capable of making decisions?"] = parse_boolean(form_data.get(
        'applicant_decision_making')) if 'applicant_decision_making' in form_data else final_data["Main Applicant"][0].get("Capable of making decisions?")
    final_data["Main Applicant"][0]["Marital Status"] = form_data.get(
        'marital_status') or final_data["Main Applicant"][0].get("Marital Status", "Single")
    final_data["Main Applicant"][0]["Percentage of Ownership"] = parse_ownership(form_data.get(
        'primary_applicant_ownership_percentage')) if 'primary_applicant_ownership_percentage' in form_data else final_data["Main Applicant"][0].get("Percentage of Ownership", 1)

    # Update spouse data if applicable
    if has_spouse(form_data):
        spouse_data = get_spouse_data(form_data)
        if spouse_data:
            final_data["Second Applicant"] = spouse_data

    if 'transaction_type' in form_data:
        final_data["Transaction Type"] = get_transaction_type(
            form_data.get('transaction_type'))

    if 'property_address' in form_data or 'property_postal_code' in form_data:
        current_address = form_data.get(
            'property_address') or final_data.get("Full Address") or ""
        postal_code = form_data.get('property_postal_code')

        if postal_code:
            address_parts = [part.strip()
                             for part in current_address.split(',')]
            has_postal_in_address = False

            if len(address_parts) > 0:
                last_part = address_parts[-1].strip()
                postal_patterns = [
                    r'[A-Za-z][0-9][A-Za-z] ?[0-9][A-Za-z][0-9]',
                    r'[0-9]{5}(-[0-9]{4})?'  # US format
                ]

                if any(re.search(pattern, last_part) for pattern in postal_patterns):
                    address_parts[-1] = postal_code
                    has_postal_in_address = True
                else:
                    for pattern in postal_patterns:
                        match = re.search(pattern, last_part)
                        if match:
                            postal_code_index = match.start()
                            if postal_code_index > 0:
                                address_parts[-1] = last_part[:postal_code_index].strip() + \
                                    " " + postal_code
                            else:
                                address_parts[-1] = postal_code
                            has_postal_in_address = True
                            break

            if not has_postal_in_address:
                if current_address and not current_address.strip().endswith(','):
                    current_address = current_address.strip() + ", " + postal_code
                else:
                    current_address = current_address.strip() + " " + postal_code
            else:
                current_address = ', '.join(address_parts)
        else:
            address_parts = [part.strip()
                             for part in current_address.split(',')]
            current_address = ', '.join(address_parts)

        final_data["Full Address"] = current_address

    if 'property_construction_status' in form_data:
        final_data["Pre Con?"] = parse_boolean(
            form_data.get('property_construction_status'))
    if 'property_type' in form_data:
        final_data["Property Type"] = form_data.get('property_type')
    if 'property_usage' in form_data:
        final_data["Intent of Use"] = form_data.get('property_usage')
    if 'title_holding_question' in form_data:
        final_data["Holding Title As"] = get_title_holding(form_data)
    if 'client_living_address' in form_data:
        final_data["Current Address"] = form_data.get('client_living_address')
    if 'closing_date' in form_data:
        final_data["Closing Date"] = form_data.get('closing_date')

    if 'mortgage_advisor' in form_data and form_data['mortgage_advisor']:
        name = extract_name_from_field(form_data['mortgage_advisor'])
        company = extract_company_from_field(form_data['mortgage_advisor'])
        lender = extract_lender_from_field(form_data['mortgage_advisor'])

        if name or company or lender:
            if not final_data.get("Mortgage Agent"):
                final_data["Mortgage Agent"] = [{}]

            if name:
                final_data["Mortgage Agent"][0]["Full Name"] = name
            if company:
                final_data["Mortgage Agent"][0]["Mortgage Brokerage"] = company
            if lender:
                final_data["Mortgage Agent"][0]["Lender"] = lender
            final_data["Mortgage Agent"][0]["Email"] = final_data["Mortgage Agent"][0].get(
                "Email") if final_data.get("Mortgage Agent") else None
            final_data["Mortgage Agent"][0]["Phone"] = final_data["Mortgage Agent"][0].get(
                "Phone") if final_data.get("Mortgage Agent") else None

    if 'real_estate_agent' in form_data and form_data['real_estate_agent']:
        name = extract_name_from_field(form_data['real_estate_agent'])
        company = extract_company_from_field(form_data['real_estate_agent'])

        if name or company:
            if not final_data.get("Realtor"):
                final_data["Realtor"] = [{}]

            if name:
                final_data["Realtor"][0]["Full Name"] = name
            if company:
                final_data["Realtor"][0]["Real Estate Brokerage"] = company
            # Preserve existing fields
            final_data["Realtor"][0]["Email"] = final_data["Realtor"][0].get(
                "Email") if final_data.get("Realtor") else None
            final_data["Realtor"][0]["Phone"] = final_data["Realtor"][0].get(
                "Phone") if final_data.get("Realtor") else None

    if 'home_insurance' in form_data and form_data['home_insurance'].lower() in ['yes', 'y', 'yeah']:
        if 'home_insurance_details' in form_data and form_data['home_insurance_details']:
            company = extract_insurance_company(
                form_data['home_insurance_details'])
            agent = extract_insurance_agent(
                form_data['home_insurance_details'])

            if company or agent:
                if not final_data.get("Insurance Agent"):
                    final_data["Insurance Agent"] = [{}]

                if agent:
                    final_data["Insurance Agent"][0]["Full Name"] = agent
                if company:
                    final_data["Insurance Agent"][0]["Insurance Company"] = company
                # Preserve existing fields
                final_data["Insurance Agent"][0]["Email"] = final_data["Insurance Agent"][0].get(
                    "Email") if final_data.get("Insurance Agent") else None
                final_data["Insurance Agent"][0]["Phone"] = final_data["Insurance Agent"][0].get(
                    "Phone") if final_data.get("Insurance Agent") else None

    with open(FINAL_JSON_PATH, 'w') as f:
        json.dump(final_data, f, indent=4)


def parse_boolean(value: str) -> bool:
    """Parse string values into boolean or null"""
    if value is None or value == "[INCOMPLETE]":
        return None

    if isinstance(value, str):
        value = value.lower()
        if value in ['yes', 'y', 'true', 'citizen', 'permanent resident', 'canadian citizen']:
            return True
        elif value in ['no', 'n', 'false']:
            return False

    return None


def parse_ownership(value: str) -> float:
    """Parse ownership percentage to a number"""
    if value is None or value == "[INCOMPLETE]":
        return 1  # Default to 100% ownership

    try:
        if isinstance(value, (int, float)):
            return float(value) / 100.0 if value > 1 else float(value)

        if isinstance(value, str):
            value = value.strip('%').strip()
            return float(value) / 100.0 if float(value) > 1 else float(value)
    except (ValueError, TypeError):
        pass

    return 1


def has_spouse(form_data: Dict[str, Any]) -> bool:
    """Check if the applicant has a spouse"""
    marital_status = form_data.get('marital_status', '').lower()
    return marital_status in ['married', 'common law partner', 'common law', 'common-law']


def get_spouse_data(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a structured spouse data object if available"""
    if not has_spouse(form_data):
        return None

    spouse_name = f"{form_data.get('spouse_first_name', '')} {form_data.get('spouse_last_name', '')}".strip(
    )
    if not spouse_name:
        return None

    return [
        {
            "Full Name": spouse_name,
            "Date of Birth": form_data.get('spouse_dob', None),
            "First-time buyer": parse_boolean(form_data.get('spouse_first_time_buyer', None)),
            "Canadian Citizen/PR": parse_boolean(form_data.get('spouse_citizenship', None)),
            "Capable of making decisions?": True,
            "Marital Status": form_data.get('marital_status', "Married"),
            "Percentage of Ownership": parse_ownership(form_data.get('spouse_ownership_percentage', None))
        }
    ]


def get_transaction_type(value: str) -> str:
    """Convert transaction type to standardized format"""
    if not value:
        return "Sell"

    value = value.lower()
    if 'buy' in value:
        return "Buy"
    elif 'sell' in value:
        return "Sell"
    elif 'refinanc' in value:
        return "Refinance"
    else:
        return "Sell"


def get_title_holding(form_data: Dict[str, Any]) -> str:
    """Get the title holding information"""
    title_holding = form_data.get('title_holding_question', None)

    if not title_holding:
        return "Not Applicable"

    title_holding = title_holding.lower()
    if 'joint tenancy' in title_holding:
        return "Joint Tenancy"
    elif 'tenants in common' in title_holding:
        return "Tenants in Common"
    else:
        return "Not Applicable"


def extract_name_from_field(value: str) -> str:
    """Extract a name from a combined field"""
    if not value or value == "[INCOMPLETE]":
        return None

    # For structured pipe-separated fields (name|company|lender)
    if isinstance(value, str) and "|" in value:
        parts = value.split("|")
        if len(parts) > 0:
            return parts[0].strip()

    # For plain text values, return as is
    if isinstance(value, str):
        value = value.replace("{", "").replace("}", "").replace("\"", "")
        value = value.replace("'", "").replace("\\n", " ")

        for separator in [' for ', ' from ', ' at ', ' with ', ', ']:
            if separator in value:
                return value.split(separator)[0].strip()

        return value

    return None


def extract_company_from_field(value: str) -> str:
    """Extract a company name from a combined field"""
    if not value or value == "[INCOMPLETE]":
        return None

    if isinstance(value, str) and "|" in value:
        parts = value.split("|")
        if len(parts) > 1:
            return parts[1].strip()

    if isinstance(value, str):
        value = value.replace("{", "").replace("}", "").replace("\"", "")
        value = value.replace("'", "").replace("\\n", " ")

        for separator in [' for ', ' from ', ' at ', ' with ', ', ']:
            if separator in value:
                parts = value.split(separator)
                if len(parts) > 1:
                    return parts[1].strip()

    return None


def extract_lender_from_field(value: str) -> str:
    """Extract a lender from a mortgage advisor field"""
    if not value or value == "[INCOMPLETE]":
        return None

    if isinstance(value, str) and "|" in value:
        parts = value.split("|")
        if len(parts) > 2:
            return parts[2].strip()

    if isinstance(value, str):
        value = value.replace("{", "").replace("}", "").replace("\"", "")
        value = value.replace("'", "").replace("\\n", " ")

        parts = value.split(',')
        if len(parts) > 2:
            return parts[2].strip()

    return None


def extract_insurance_company(value: str) -> str:
    """Extract insurance company from home insurance details"""
    if not value or value == "[INCOMPLETE]":
        return None

    if isinstance(value, str) and "|" in value:
        parts = value.split("|")
        if len(parts) > 0:
            return parts[0].strip()

    if isinstance(value, str):
        value = value.replace("{", "").replace("}", "").replace("\"", "")
        value = value.replace("'", "").replace("\\n", " ")

        if 'company' in value.lower():
            parts = value.lower().split('company')
            if len(parts) > 1:
                company_part = parts[1].strip()
                if company_part.startswith('is ') or company_part.startswith(':'):
                    company_part = company_part[2:].strip()
                    for sep in [',', ';', '\n', ' and ', ' with ']:
                        if sep in company_part:
                            company_part = company_part.split(sep)[0].strip()
                return company_part.capitalize()

    return None


def extract_insurance_agent(value: str) -> str:
    """Extract insurance agent from home insurance details"""
    if not value or value == "[INCOMPLETE]":
        return None

    if isinstance(value, str) and "|" in value:
        parts = value.split("|")
        if len(parts) > 1:
            return parts[1].strip()

    if isinstance(value, str):
        value = value.replace("{", "").replace("}", "").replace("\"", "")
        value = value.replace("'", "").replace("\\n", " ")

        if 'advisor' in value.lower():
            parts = value.lower().split('advisor')
            if len(parts) > 1:
                advisor_part = parts[1].strip()
                if advisor_part.startswith('is ') or advisor_part.startswith(':'):
                    advisor_part = advisor_part[2:].strip()
                    for sep in [',', ';', '\n', ' and ', ' with ']:
                        if sep in advisor_part:
                            advisor_part = advisor_part.split(sep)[0].strip()
                return advisor_part.capitalize()

    return None