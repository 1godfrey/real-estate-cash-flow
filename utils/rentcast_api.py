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
    
    querystring = {
        "zip": zip_code,
        "bedrooms": str(capped_bedrooms),
        "propertyType": "SFH"  # Single Family Home - a reasonable default
    }
    
    headers = {
        "accept": "application/json",
        "X-Api-Key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        
        data = response.json()
        
        if "rent" in data:
            return float(data["rent"])
        else:
            logging.warning(f"No rent data found for ZIP {zip_code}, {bedrooms} bedrooms")
            
            # If no SFH data, try with multifamily as fallback
            querystring["propertyType"] = "MFH"
            response = requests.get(url, headers=headers, params=querystring)
            response.raise_for_status()
            
            data = response.json()
            if "rent" in data:
                return float(data["rent"])
                
            return None
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching RentCast data for ZIP {zip_code}: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"API response: {e.response.text}")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"Error parsing RentCast API response for ZIP {zip_code}: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error with RentCast API for ZIP {zip_code}: {str(e)}")
        return None
