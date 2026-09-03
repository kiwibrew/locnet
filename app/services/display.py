from app.services.reference_data import demand_curve


def get_dc_points(dc_parameter_a, dc_parameter_b):
    para = dc_parameter_a
    parb = dc_parameter_b

    dc_inc_pct_a = 0.20
    dc_inc_pct_b = dc_inc_pct_a * 0.85
    dc_inc_pct_c = dc_inc_pct_b * 0.85
    dc_inc_pct_d = dc_inc_pct_c * 0.85
    dc_inc_pct_e = dc_inc_pct_d * 0.85
    dc_inc_pct_f = dc_inc_pct_e * 0.85
    dc_inc_pct_g = dc_inc_pct_f * 0.85
    dc_inc_pct_h = dc_inc_pct_g * 0.85
    dc_inc_pct_i = dc_inc_pct_h * 0.85
    dc_inc_pct_j = dc_inc_pct_i * 0.85
    dc_inc_pct_k = dc_inc_pct_j * 0.85
    dc_inc_pct_l = dc_inc_pct_k * 0.85

    dc_pen_a = demand_curve(dc_inc_pct_a, para, parb)
    dc_pen_b = demand_curve(dc_inc_pct_b, para, parb)
    dc_pen_c = demand_curve(dc_inc_pct_c, para, parb)
    dc_pen_d = demand_curve(dc_inc_pct_d, para, parb)
    dc_pen_e = demand_curve(dc_inc_pct_e, para, parb)
    dc_pen_f = demand_curve(dc_inc_pct_f, para, parb)
    dc_pen_g = demand_curve(dc_inc_pct_g, para, parb)
    dc_pen_h = demand_curve(dc_inc_pct_h, para, parb)
    dc_pen_i = demand_curve(dc_inc_pct_i, para, parb)
    dc_pen_j = demand_curve(dc_inc_pct_j, para, parb)
    dc_pen_k = demand_curve(dc_inc_pct_k, para, parb)
    dc_pen_l = demand_curve(dc_inc_pct_l, para, parb)

    dc_points = [
        {"x": dc_pen_a, "y": dc_inc_pct_a},
        {"x": dc_pen_b, "y": dc_inc_pct_b},
        {"x": dc_pen_c, "y": dc_inc_pct_c},
        {"x": dc_pen_d, "y": dc_inc_pct_d},
        {"x": dc_pen_e, "y": dc_inc_pct_e},
        {"x": dc_pen_f, "y": dc_inc_pct_f},
        {"x": dc_pen_g, "y": dc_inc_pct_g},
        {"x": dc_pen_h, "y": dc_inc_pct_h},
        {"x": dc_pen_i, "y": dc_inc_pct_i},
        {"x": dc_pen_j, "y": dc_inc_pct_j},
        {"x": dc_pen_k, "y": dc_inc_pct_k},
        {"x": dc_pen_l, "y": dc_inc_pct_l}
    ]

    return dc_points


def get_net_summary_table(country_name, system_life, year_1_traffic, traffic_growth,
                          backhaul_required, total_backhaul_available, total_power_required,
                          system_capex, access_capex, tower_capex, backhaul_capex,
                          midhaul_capex, power_capex):
    net_summary_table_rows = [
        # ---- Coverage Details ----
        {
            "row_type": "section",
            "label": "Coverage Details",
            "value": None,
            "unit": None,
        },
        {
            "row_type": "data",
            "label": "Country",
            "value": country_name,
            "unit": None,
        },

        # ---- Network Properties ----
        {
            "row_type": "section",
            "label": "Network Properties",
            "value": None,
            "unit": None,
        },
        {
            "row_type": "data",
            "label": "System Life",
            "value": system_life,
            "unit": "years",
        },
        {
            "row_type": "data",
            "label": "Year 1 Traffic",
            "value": year_1_traffic,
            "unit": "GB per user",
        },
        {
            "row_type": "data",
            "label": "Traffic Growth",
            "value": traffic_growth,
            "unit": "% per annum",
        },
        {
            "row_type": "data",
            "label": "Backhaul Required (year 10)",
            "value": backhaul_required,
            "unit": "Mbps",
        },
        {
            "row_type": "data",
            "label": "Backhaul Available",
            "value": total_backhaul_available,
            "unit": "Mbps",
        },
        {
            "row_type": "data",
            "label": "Total Power Required",
            "value": total_power_required,
            "unit": "Watts",
        },

        # ---- CapEx ----
        {
            "row_type": "section",
            "label": "CapEx",
            "value": None,
            "unit": None,
        },
        {
            "row_type": "data",
            "label": "Consolidated CapEx",
            "value": system_capex,
            "unit": "USD",
        },
        {
            "row_type": "data",
            "label": "Access Network CapEx",
            "value": access_capex,
            "unit": "USD",
        },
        {
            "row_type": "data",
            "label": "Towers CapEx",
            "value": tower_capex,
            "unit": "USD",
        },
        {
            "row_type": "data",
            "label": "Backhaul CapEx",
            "value": backhaul_capex,
            "unit": "USD",
        },
        {
            "row_type": "data",
            "label": "Network Links CapEx",
            "value": midhaul_capex,
            "unit": "USD",
        },
        {
            "row_type": "data",
            "label": "Power System CapEx",
            "value": power_capex,
            "unit": "USD",
        },
    ]

    net_summary_table_columns = [
        {"title": "Metric", "data": "label"},
        {"title": "Value", "data": "value"},
        {"title": "Unit", "data": "unit"},
    ]

    return net_summary_table_rows, net_summary_table_columns


def get_dcba_table(ndm,
                   cba_ndm_sp, cba_nu_sp, cba_gbm_sp, cba_mcec_sp, cba_moec_sp, cba_omsdm_sp, cba_tsec_sp,
                   cba_pen_sp, cba_dem_sp, cba_dgbm_sp, cba_aup_sp, cba_sur_ratio_sp, cba_sur_sp,
                   cba_soc_priv_rat_sp, cba_tacb_sp,
                   cba_ndm_bus, cba_nu_bus, cba_gbm_bus, cba_mcec_bus, cba_moec_bus, cba_omsdm_bus, cba_tsec_bus,
                   cba_pen_bus, cba_dem_bus, cba_dgbm_bus, cba_aup_bus, cba_sur_ratio_bus, cba_sur_bus,
                   cba_soc_priv_rat_bus, cba_tacb_bus,
                   cba_ndm_hha, cba_nu_hha, cba_gbm_hha, cba_mcec_hha, cba_moec_hha, cba_omsdm_hha, cba_tsec_hha,
                   cba_pen_hha, cba_dem_hha, cba_dgbm_hha, cba_aup_hha, cba_sur_ratio_hha, cba_sur_hha,
                   cba_soc_priv_rat_hha, cba_tacb_hha,
                   cba_ndm_hhb, cba_nu_hhb, cba_gbm_hhb, cba_mcec_hhb, cba_moec_hhb, cba_omsdm_hhb, cba_tsec_hhb,
                   cba_pen_hhb, cba_dem_hhb, cba_dgbm_hhb, cba_aup_hhb, cba_sur_ratio_hhb, cba_sur_hhb,
                   cba_soc_priv_rat_hhb, cba_tacb_hhb,
                   cba_nu_sub, cba_gbm_sub, cba_mcec_sub, cba_moec_sub, cba_omsdm_sub, cba_tsec_sub,
                   cba_pen_sub, cba_dem_sub, cba_dgbm_sub, cba_aup_sub, cba_sur_sub, cba_tacb_sub,
                   cba_mcec_paf, cba_moec_paf, cba_omsdm_paf, cba_tsec_paf, cba_dem_paf, cba_dgbm_paf,
                   cba_aup_paf, cba_sur_ratio_paf, cba_sur_paf, cba_soc_priv_rat_paf, cba_tacb_paf,
                   cba_nu_oo, cba_mcec_oo, cba_moec_oo, cba_dem_oo, cba_dgbm_oo, cba_aup_oo,
                   cba_sur_ratio_oo, cba_sur_oo, cba_tacb_oo):
    dcba_table_rows = [
        {
            "label": "Service providers",
            "cba_ndm": cba_ndm_sp,
            "cba_nu": cba_nu_sp,
            "cba_gbm": cba_gbm_sp,
            "cba_mcec": cba_mcec_sp,
            "cba_moec": cba_moec_sp,
            "cba_omsdm": cba_omsdm_sp,
            "cba_tsec": cba_tsec_sp,
            "cba_pen": cba_pen_sp,
            "cba_dem": cba_dem_sp,
            "cba_dgbm": cba_dgbm_sp,
            "cba_aup": cba_aup_sp,
            "cba_sur_ratio": cba_sur_ratio_sp,
            "cba_sur": cba_sur_sp,
            "cba_soc": cba_soc_priv_rat_sp,
            "cba_tacb": cba_tacb_sp
        },
        {
            "label": "Corporate/business",
            "cba_ndm": cba_ndm_bus,
            "cba_nu": cba_nu_bus,
            "cba_gbm": cba_gbm_bus,
            "cba_mcec": cba_mcec_bus,
            "cba_moec": cba_moec_bus,
            "cba_omsdm": cba_omsdm_bus,
            "cba_tsec": cba_tsec_bus,
            "cba_pen": cba_pen_bus,
            "cba_dem": cba_dem_bus,
            "cba_dgbm": cba_dgbm_bus,
            "cba_aup": cba_aup_bus,
            "cba_sur_ratio": cba_sur_ratio_bus,
            "cba_sur": cba_sur_bus,
            "cba_soc": cba_soc_priv_rat_bus,
            "cba_tacb": cba_tacb_bus
        },
        {
            "label": "Households (above median income)",
            "cba_ndm": cba_ndm_hha,
            "cba_nu": cba_nu_hha,
            "cba_gbm": cba_gbm_hha,
            "cba_mcec": cba_mcec_hha,
            "cba_moec": cba_moec_hha,
            "cba_omsdm": cba_omsdm_hha,
            "cba_tsec": cba_tsec_hha,
            "cba_pen": cba_pen_hha,
            "cba_dem": cba_dem_hha,
            "cba_dgbm": cba_dgbm_hha,
            "cba_aup": cba_aup_hha,
            "cba_sur_ratio": cba_sur_ratio_hha,
            "cba_sur": cba_sur_hha,
            "cba_soc": cba_soc_priv_rat_hha,
            "cba_tacb": cba_tacb_hha
        },
        {
            "label": "Households (below median income)",
            "cba_ndm": cba_ndm_hhb,
            "cba_nu": cba_nu_hhb,
            "cba_gbm": cba_gbm_hhb,
            "cba_mcec": cba_mcec_hhb,
            "cba_moec": cba_moec_hhb,
            "cba_omsdm": cba_omsdm_hhb,
            "cba_tsec": cba_tsec_hhb,
            "cba_pen": cba_pen_hhb,
            "cba_dem": cba_dem_hhb,
            "cba_dgbm": cba_dgbm_hhb,
            "cba_aup": cba_aup_hhb,
            "cba_sur_ratio": cba_sur_ratio_hhb,
            "cba_sur": cba_sur_hhb,
            "cba_soc": cba_soc_priv_rat_hhb,
            "cba_tacb": cba_tacb_hhb
        },
        {
            "label": "Sub total",
            "cba_ndm": ndm,
            "cba_nu": cba_nu_sub,
            "cba_gbm": cba_gbm_sub,
            "cba_mcec": cba_mcec_sub,
            "cba_moec": cba_moec_sub,
            "cba_omsdm": cba_omsdm_sub,
            "cba_tsec": cba_tsec_sub,
            "cba_pen": cba_pen_sub,
            "cba_dem": cba_dem_sub,
            "cba_dgbm": cba_dgbm_sub,
            "cba_aup": cba_aup_sub,
            "cba_sur_ratio": None,
            "cba_sur": cba_sur_sub,
            "cba_soc": None,
            "cba_tacb": cba_tacb_sub
        },
        {
            "label": "Public access facilities",
            "cba_ndm": None,
            "cba_nu": None,
            "cba_gbm": None,
            "cba_mcec": cba_mcec_paf,
            "cba_moec": cba_moec_paf,
            "cba_omsdm": cba_omsdm_paf,
            "cba_tsec": cba_tsec_paf,
            "cba_pen": None,
            "cba_dem": cba_dem_paf,
            "cba_dgbm": cba_dgbm_paf,
            "cba_aup": cba_aup_paf,
            "cba_sur_ratio": cba_sur_ratio_paf,
            "cba_sur": cba_sur_paf,
            "cba_soc": cba_soc_priv_rat_paf,
            "cba_tacb": cba_tacb_paf
        },
        {
            "label": "Overall",
            "cba_ndm": ndm,
            "cba_nu": cba_nu_oo,
            "cba_gbm": None,
            "cba_mcec": cba_mcec_oo,
            "cba_moec": cba_moec_oo,
            "cba_omsdm": None,
            "cba_tsec": None,
            "cba_pen": None,
            "cba_dem": cba_dem_oo,
            "cba_dgbm": cba_dgbm_oo,
            "cba_aup": cba_aup_oo,
            "cba_sur_ratio": cba_sur_ratio_oo,
            "cba_sur": cba_sur_oo,
            "cba_soc": None,
            "cba_tacb": cba_tacb_oo
        }
    ]

    dcba_table_columns = [
        {"title": "Segment", "data": "label"},
        {"title": "Number of decision makers", "data": "cba_ndm"},
        {"title": "Number of users", "data": "cba_nu"},
        {"title": "GB per month demand (100% takeup)", "data": "cba_gbm"},
        {"title": "Monthly capex economic cost (including power and after subsidy) per decision maker",
         "data": "cba_mcec"},
        {"title": "Monthly Opex economic cost (after subsidy) per decision maker", "data": "cba_moec"},
        {"title": "Other monthly spend per decision maker (after subsidy)", "data": "cba_omsdm"},
        {"title": "Total system economic cost per month per decision maker (after subsidy)", "data": "cba_tsec"},
        {"title": "Penetration rate", "data": "cba_pen"},
        {"title": "Number of actual users", "data": "cba_dem"},
        {"title": "GB per month demand (actual)", "data": "cba_dgbm"},
        {"title": "Annual user payments to network provider", "data": "cba_aup"},
        {"title": "Consumer Surplus ratio", "data": "cba_sur_ratio"},
        {"title": "Consumer Surplus", "data": "cba_sur"},
        {"title": "Social to Private Benefit ratio", "data": "cba_soc"},
        {"title": "Total Annual Community Benefit", "data": "cba_tacb"},
    ]

    return dcba_table_rows, dcba_table_columns
