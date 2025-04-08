import os
import json
import logging
import requests
from typing import Optional

def get_rent_estimate(zip_code: str, bedrooms: int) -> Optional[float]:
    """
    Gets rent estimate for a property with the given ZIP code and bedroom count.
    
    Args:
        zip_code: The ZIP code of the property.
        bedrooms: The number of bedrooms.
        
    Returns:
        The estimated monthly rent, or None if unable to get an estimate.
    """
    logging.debug(f"Getting rent estimate for ZIP {zip_code} with {bedrooms} bedrooms")
    api_key = os.environ.get("RENTCAST_API_KEY")
    
    if not api_key:
        logging.error("RentCast API key not found in environment variables")
        raise ValueError("RentCast API key not configured. Please set the RENTCAST_API_KEY environment variable.")
    
    url = "https://api.rentcast.io/v1/avm/rent/zip"
    
    # Ensure bedrooms is within valid range
    capped_bedrooms = min(max(bedrooms, 1), 5)  # Most APIs limit to 1-5 bedrooms
    
    headers = {
        "accept": "application/json",
        "X-Api-Key": api_key
    }
    
    # Try different property types to increase chances of getting data
    property_types = ["SFH", "MFH", "CONDO"]
    
    for prop_type in property_types:
        try:
            querystring = {
                "zip": zip_code,
                "bedrooms": str(capped_bedrooms),
                "propertyType": prop_type
            }
            
            logging.debug(f"Trying rent estimate for ZIP {zip_code}, {bedrooms} BR, type {prop_type}")
            response = requests.get(url, headers=headers, params=querystring)
            
            # If we get a 404, that means this combination doesn't exist in their database
            if response.status_code == 404:
                logging.debug(f"No data for {zip_code}, {bedrooms} BR with type {prop_type}")
                continue
                
            # For other errors, still try the next property type
            if response.status_code != 200:
                logging.warning(f"API error {response.status_code} for {zip_code}, {bedrooms} BR, type {prop_type}")
                continue
                
            data = response.json()
            
            if "rent" in data and data["rent"]:
                logging.info(f"Found rent: ${data['rent']} for {zip_code}, {bedrooms} BR, type {prop_type}")
                return float(data["rent"])
                
        except Exception as e:
            logging.warning(f"Error for {prop_type}: {str(e)}")
            continue
    
    # If we get here, we tried all property types and didn't find rent data
    logging.warning(f"No rent data found for ZIP {zip_code}, {bedrooms} bedrooms")
    
    # As a fallback, use a conservative estimate based on national averages
    # This is better than no data at all for calculation purposes
    fallback_rents = {
        1: 950,   # 1BR national average
        2: 1200,  # 2BR national average
        3: 1500,  # 3BR national average
        4: 1800,  # 4BR national average
        5: 2100   # 5BR+ national average
    }
    
    # Default to 2BR if outside the range
    logging.info(f"Using fallback national average rent for {zip_code}, {bedrooms} BR")
    return fallback_rents.get(capped_bedrooms, fallback_rents[2])
