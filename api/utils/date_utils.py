"""
Date Utility Functions

This module provides functions for normalizing and working with dates.
"""

import re
from datetime import datetime

def normalize_date(date_str: str) -> str:
    """
    Normalize a spoken date into YYYY-MM-DD format.
    Handles various spoken date formats like:
    - "july twenty seventh two thousand and one"
    - "july 27 2001"
    - "7/27/2001"
    - "27-07-2001"
    - "july first two thousand one"
    - "the third of september, nineteen ninety-five"
    
    Returns:
        Normalized date string in YYYY-MM-DD format
        "incomplete" if the date cannot be properly parsed
    """
    date_str = date_str.lower().strip()
    
    # Dictionary for month names and abbreviations
    months = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sept': 9, 'sep': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
    
    # Dictionary for number words
    number_words = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
        'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
        'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
        'eighty': 80, 'ninety': 90
    }
    
    # Dictionary for ordinal numbers
    ordinal_words = {
        'first': 1, '1st': 1,
        'second': 2, '2nd': 2,
        'third': 3, '3rd': 3,
        'fourth': 4, '4th': 4,
        'fifth': 5, '5th': 5,
        'sixth': 6, '6th': 6,
        'seventh': 7, '7th': 7,
        'eighth': 8, '8th': 8,
        'ninth': 9, '9th': 9,
        'tenth': 10, '10th': 10,
        'eleventh': 11, '11th': 11,
        'twelfth': 12, '12th': 12,
        'thirteenth': 13, '13th': 13,
        'fourteenth': 14, '14th': 14,
        'fifteenth': 15, '15th': 15,
        'sixteenth': 16, '16th': 16,
        'seventeenth': 17, '17th': 17,
        'eighteenth': 18, '18th': 18,
        'nineteenth': 19, '19th': 19,
        'twentieth': 20, '20th': 20,
        'thirtieth': 30, '30th': 30,
        'fortieth': 40, '40th': 40,
        'fiftieth': 50, '50th': 50,
        'sixtieth': 60, '60th': 60,
        'seventieth': 70, '70th': 70,
        'eightieth': 80, '80th': 80,
        'ninetieth': 90, '90th': 90
    }
    
    # Add compound ordinals (twenty-first, twenty-second, etc.)
    for tens_digit, tens_value in [('twenty', 20), ('thirty', 30), ('forty', 40), 
                                  ('fifty', 50), ('sixty', 60), ('seventy', 70), 
                                  ('eighty', 80), ('ninety', 90)]:
        for units_digit in ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 
                            'seventh', 'eighth', 'ninth']:
            compound = f"{tens_digit}-{units_digit}"
            simple_compound = f"{tens_digit}{units_digit}"
            
            # Extract the units value from the ordinal word
            units_value = ordinal_words[units_digit]
            
            # Add compound ordinals with and without hyphens
            ordinal_words[compound] = tens_value + units_value
            ordinal_words[simple_compound] = tens_value + units_value
    
    try:
        # Try parsing standard date formats first
        for fmt in ['%m/%d/%Y', '%d-%m-%Y', '%Y-%m-%d', '%B %d %Y', '%b %d %Y', '%d %B %Y', '%d %b %Y']:
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Extract month
        month = None
        for m in months:
            if m in date_str.split():  # Only match whole words
                month = months[m]
                break
            
        # If no whole word match, try substring match for abbreviated months
        if not month:
            for m in months:
                if len(m) <= 3 and m in date_str:  # Only abbreviations
                    month = months[m]
                    break
        
        if not month:
            return "incomplete"
        
        # Extract day
        day = None
        
        # First check for ordinals
        for ordinal_word, value in ordinal_words.items():
            if ordinal_word in date_str:
                day = value
                break
                
        # If no ordinal match, try to find a numeric day
        if not day:
            day_match = re.search(r'\b(\d{1,2})(st|nd|rd|th)?\b', date_str)
            if day_match:
                day = int(day_match.group(1))
            else:
                # Try to find a day as a number word (one, two, etc.)
                for word in date_str.split():
                    if word in number_words:
                        day = number_words[word]
                        break
                        
                # Handle compound numbers like "twenty one" without hyphens
                if not day:
                    for tens_word in ['twenty', 'thirty']:
                        if tens_word in date_str:
                            tens_value = number_words[tens_word]
                            # Look for units digit after tens
                            for units_word in ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']:
                                if units_word in date_str and date_str.find(tens_word) < date_str.find(units_word):
                                    units_value = number_words[units_word]
                                    day = tens_value + units_value
                                    break
                            if day:
                                break
        
        if not day or day > 31:  # Basic validation
            return "incomplete"
        
        # Extract year
        year = None
        
        # First try to find a numeric year
        year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
        if year_match:
            year = int(year_match.group(0))
        else:
            # Try to match expressions like "two thousand and one" or "nineteen ninety-five"
            if 'thousand' in date_str:
                # Handle "two thousand (and) one/two/etc."
                base = 2000
                for word in date_str.split():
                    if word in number_words and word != 'thousand' and date_str.find('thousand') < date_str.find(word):
                        year = base + number_words[word]
                        break
                
                # If no specific year found after "thousand", use 2000
                if not year and 'thousand' in date_str:
                    for word in date_str.split():
                        if word in ['one', 'two'] and date_str.find(word) < date_str.find('thousand'):
                            base = number_words[word] * 1000
                            break
                    
                    year = base
                    
                    # Look for additional years after thousand
                    units_value = 0
                    for unit_word in ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
                                     'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
                                     'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty', 'thirty']:
                        if unit_word in date_str and date_str.find('thousand') < date_str.find(unit_word):
                            units_value = number_words[unit_word]
                            break
                    
                    if units_value > 0:
                        year += units_value
            
            # Handle "nineteen ninety five" format
            elif 'nineteen' in date_str or 'twenty' in date_str:
                for prefix in ['nineteen', 'twenty']:
                    if prefix in date_str:
                        prefix_value = 1900 if prefix == 'nineteen' else 2000
                        
                        # Look for the decade
                        for decade in ['twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']:
                            if decade in date_str and date_str.find(prefix) < date_str.find(decade):
                                decade_value = number_words[decade]
                                
                                # Year base (e.g., 1990 from "nineteen ninety")
                                year_base = prefix_value + decade_value
                                
                                # Look for the final digits
                                for unit in ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']:
                                    if unit in date_str and date_str.find(decade) < date_str.find(unit):
                                        year = year_base + number_words[unit]
                                        break
                                
                                # If no units found, use just the decade
                                if not year:
                                    year = year_base
                                
                                break
        
        # If still no year, use current year
        if not year:
            year = datetime.now().year
        
        # Validate the date
        try:
            date_obj = datetime(year, month, day)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return "incomplete"
            
    except Exception:
        return "incomplete" 