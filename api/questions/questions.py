"""
Contains the structured questions for the form intake process.
Questions are organized in a way that makes it easy to navigate
based on conditional logic and previous answers.
"""

QUESTIONS = [
    {
        "id": "welcome",
        "text": "Hi there! I'm your virtual assistant. I'm here to guide you through the intake process for your real estate closing. I'll be asking you a few questions — this should take about 5 minutes. Before we begin, please make sure you're in a quiet place and make sure to speak slowly and clearly. Don't worry if you are not able to answer some questions. We will send you a summary of the information you provide to us to your email and you will be able to adjust anything using the philer platform. Ready to get started? Say Start.",
        "required": True,
        "next": "applicant_first_name"
    },
    {
        "id": "transition_start",
        "text": "Great! Let's start!",
        "required": False,
        "next": "applicant_first_name"
    },
    {
        "id": "applicant_first_name",
        "text": "Please tell me your first name. Feel free to spell it if you prefer.",
        "required": True,
        "next": "applicant_last_name"
    },
    {
        "id": "applicant_last_name",
        "text": "Now your last name.",
        "required": True,
        "next": "applicant_dob"
    },
    {
        "id": "applicant_dob",
        "text": "What is your date of birth?",
        "required": True,
        "next": "applicant_first_time_buyer"
    },
    {
        "id": "applicant_first_time_buyer",
        "text": "Are you a first-time homebuyer? This means you have never purchased any property anywhere in the world.",
        "required": True,
        "next": "applicant_citizenship"
    },
    {
        "id": "applicant_citizenship",
        "text": "Are you a Canadian Citizen or Permanent Resident? Please specify.",
        "required": True,
        "next": "applicant_decision_making"
    },
    {
        "id": "applicant_decision_making",
        "text": "Do you acknowledge that you are fully able to understand and make decisions on your own?",
        "required": True,
        "next": "transaction_type"
    },
    {
        "id": "transaction_type",
        "text": "Are you Purchasing, Selling or Refinancing your property?",
        "required": True,
        "next": lambda state: "property_construction_status" if state.get("transaction_type", "").lower() == "purchasing" else "property_type"
    },
    {
        "id": "property_construction_status",
        "text": "Is the property already built or it is a pre-construction purchase?",
        "required": False,
        "condition": lambda state: state.get("transaction_type", "").lower() == "purchasing",
        "next": "property_type"
    },
    {
        "id": "property_type",
        "text": "What is the type of the property you're closing on? Condo Apartment, Detached House, Semi-detached House, Freehold Townhouse, Condo Townhouse, Multiplex or other?",
        "required": True,
        "next": "closing_date"
    },
    {
        "id": "closing_date",
        "text": "What is your Closing Date?",
        "required": True,
        "next": "property_postal_code"
    },
    {
        "id": "property_postal_code",
        "text": "Do you know the property postal code? No problem if you don't have this information now.",
        "required": True,
        "next": "property_address"
    },
    {
        "id": "property_address",
        "text": "Ok! Please tell me the property address, including the city.",
        "required": True,
        "next": "living_at_property"
    },
    {
        "id": "living_at_property",
        "text": "Is this the address where you will be living after closing?",
        "required": False,
        "condition": lambda state: state.get("transaction_type", "").lower() == "purchasing",
        "next": lambda state: "alternative_address" if state.get("living_at_property", "").lower() in ["no", "n", "nope"] else "property_usage"
    },
    {
        "id": "alternative_address",
        "text": "So, what is the address of the place you live or will be living after closing?",
        "required": False,
        "condition": lambda state: state.get("living_at_property", "").lower() in ["no", "n", "nope"],
        "next": "alternative_postal_code"
    },
    {
        "id": "alternative_postal_code",
        "text": "And what is the postal code?",
        "required": False,
        "condition": lambda state: state.get("living_at_property", "").lower() in ["no", "n", "nope"],
        "next": "property_usage"
    },
    {
        "id": "property_usage",
        "text": "How do you intend to use the property you are acquiring? Primary Residence, Secondary Residence, Investment Property, Fix and Flip, Family Use or Other uses?",
        "required": False,
        "condition": lambda state: state.get("transaction_type", "").lower() == "purchasing",
        "next": lambda state: "marital_status" if (state.get("property_usage", "").lower() == "primary residence" or 
                                                 state.get("living_at_property", "").lower() in ["yes", "y", "yeah", "yep"] or
                                                 state.get("alternative_address") is not None) else "client_living_address"
    },
    {
        "id": "client_living_address",
        "text": "What is your current address where you are living?",
        "required": False,
        "condition": lambda state: (state.get("transaction_type", "").lower() == "purchasing" and 
                                  state.get("property_usage", "").lower() != "primary residence" and
                                  state.get("living_at_property", "").lower() not in ["yes", "y", "yeah", "yep"] and
                                  state.get("alternative_address") is None),
        "next": "client_living_postal_code"
    },
    {
        "id": "client_living_postal_code",
        "text": "And what is the postal code of your living address?",
        "required": False,
        "condition": lambda state: (state.get("transaction_type", "").lower() == "purchasing" and 
                                  state.get("property_usage", "").lower() != "primary residence"),
        "next": "marital_status"
    },
    {
        "id": "marital_status",
        "text": "What is your marital status? Married, Common Law Partner, Single, Divorced or Separed?",
        "required": True,
        "next": lambda state: "spouse_first_name" if state.get("marital_status", "").lower() in ["married", "common law partner", "common law", "common-law"] else "single_additional_applicants_question"
    },
    {
        "id": "spouse_first_name",
        "text": "Please tell me your spouse's first name. Feel free to spell it if you prefer.",
        "required": False,
        "condition": lambda state: state.get("marital_status", "").lower() in ["married", "common law partner", "common law", "common-law"],
        "next": "spouse_last_name"
    },
    {
        "id": "spouse_last_name",
        "text": "Now your spouse's last name.",
        "required": False,
        "condition": lambda state: state.get("marital_status", "").lower() in ["married", "common law partner", "common law", "common-law"],
        "next": "spouse_dob"
    },
    {
        "id": "spouse_dob",
        "text": "What is your spouse's date of birth?",
        "required": False,
        "condition": lambda state: state.get("marital_status", "").lower() in ["married", "common law partner", "common law", "common-law"],
        "next": "spouse_first_time_buyer"
    },
    {
        "id": "spouse_first_time_buyer",
        "text": "Is your spouse a first-time homebuyer? This means your spouse has never purchased any property anywhere in the world.",
        "required": False,
        "condition": lambda state: state.get("marital_status", "").lower() in ["married", "common law partner", "common law", "common-law"],
        "next": "spouse_citizenship"
    },
    {
        "id": "spouse_citizenship",
        "text": "Is your spouse a Canadian Citizen or Permanent Resident? Please specify.",
        "required": False,
        "condition": lambda state: state.get("marital_status", "").lower() in ["married", "common law partner", "common law", "common-law"],
        "next": "additional_applicants_question"
    },
    {
        "id": "additional_applicants_question",
        "text": "Thank you for providing your spouse details! Are there any additional Applicants besides you and your spouse? Answer clearly with 'yes' or 'no'.",
        "required": False,
        "condition": lambda state: state.get("marital_status", "").lower() in ["married", "common law partner", "common law", "common-law"],
        "next": lambda state: "multiple_owners_question" if state.get("additional_applicants_question", "").lower() in ["no", "n", "nope"] else "additional_applicant_transition"
    },
    {
        "id": "single_additional_applicants_question",
        "text": "Will anyone else be on the application besides you? Please answer 'No' if you are the only applicant, or 'Yes' if there are additional people.",
        "required": False,
        "condition": lambda state: state.get("marital_status", "").lower() not in ["married", "common law partner", "common law", "common-law"],
        "next": lambda state: "farewell" if state.get("single_additional_applicants_question", "").lower() in ["no", "n", "nope"] else "additional_applicant_transition"
    },
    {
        "id": "additional_applicant_transition",
        "text": "Ok! Please tell me the additional applicant's details",
        "required": False,
        "condition": lambda state: (state.get("additional_applicants_question", "").lower() not in ["no", "n", "nope"] or 
                                   state.get("single_additional_applicants_question", "").lower() not in ["no", "n", "nope"]),
        "next": "additional_applicant_first_name"
    },
    {
        "id": "additional_applicant_first_name",
        "text": "Please tell me the applicant first name. Feel free to spell it if you prefer.",
        "required": False,
        "condition": lambda state: (state.get("additional_applicants_question", "").lower() not in ["no", "n", "nope"] or 
                                   state.get("single_additional_applicants_question", "").lower() not in ["no", "n", "nope"]),
        "next": "additional_applicant_last_name"
    },
    {
        "id": "additional_applicant_last_name",
        "text": "Now the applicant's last name.",
        "required": False,
        "condition": lambda state: (state.get("additional_applicants_question", "").lower() not in ["no", "n", "nope"] or 
                                   state.get("single_additional_applicants_question", "").lower() not in ["no", "n", "nope"]),
        "next": "additional_applicant_dob"
    },
    {
        "id": "additional_applicant_dob",
        "text": "What is the additional applicant's date of birth?",
        "required": False,
        "condition": lambda state: (state.get("additional_applicants_question", "").lower() not in ["no", "n", "nope"] or 
                                   state.get("single_additional_applicants_question", "").lower() not in ["no", "n", "nope"]),
        "next": "additional_applicant_first_time_buyer"
    },
    {
        "id": "additional_applicant_first_time_buyer",
        "text": "Is the additional applicant a first-time homebuyer? This means the additional applicant has never purchased any property anywhere in the world.",
        "required": False,
        "condition": lambda state: (state.get("additional_applicants_question", "").lower() not in ["no", "n", "nope"] or 
                                   state.get("single_additional_applicants_question", "").lower() not in ["no", "n", "nope"]),
        "next": "additional_applicant_citizenship"
    },
    {
        "id": "additional_applicant_citizenship",
        "text": "Is the additional applicant a Canadian Citizen or Permanent Resident? Please specify.",
        "required": False,
        "condition": lambda state: (state.get("additional_applicants_question", "").lower() not in ["no", "n", "nope"] or 
                                   state.get("single_additional_applicants_question", "").lower() not in ["no", "n", "nope"]),
        "next": "more_additional_applicants"
    },
    {
        "id": "more_additional_applicants",
        "text": "Thank you for providing the additional applicant details! Are there any other additional Applicants?",
        "required": False,
        "condition": lambda state: (state.get("additional_applicants_question", "").lower() not in ["no", "n", "nope"] or 
                                   state.get("single_additional_applicants_question", "").lower() not in ["no", "n", "nope"]),
        "next": lambda state: "multiple_owners_question" if state.get("more_additional_applicants", "").lower() in ["no", "n", "nope"] else "additional_applicant_transition"
    },
    {
        "id": "multiple_owners_question",
        "text": "Will the property have multiple owners?",
        "required": True,
        "condition": lambda state: (state.get("marital_status", "").lower() in ["married", "common law partner", "common law", "common-law"] or
                                  state.get("additional_applicants_question", "").lower() not in ["no", "n", "nope"] or
                                  state.get("single_additional_applicants_question", "").lower() not in ["no", "n", "nope"]),
        "next": lambda state: "title_holding_question" if state.get("multiple_owners_question", "").lower() in ["yes", "y", "yeah"] else "farewell"
    },
    {
        "id": "title_holding_question",
        "text": "How do you intend to hold the title? There are two options. Option one: Joint Tenancy - This is usually chosen by spouses as the interest in the property automatically passes to the surviving owner in case of the other owner's death - in this case all owners must have equal ownership shares. Option two is Tenants in common. In this case, each owner's share goes to their estate/heirs upon death. Unlike in the first option, ownership can be unequal (e.g., one person owns 60%, the other 40%). What option you want to chose? Joint Tenancy or Tenants in Common?",
        "required": False,
        "condition": lambda state: state.get("multiple_owners_question", "").lower() in ["yes", "y", "yeah"],
        "next": lambda state: "primary_applicant_ownership_percentage" if state.get("title_holding_question", "").lower() == "tenants in common" else "farewell"
    },
    {
        "id": "primary_applicant_ownership_percentage",
        "text": "What will be your percentage of ownership?",
        "required": False,
        "condition": lambda state: state.get("title_holding_question", "").lower() == "tenants in common",
        "next": lambda state: "spouse_ownership_percentage" if state.get("marital_status", "").lower() in ["married", "common law partner", "common law", "common-law"] else "additional_applicant_ownership_percentage"
    },
    {
        "id": "spouse_ownership_percentage",
        "text": "What will be your spouse's share of ownership?",
        "required": False,
        "condition": lambda state: (state.get("title_holding_question", "").lower() == "tenants in common" and
                                  state.get("marital_status", "").lower() in ["married", "common law partner", "common law", "common-law"]),
        "next": lambda state: "additional_applicant_ownership_percentage" if state.get("additional_applicants_question", "").lower() not in ["no", "n", "nope"] else "farewell"
    },
    {
        "id": "additional_applicant_ownership_percentage",
        "text": "What will be the additional applicant's share of ownership?",
        "required": False,
        "condition": lambda state: (state.get("title_holding_question", "").lower() == "tenants in common" and
                                  ((state.get("additional_applicants_question", "").lower() not in ["no", "n", "nope"]) or
                                   (state.get("single_additional_applicants_question", "").lower() not in ["no", "n", "nope"]))),
        "next": "farewell"
    },
    # {
    #     "id": "mortgage_advisor",
    #     "text": "Would you know who your Mortgage Advisor is? If yes, please share their full name, Brokerage and your lender.",
    #     "required": True,
    #     "next": "real_estate_agent"
    # },
    # {
    #     "id": "real_estate_agent",
    #     "text": "Please share the details of your real estate agent. What is their full-name and Real Estate Brokerage Company?",
    #     "required": True,
    #     "next": "home_insurance"
    # },
    # {
    #     "id": "home_insurance",
    #     "text": "If you are financing your home, it is likely that the lender will require you to have Home Insurance. Have you acquired Home Insurance yet?",
    #     "required": True,
    #     "next": lambda state: "home_insurance_details" if state.get("home_insurance", "").lower() in ["yes", "y", "yeah"] else "farewell"
    # },
    # {
    #     "id": "home_insurance_details",
    #     "text": "Please share more details of the home insurance company and their advisor.",
    #     "required": False,
    #     "condition": lambda state: state.get("home_insurance", "").lower() in ["yes", "y", "yeah"],
    #     "next": "farewell"
    # },
    {
        "id": "farewell",
        "text": "We've completed your Intake! We will send you an email with the summary of the information you provided to us shortly. Don't worry if there are typos or any missing information. You will be able to adjust anything on the Philer Platform - we will also provide you with instructions to access it. Finally, we will ask you to send two pieces of ID and any other required documents you haven't sent them to us already. Everything you need to know will be in the email we are sending shortly. Thank you for choosing Philer for your real estate closing! Have a good day!",
        "required": True,
        "next": None
    }
] 