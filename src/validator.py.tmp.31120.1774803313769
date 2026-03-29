import re

def validate_data(data, confidence_score):
    """
    Takes the extracted data dictionary and an OCR confidence score.
    Returns a new dictionary with validation status columns added.
    Colors requested by user:
    - Green: Valid / High Confidence
    - Yellow: Low Confidence OCR
    - Red: Missing Field
    For dataframes, we just assign the status string, and Streamlit can color it via Pandas styling.
    """
    validated = data.copy()
    
    # Base status if OCR confidence is very low, we might mark things Yellow unless they are strictly validated
    is_low_conf = confidence_score < 0.75
    
    # 1. Essential Fields Validation
    for field in ['Name', 'Company', 'Title', 'Address', 'City', 'State', 'Country', 'Website', 'Mobile']:
        status_key = f'status_{field.lower()}'
        val = validated.get(field, '').strip()
        
        if not val:
            validated[status_key] = '🔴'
        else:
            if is_low_conf:
                validated[status_key] = '🟡'
            else:
                validated[status_key] = '🟢'

    # 2. Strict Format Fields Validation
    # Email
    email = validated.get('Email', '').strip()
    status_email = 'status_email'
    if not email:
        validated[status_email] = '🔴'
    else:
        # Check strict regex
        if re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', email):
            validated[status_email] = '🟡' if is_low_conf else '🟢'
        else:
            validated[status_email] = '🟡' # format is slightly off, but something is there
            
    # Phone
    phone = validated.get('Phone', '').strip()
    status_phone = 'status_phone'
    if not phone:
        validated[status_phone] = '🔴'
    else:
        validated[status_phone] = '🟡' if is_low_conf else '🟢'
        
    # Zip
    zip_code = validated.get('Zip', '').strip()
    status_zip = 'status_zip'
    if not zip_code:
        validated[status_zip] = '🔴'
    else:
        if re.match(r'^\d{5}(?:-\d{4})?$', zip_code):
            validated[status_zip] = '🟡' if is_low_conf else '🟢'
        else:
            validated[status_zip] = '🟡'

    return validated
