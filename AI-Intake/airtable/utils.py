def populate_form_data(data: dict) -> dict:
    """
    Scan `data` for non-None values and map them into form_data[question_id] = answer.
    """
    form_data = {}

    # ——— Main Applicant ———
    mains = data.get('Main Applicant') or []
    if mains:
        applicant = mains[0]
        # Split full name
        full_name = applicant.get('Full Name')
        if full_name:
            parts = full_name.split(None, 1)
            form_data['applicant_first_name'] = parts[0]
            if len(parts) > 1:
                form_data['applicant_last_name'] = parts[1]
        # DOB
        if dob := applicant.get('Date of Birth'):
            form_data['applicant_dob'] = dob
        # First-time buyer?
        if 'First-time buyer' in applicant:
            form_data['applicant_first_time_buyer'] = \
                'Yes' if applicant['First-time buyer'] else 'No'
        # Citizenship
        if 'Canadian Citizen/PR' in applicant:
            form_data['applicant_citizenship'] = \
                'Yes' if applicant['Canadian Citizen/PR'] else 'No'
        # Decision-making capacity
        if 'Capable of making decisions?' in applicant:
            form_data['applicant_decision_making'] = \
                'Yes' if applicant['Capable of making decisions?'] else 'No'
        # Ownership %
        if own := applicant.get('Percentage of Ownership') is not None:
            form_data['primary_applicant_ownership_percentage'] = own

    # ——— Transaction & Property ———
    if tx := data.get('Transaction Type'):
        form_data['transaction_type'] = tx
    if pre := data.get('Pre Con?') is not None:
        # Map boolean to your phrasing
        form_data['property_construction_status'] = \
            'Pre-Construction' if data['Pre Con?'] else 'Built'
    if ptype := data.get('Property Type'):
        form_data['property_type'] = ptype
    if cdate := data.get('Closing Date'):
        form_data['closing_date'] = cdate
    if addr := data.get('Full Address'):
        form_data['property_address'] = addr
    if intent := data.get('Intent of Use'):
        form_data['property_usage'] = intent

    # ——— Personal status ———
    if ms := data.get('Marital Status'):
        form_data['marital_status'] = ms
    if hold := data.get('Holding Title As'):
        form_data['title_holding_question'] = hold

    # ——— Mortgage Advisor ———
    mort = data.get('Mortgage Agent') or []
    if mort:
        m = mort[0]
        parts = [
            m.get('Full Name'),
            m.get('Mortgage Brokerage'),
            m.get('Lender')
        ]
        form_data['mortgage_advisor'] = ', '.join(p for p in parts if p)

    # ——— Real Estate Agent ———
    rets = data.get('Realtor') or []
    if rets:
        r = rets[0]
        parts = [r.get('Full Name'), r.get('Real Estate Brokerage')]
        form_data['real_estate_agent'] = ', '.join(p for p in parts if p)

    # ——— Home Insurance ———
    ins = data.get('Insurance Agent') or []
    if ins:
        form_data['home_insurance'] = 'Yes'
        i = ins[0]
        parts = [i.get('Full Name'), i.get('Insurance Company')]
        form_data['home_insurance_details'] = ', '.join(p for p in parts if p)

    return form_data

