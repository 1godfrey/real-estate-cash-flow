import os
import json
import logging
import requests
from typing import Optional

def get_rent_estimate(zip_code: str, bedrooms: int) -> float:
    """
    Gets rent estimate for a property with the given ZIP code and bedroom count.
    
    Args:
        zip_code: The ZIP code of the property.
        bedrooms: The number of bedrooms.
        
    Returns:
        The estimated monthly rent (always returns a value by using fallbacks if needed).
    """
    logging.info(f"Getting rent estimate for ZIP {zip_code} with {bedrooms} bedrooms")
    api_key = os.environ.get("RENTCAST_API_KEY")
    
    if not api_key:
        logging.error("RentCast API key not found in environment variables")
        raise ValueError("RentCast API key not configured. Please set the RENTCAST_API_KEY environment variable.")
    
    # Identify high-end ZIP codes that require special handling
    high_end_zip_prefixes = ['902', '904', '945', '100', '101', '941']
    is_high_end_zip = any(zip_code.startswith(prefix) for prefix in high_end_zip_prefixes)
    
    if is_high_end_zip:
        logging.info(f"High-end ZIP code {zip_code} detected - will use premium rent estimates if APIs fail")
    
    url = "https://api.rentcast.io/v1/avm/rent/zip"
    
    # Ensure bedrooms is within valid range
    capped_bedrooms = min(max(bedrooms, 1), 5)  # Most APIs limit to 1-5 bedrooms
    
    headers = {
        "accept": "application/json",
        "X-Api-Key": api_key
    }
    
    # Try different property types to increase chances of getting data
    # For high-end ZIPs, try luxury property types first
    property_types = ["CONDO", "SFH", "MFH"] if is_high_end_zip else ["SFH", "MFH", "CONDO"]
    
    # First, try with the exact bedroom count provided
    for prop_type in property_types:
        try:
            querystring = {
                "zip": zip_code,
                "bedrooms": str(capped_bedrooms),
                "propertyType": prop_type
            }
            
            logging.info(f"Trying rent estimate for ZIP {zip_code}, {bedrooms} BR, type {prop_type}")
            response = requests.get(url, headers=headers, params=querystring)
            logging.info(f"RentCast API response for {zip_code}, {bedrooms} BR, {prop_type}: {response.status_code}")
            
            # If we get a 404, that means this combination doesn't exist in their database
            if response.status_code == 404:
                logging.debug(f"No data for {zip_code}, {bedrooms} BR with type {prop_type}")
                continue
                
            # For other errors, still try the next property type
            if response.status_code != 200:
                logging.warning(f"API error {response.status_code} for {zip_code}, {bedrooms} BR, type {prop_type}")
                continue
                
            data = response.json()
            logging.info(f"RentCast API response data keys for {zip_code}: {list(data.keys())}")
            
            if "rent" in data and data["rent"]:
                rent = float(data["rent"])
                logging.info(f"Found rent: ${rent} for {zip_code}, {bedrooms} BR, type {prop_type}")
                return rent
                
        except Exception as e:
            logging.warning(f"Error for {prop_type}: {str(e)}")
            continue
    
    # If no results with the exact bedroom count, try with other bedroom counts
    # Some ZIP codes may have data for certain bedroom counts but not others
    other_bedroom_counts = [3, 2, 4, 1, 5]  # Try common ones first
    other_bedroom_counts = [b for b in other_bedroom_counts if b != capped_bedrooms]  # Remove current one
    
    logging.info(f"No data found for {zip_code} with {bedrooms} BR, trying other bedroom counts: {', '.join(map(str, other_bedroom_counts))}")
    
    for alt_bedrooms in other_bedroom_counts:
        for prop_type in property_types:
            try:
                querystring = {
                    "zip": zip_code,
                    "bedrooms": str(alt_bedrooms),
                    "propertyType": prop_type
                }
                
                logging.info(f"Trying alternative: ZIP {zip_code}, {alt_bedrooms} BR, type {prop_type}")
                response = requests.get(url, headers=headers, params=querystring)
                
                if response.status_code == 404:
                    continue
                    
                if response.status_code != 200:
                    continue
                    
                data = response.json()
                
                if "rent" in data and data["rent"]:
                    rent_value = float(data["rent"])
                    # Adjust the rent value based on bedroom differences
                    bedroom_diff = capped_bedrooms - alt_bedrooms
                    
                    # For high-end areas, each bedroom adds more value
                    bedroom_premium = 500 if is_high_end_zip else 200
                    adjusted_rent = rent_value + (bedroom_diff * bedroom_premium)
                    
                    logging.info(f"Found rent for {alt_bedrooms} BR: ${rent_value}, adjusted for {capped_bedrooms} BR: ${adjusted_rent}")
                    return adjusted_rent
                    
            except Exception as e:
                logging.warning(f"Error trying alternative bedrooms: {str(e)}")
                continue
    
    # If we get here, we tried all property types and didn't find rent data
    logging.info(f"No RentCast API data found for ZIP {zip_code}, {bedrooms} bedrooms - using fallback estimates")
    
    # For high-end ZIP codes, use premium rent estimates
    if is_high_end_zip:
        # High-end areas have much higher rents
        high_end_rents = {
            1: 3000,  # 1BR luxury
            2: 4500,  # 2BR luxury
            3: 6000,  # 3BR luxury
            4: 8000,  # 4BR luxury
            5: 12000  # 5BR+ luxury
        }
        rent_estimate = high_end_rents.get(capped_bedrooms, high_end_rents[3])
        logging.info(f"Using high-end premium rent estimate for {zip_code}, {bedrooms} BR: ${rent_estimate}")
        return rent_estimate
    
    # For regular areas, use standard national averages
    standard_rents = {
        1: 950,   # 1BR national average
        2: 1200,  # 2BR national average
        3: 1500,  # 3BR national average
        4: 1800,  # 4BR national average
        5: 2100   # 5BR+ national average
    }
    
    # Default to 2BR if outside the range
    rent_estimate = standard_rents.get(capped_bedrooms, standard_rents[2])
    logging.info(f"Using standard national average rent for {zip_code}, {bedrooms} BR: ${rent_estimate}")
    return rent_estimate
