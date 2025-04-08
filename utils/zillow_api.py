import os
import time
import json
import logging
import requests
from typing import List, Dict, Any, Optional

def get_zillow_listings(zip_code: str) -> List[Dict[str, Any]]:
    """
    Fetches property listings from Zillow API for a given ZIP code.
    
    Args:
        zip_code: The ZIP code to search for properties.
        
    Returns:
        A list of property listings.
    """
    logging.info(f"Fetching Zillow listings for ZIP: {zip_code}")
    api_key = os.environ.get("ZILLOW_API_KEY")
    
    if not api_key:
        logging.error("Zillow API key not found in environment variables")
        raise ValueError("Zillow API key not configured. Please set the ZILLOW_API_KEY environment variable.")
    
    # Define our Zillow API endpoints
    search_endpoint = "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch"
    sale_endpoint = "https://zillow-com1.p.rapidapi.com/properties/list-for-sale"
    
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
    }
    
    # For high-end ZIP codes, use different search parameters
    # These areas often have different market dynamics
    high_end_zip_prefixes = ['902', '904', '945', '100', '101', '941']
    is_high_end_zip = any(zip_code.startswith(prefix) for prefix in high_end_zip_prefixes)
    all_properties = []
    
    # Try the primary search endpoint first
    try:
        if is_high_end_zip:
            logging.info(f"Using special search parameters for high-end ZIP code {zip_code}")
            querystring = {
                "location": zip_code,
                "home_type": "All",
                "sort": "Price_High_Low",  # For high-end areas, look at higher priced properties
                "page": "1"
            }
        else:
            querystring = {
                "location": zip_code,
                "home_type": "All",  # More inclusive to show all property types
                "sort": "Price_Low_High",
                "page": "1"
            }
        
        logging.info(f"Making API request to search endpoint for ZIP {zip_code} with params: {querystring}")
        response = requests.get(search_endpoint, headers=headers, params=querystring)
        logging.info(f"Zillow search API status for ZIP {zip_code}: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logging.info(f"Raw API response keys for ZIP {zip_code}: {list(data.keys())}")
            
            # Check if we have properties in the response
            if "props" in data and data["props"]:
                properties = data["props"]
                logging.info(f"Found {len(properties)} properties from search endpoint for ZIP {zip_code}")
                all_properties.extend(properties)
    
    except Exception as e:
        logging.error(f"Error with search endpoint for ZIP {zip_code}: {str(e)}")
    
    # If we got no results or we're dealing with a high-end ZIP, try the sale endpoint as well
    if len(all_properties) == 0 or is_high_end_zip:
        try:
            sale_querystring = {
                "location": zip_code,
                "page": "1",
                "sort": "Price Low to High" if not is_high_end_zip else "Price High to Low"
            }
            
            logging.info(f"Trying sale endpoint for ZIP {zip_code} with params: {sale_querystring}")
            sale_response = requests.get(sale_endpoint, headers=headers, params=sale_querystring)
            logging.info(f"Zillow sale API status for ZIP {zip_code}: {sale_response.status_code}")
            
            if sale_response.status_code == 200:
                sale_data = sale_response.json()
                logging.info(f"Sale API response keys for ZIP {zip_code}: {list(sale_data.keys())}")
                
                if "props" in sale_data and sale_data["props"]:
                    sale_properties = sale_data["props"] 
                    logging.info(f"Found {len(sale_properties)} properties from sale endpoint for ZIP {zip_code}")
                    all_properties.extend(sale_properties)
        
        except Exception as e:
            logging.error(f"Error with sale endpoint for ZIP {zip_code}: {str(e)}")
    
    # If still no properties, we've tried our best
    if len(all_properties) == 0:
        logging.warning(f"No properties found for ZIP code {zip_code} after trying multiple endpoints")
        return []
    
    logging.info(f"Combined total of {len(all_properties)} properties found for ZIP {zip_code}")
    
    # Remove duplicates based on address if present
    unique_properties = []
    seen_addresses = set()
    
    for prop in all_properties:
        address = prop.get('address', prop.get('streetAddress', ''))
        if address:
            if address not in seen_addresses:
                seen_addresses.add(address)
                unique_properties.append(prop)
        else:
            unique_properties.append(prop)
    
    logging.info(f"After removing duplicates: {len(unique_properties)} properties for ZIP {zip_code}")
    
    # Log property types for debugging
    property_types = set()
    for prop in unique_properties:
        home_type = prop.get('propertyType', prop.get('homeType', 'Unknown'))
        property_types.add(home_type)
        
    logging.info(f"Property types found in ZIP {zip_code}: {', '.join(property_types)}")
    return unique_properties
