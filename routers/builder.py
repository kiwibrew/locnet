from fastapi import APIRouter, Request, HTTPException, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import logging
from app.dependencies import DataRepositoryDependency
from app.repositories import DataRepository
from library.helpers import get_text
from library.app_logic import modeler
from library.classes import BuilderInput, ModelerOutput, ModelerAPIOutput
from library.geospatial import (
    GEOSPATIAL_API_ERROR_DETAIL,
    GeospatialConfigurationError,
    GeospatialServiceError,
)

router = APIRouter()

# Set up templates directory
templates = Jinja2Templates(directory="templates")


# Function to handle modeler logic
async def modeler_logic(
    input_data: BuilderInput,
    repository: DataRepository,
) -> ModelerOutput:
    logging.info("entering function modeler_logic")
    logging.info(f'Received input: {input_data.model_dump_json()}')
    try:
        # Call the builder function from helpers
        return await modeler(input_data, repository)
    except HTTPException:
        raise
    except GeospatialConfigurationError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except GeospatialServiceError as e:
        logging.error("Geospatial API failure: %s", e)
        raise HTTPException(
            status_code=502,
            detail=GEOSPATIAL_API_ERROR_DETAIL,
        ) from e
    except ValueError as e:
        logging.error(f"{e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logging.exception("Error in modeler function")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/api/modeler/validate",
    summary="Validate a saved network model",
    description="Validates a saved network model against the BuilderInput schema.",
    response_model=BuilderInput,
    tags=["API POST Endpoints"],
    include_in_schema=False,
)
async def validate_model_input(input_data: BuilderInput) -> BuilderInput:
    """Return a BuilderInput only after Pydantic has validated the request body."""
    return input_data


# POST endpoint for form submission and returning JSON
@router.post("/api/modeler", summary="Network Modelling Function (JSON)",
             description="This endpoint accepts a JSON structure containing the user's input parameters and returns the results as JSON",
             response_model=ModelerAPIOutput,
             tags=["API POST Endpoints"],
             include_in_schema=True
             )
async def modeler_api(repository: DataRepositoryDependency, input_data: BuilderInput = Body(
    ...,
    example={
        "model_version": 2,
        "iso_3": "PER",
        "area_sqkm": 100,
        "households_total": 100,
        "users_per_household": 3.19,
        "total_potential_users": 319,
        "pop_growth_rate": 1.1,
        "hh_income_week": 245.9,
        "paf_usd_hour": 0.6,
        "capex_subsidy": 10000,
        "businesses": 1,
        "business_users": 2,
        "service_providers": 1,
        "service_provider_users": 2,
        "paf_deterred_use": 13,
        "paf_sub_use": 4,
        "paf_non_sub_use": 9,
        "paf_facilities_charge": 0.25,
        "provider_type": "provider_community",
        "oc_margin": 15,
        "other_opex": 7.5,
        "corp_tax": 0,
        "wacc": 6,
        "finance_cost": 5,
        "staff_opex_fixed": 1.2,
        "staff_opex_variable": 0.3,
        "power_reliable_hours": 4,
        "power_intermittent_hours": 24,
        "power_offgrid_hours": 48,
        "power_hybrid_hours": 12,
        "labour_cost": 4.6,
        "maintenance_opex": 2,
        "opex_subsidy": 0,
        "ue_subsidy": 0,
        "ue_cost": 100,
        "debt_proportion": 50,
        "inflation": 2.01,
        "spectrum_licence_fee": 0,
        "community_capex_discount": 0,
        "system_life": 10,
        "year_1_traffic": 10,
        "traffic_growth": 25,
        "hh_size": 3.5,
        "existing_ue_above_med": 50,
        "existing_ue_below_med": 30,
        "mains_power_installation_cost": 2000,
        "mains_power_cost_kwh": 0.65,
        "solar_cost_watt": 0.6,
        "battery_cost_watt_hour": 0.3,
        "battery_dod": 80,
        "charger_inverter_base": 50,
        "charger_inverter_variable": 0.35,
        "solar_efficiency": 21,
        "solar_derating": 0.5,
        "battery_age_derating": 0.5,
        "locations": [
            {
                "location_name": "Location 1",
                "latitude": -12.0464,
                "longitude": -77.0428,
                "radius": 2,
                "households": None,
                "power_type": "power_mains_rel",
                "tower_cost": 1000,
                "tower_opex": 0,
                "tower_height": 6,
                "network_type": ["ISM FWA 5.8 GHz", "ISM Wi-Fi 2.4 GHz"],
                "sectors": [1, 1],
                "network_links": ["ISM FWA 500"],
                "backhaul_links": [],
                "backhaul_cost_base": [],
                "backhaul_cost_mbps": []
            },
            {
                "location_name": "Location 2",
                "latitude": -13.1631,
                "longitude": -72.545,
                "radius": 2,
                "households": None,
                "power_type": "power_mains_rel",
                "tower_cost": 1000,
                "tower_opex": 0,
                "tower_height": 6,
                "network_type": ["ISM FWA 5.8 GHz", "ISM Wi-Fi 2.4 GHz"],
                "sectors": [1, 1],
                "network_links": ["ISM FWA 500", "ISM FWA 500"],
                "backhaul_links": ["LEO Satellite"],
                "backhaul_cost_base": [100],
                "backhaul_cost_mbps": [5]
            },
            {
                "location_name": "Location 3",
                "latitude": -16.409,
                "longitude": -71.5375,
                "radius": 2,
                "households": None,
                "power_type": "power_solar",
                "tower_cost": 1000,
                "tower_opex": 0,
                "tower_height": 6,
                "network_type": ["ISM FWA 5.8 GHz", "ISM Wi-Fi 2.4 GHz"],
                "sectors": [1, 1],
                "network_links": ["ISM FWA 500"],
                "backhaul_links": ["Fibre 1G", "HTS VSAT"],
                "backhaul_cost_base": [200, 50],
                "backhaul_cost_mbps": [0.5, 20]
            }
        ]
    }
 )):
    # Use the modeler_logic function to get the result
    return await modeler_logic(input_data, repository)
