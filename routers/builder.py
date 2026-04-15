from fastapi import APIRouter, Request, HTTPException, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import logging
from library.helpers import get_text
from library.app_logic import modeler
from library.classes import BuilderInput, ModelerOutput, ModelerAPIOutput

router = APIRouter()

# Set up templates directory
templates = Jinja2Templates(directory="templates")


# Function to handle modeler logic
def modeler_logic(input_data: BuilderInput) -> ModelerOutput:
    logging.info("entering function modeler_logic")
    logging.info(f'Received input: {input_data.model_dump_json()}')
    try:
        # Call the builder function from helpers
        return modeler(input_data)
    except Exception as e:
        logging.error(f"Error in modeler function: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# POST endpoint for form submission and returning JSON
@router.post("/api/modeler", summary="Network Modelling Function (JSON)",
             description="This endpoint accepts a JSON structure containing the user's input parameters and returns the results as JSON",
             response_model=ModelerAPIOutput,
             tags=["API POST Endpoints"],
             include_in_schema=True
             )
async def modeler_api(input_data: BuilderInput = Body(
    ...,
    example={
        "total_potential_users": 500,
        "area_sqkm": 100,
        "iso_3": "PER",
        "users_per_household": 4,
        "terrain_type": "None",
        "vegetation_type": "None",
        "system_life": 10,
        "year_1_traffic": 10,
        "traffic_growth": 30,
        "labour_cost": 25.0,
        "mains_power_installation_cost": 2000.0,
        "mains_power_cost_kwh": 0.65,
        "solar_cost_watt": 0.6,
        "battery_cost_watt_hour": 0.42,
        "charger_inverter_base": 50.0,
        "charger_inverter_variable": 0.35,
        "solar_efficiency": 20,
        "solar_derating": 0.1,
        "battery_age_derating": 0.5,
        "locations": [
            {
                "location_name": "Location 1",
                "tower_cost": 1000,
                "network_type": ["ISM Wi-Fi 2.4 GHz", "ISM FWA 5.8 GHz"],
                "sectors": [2, 2],
                "network_links": ["ISM FWA 500"],
                "backhaul_links": [],
                "backhaul_cost_base": [],
                "backhaul_cost_mbps": [],
                "power_type": "power_mains_rel"
            },
            {
                "location_name": "Location 2",
                "tower_cost": 2000,
                "network_type": ["ISM Wi-Fi 2.4 GHz", "ISM FWA 5.8 GHz"],
                "sectors": [2, 2],
                "network_links": ["ISM FWA 500", "ISM FWA 500"],
                "backhaul_links": ["LEO Satellite"],
                "backhaul_cost_base": [100],
                "backhaul_cost_mbps": [5],
                "power_type": "power_mains_int"
            },
            {
                "location_name": "Location 3",
                "tower_cost": 6000,
                "network_type": ["ISM Wi-Fi 2.4 GHz", "ISM FWA 5.8 GHz"],
                "sectors": [3, 1],
                "network_links": ["ISM FWA 500"],
                "backhaul_links": ["Fibre 1G", "HTS VSAT"],
                "backhaul_cost_base": [200, 50],
                "backhaul_cost_mbps": [0.5, 20],
                "power_type": "power_solar"
            }
        ]
    }
)):
    # Use the modeler_logic function to get the result
    return modeler_logic(input_data)
