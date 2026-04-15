import logging
import math
import numpy_financial as npf


def get_pl_lab_cos_by_year(
        system_life: int,
        opex_ftes_fixed: float,
        opex_ftes_variable: float,
        total_users_supported: float,
        cba_pen_sub: float,
        pop_growth_rate: float,
        hh_income_week: float,
        inf: float,
        tu_rates: dict
) -> dict:
    pl_lab_cos_by_year = {}

    for year in range(1, 11):
        if year > system_life:
            pl_lab_cos = 0
            # logging.info(f"Year {year}: Beyond system life, pl_lab_cos_y{year} = 0")
        else:
            # years_elapsed = year - 1  # C2 is year 1
            # logging.info(f"Year {year}: years_elapsed = {year}")

            # Growth multipliers
            pop_multiplier = math.pow(1 + pop_growth_rate, year)
            inf_multiplier = math.pow(1 + inf, year)

            # logging.info(f"Year {year}: pop_multiplier = {pop_multiplier}, inf_multiplier = {inf_multiplier}")

            # Effective take-up rate
            tu_rate = tu_rates.get(year, 1)
            # logging.info(f"Year {year}: tu_rate = {tu_rate}")

            # Labour headcount
            labour_headcount = (
                    opex_ftes_fixed +
                    opex_ftes_variable * total_users_supported * (cba_pen_sub / 100) * tu_rate * pop_multiplier
            )
            # logging.info(f"Year {year}: labour_headcount = {labour_headcount}")

            # Wage cost per FTE
            wage_cost_per_fte = (hh_income_week / 1.5) * 52 * inf_multiplier
            # logging.info(f"Year {year}: wage_cost_per_fte = {wage_cost_per_fte}")

            # Total labour cost in millions
            pl_lab_cos = (labour_headcount * wage_cost_per_fte) / 1_000_000
            # logging.info(f"Year {year}: pl_lab_cos_y{year} = {pl_lab_cos}")

        pl_lab_cos_by_year[f"pl_lab_cos_y{year}"] = pl_lab_cos

    return pl_lab_cos_by_year


def get_pl_oth_sys_op_cos_by_year(
    system_life: int,
    pl_lab_cos_by_year: dict,
    opex_other: float
) -> dict:
    pl_oth_sys_op_cos_by_year = {}

    for year in range(1, 11):
        pl_lab_cos = pl_lab_cos_by_year.get(f"pl_lab_cos_y{year}", 0)

        if year <= 3:
            # Years 1–3: no system life check
            pl_oth_sys_op_cos = pl_lab_cos * opex_other
            # logging.info(f"Year {year}: (no system life check) pl_lab_cos = {pl_lab_cos}, pl_oth_sys_op_cos_y{year} = {pl_oth_sys_op_cos}")
        else:
            # Years 4–10: system life check
            if (year - 3) > system_life:
                pl_oth_sys_op_cos = 0
                # logging.info(f"Year {year}: Beyond system life, pl_oth_sys_op_cos_y{year} = 0")
            else:
                pl_oth_sys_op_cos = pl_lab_cos * opex_other
                # logging.info(f"Year {year}: pl_lab_cos = {pl_lab_cos}, pl_oth_sys_op_cos_y{year} = {pl_oth_sys_op_cos}")

        pl_oth_sys_op_cos_by_year[f"pl_oth_sys_op_cos_y{year}"] = pl_oth_sys_op_cos

    return pl_oth_sys_op_cos_by_year


def get_pl_bh_pow_op_cos_by_year(
    system_life: int,
    backhaul_opex: float,
    power_opex: float,
    inf: float
) -> dict:
    pl_bh_pow_op_cos_by_year = {}
    annual_base = (backhaul_opex + power_opex) / system_life
    # logging.info(f"Base annual opex (backhaul + power) per year: {annual_base}")

    for year in range(1, 11):
        years_elapsed = year - 1
        inf_multiplier = math.pow(1 + inf, years_elapsed)
        pl_op_cos = (annual_base * inf_multiplier) / 1_000_000

        # logging.info(f"Year {year}: inf_multiplier = {inf_multiplier}, pl_bh_pow_op_cos_y{year} = {pl_op_cos}")

        pl_bh_pow_op_cos_by_year[f"pl_bh_pow_op_cos_y{year}"] = pl_op_cos

    return pl_bh_pow_op_cos_by_year


def get_pl_spec_fee_by_year(
    system_life: int,
    wacc: float,
    spectrum_fee: float
) -> dict:
    pl_spec_fee_by_year = {}

    # Calculate Year 3 payment using PMT formula
    pl_spec_fee_y3 = npf.pmt(rate=wacc, nper=system_life, pv=-spectrum_fee) / 1_000_000
    # logging.info(f"pl_spec_fee_y3: {pl_spec_fee_y3}")

    for year in range(1, 11):
        if (year - 3) > system_life:
            pl_spec_fee = 0
            # logging.info(f"Year {year}: Beyond system life, pl_spec_fee_y{year} = 0")
        else:
            pl_spec_fee = pl_spec_fee_y3
            # logging.info(f"Year {year}: pl_spec_fee_y{year} = {pl_spec_fee}")

        pl_spec_fee_by_year[f"pl_spec_fee_y{year}"] = pl_spec_fee

    return pl_spec_fee_by_year


def get_pl_maint_cos_by_year(
    system_life: int,
    cons_spd: float,
    maint_opex: float,
    inf: float
) -> dict:
    pl_maint_cos_by_year = {}
    # logging.info("Entering P&L Maintenance Cost By Year")
    # logging.info(f"System life is {system_life}, Construction spend {cons_spd}, Maintenance Opex {maint_opex}, "
                 # f"and inflation is {inf}")

    for year in range(1, 11):
        years_elapsed = year - 1

        if years_elapsed > system_life:
            pl_maint_cos = 0
            # logging.info(f"Year {year}: Beyond system life, pl_maint_cos_y{year} = 0")
        else:
            inflation_multiplier = math.pow(1 + inf, years_elapsed)
            pl_maint_cos = cons_spd * maint_opex * inflation_multiplier
            # logging.info(f"Year {year}: pl_maint_cos_y{year} = {pl_maint_cos}")

        pl_maint_cos_by_year[f"pl_maint_cos_y{year}"] = pl_maint_cos

    return pl_maint_cos_by_year


def get_pl_tot_op_cos_by_year(
    pl_lab_cos_by_year: dict,
    pl_oth_sys_op_cos_by_year: dict,
    pl_bh_pow_op_cos_by_year: dict,
    pl_spec_fee_by_year: dict,
    pl_maint_cos_by_year: dict
) -> dict:
    pl_tot_op_cos_by_year = {}

    for year in range(1, 11):
        pl_tot_op_cos = (
            pl_lab_cos_by_year.get(f"pl_lab_cos_y{year}", 0) +
            pl_oth_sys_op_cos_by_year.get(f"pl_oth_sys_op_cos_y{year}", 0) +
            pl_bh_pow_op_cos_by_year.get(f"pl_bh_pow_op_cos_y{year}", 0) +
            pl_spec_fee_by_year.get(f"pl_spec_fee_y{year}", 0) +
            pl_maint_cos_by_year.get(f"pl_maint_cos_y{year}", 0)
        )
        # logging.info(f"Year {year}: pl_tot_op_cos_y{year} = {pl_tot_op_cos}")
        pl_tot_op_cos_by_year[f"pl_tot_op_cos_y{year}"] = pl_tot_op_cos

    return pl_tot_op_cos_by_year


def get_pl_op_prof_by_year(
    pl_tot_rev_by_year: dict,
    pl_tot_op_cos_by_year: dict
) -> dict:
    pl_op_prof_by_year = {}
    # logging.info("Entering the Operational Profit by Year")
    # logging.info("Dumping the Client Revenue object")
    # logging.info(pl_tot_rev_by_year)

    for year in range(1, 11):
        tot_rev = pl_tot_rev_by_year.get(f"pl_tot_rev_y{year}", 0)
        tot_op_cos = pl_tot_op_cos_by_year.get(f"pl_tot_op_cos_y{year}", 0)
        op_prof = tot_rev - tot_op_cos

        # logging.info(f"Year {year}: pl_tot_rev = {tot_rev}, pl_tot_op_cos = {tot_op_cos}, pl_op_prof_y{year} = {op_prof}")

        pl_op_prof_by_year[f"pl_op_prof_y{year}"] = op_prof

    return pl_op_prof_by_year


def get_pl_dep_by_year(
    system_life: int,
    total_system_cost: float
) -> dict:
    pl_dep_by_year = {}
    annual_dep = total_system_cost / system_life

    for year in range(1, 11):
        if (year - 3) > system_life:
            dep = 0
            # logging.info(f"Year {year}: Beyond system life, pl_dep_y{year} = 0")
        else:
            dep = annual_dep
            # logging.info(f"Year {year}: pl_dep_y{year} = {dep}")

        pl_dep_by_year[f"pl_dep_y{year}"] = dep

    return pl_dep_by_year


def get_pl_ebit_by_year(
    pl_op_prof_by_year: dict,
    pl_dep_by_year: dict
) -> dict:
    pl_ebit_by_year = {}

    for year in range(1, 11):
        op_prof = pl_op_prof_by_year.get(f"pl_op_prof_y{year}", 0)
        dep = pl_dep_by_year.get(f"pl_dep_y{year}", 0)
        ebit = op_prof - dep

        # logging.info(f"Year {year}: op_prof = {op_prof}, dep = {dep}, pl_ebit_y{year} = {ebit}")

        pl_ebit_by_year[f"pl_ebit_y{year}"] = ebit

    return pl_ebit_by_year


def get_pl_int_by_year(
    system_life: int,
    cons_spd: float,
    debt_prop: float,
    fin_cos: float
) -> dict:
    pl_int_by_year = {}

    base_interest_payment = cons_spd * debt_prop * fin_cos
    # logging.info(f"Base annual interest payment (cons_spd × debt_prop × fin_cos): {base_interest_payment}")

    for year in range(1, 11):
        if (year - 3) > system_life:
            pl_int = 0
            # logging.info(f"Year {year}: Beyond system life, pl_int_y{year} = 0")
        else:
            pl_int = base_interest_payment
            # logging.info(f"Year {year}: pl_int_y{year} = {pl_int}")

        pl_int_by_year[f"pl_int_y{year}"] = pl_int

    return pl_int_by_year


def get_pl_ebt_by_year(
    pl_ebit_by_year: dict,
    pl_int_by_year: dict
) -> dict:
    pl_ebt_by_year = {}
    #logging.info("entering Calculate EBIT by year")

    for year in range(1, 11):
        ebit = pl_ebit_by_year.get(f"pl_ebit_y{year}", 0)
        interest = pl_int_by_year.get(f"pl_int_y{year}", 0)
        ebt = ebit - interest

        # logging.info(f"Year {year}: ebit = {ebit}, interest = {interest}, pl_ebt_y{year} = {ebt}")
        pl_ebt_by_year[f"pl_ebt_y{year}"] = ebt

    return pl_ebt_by_year


def get_pl_tax_by_year(
    pl_ebt_by_year: dict,
    tax_rate: float
) -> dict:
    pl_tax_by_year = {}
    # logging.info("entering profit & loss tax by year")
    for year in range(1, 11):
        ebt = pl_ebt_by_year.get(f"pl_ebt_y{year}", 0)
        tax = ebt * tax_rate
        # logging.info(f"Year {year}: ebt = {ebt}, tax_rate = {tax_rate}, pl_tax_y{year} = {tax}")
        pl_tax_by_year[f"pl_tax_y{year}"] = tax
    # logging.info("returning profit & loss tax by year")
    return pl_tax_by_year


def get_pl_prof_by_year(
    pl_ebt_by_year: dict,
    pl_tax_by_year: dict
) -> dict:
    pl_prof_by_year = {}
    # logging.info("entering profit & loss profit by year")
    for year in range(1, 11):
        ebt = pl_ebt_by_year.get(f"pl_ebt_y{year}", 0)
        tax = pl_tax_by_year.get(f"pl_tax_y{year}", 0)
        profit = ebt - tax

        # logging.info(f"Year {year}: ebt = {ebt}, tax = {tax}, pl_prof_y{year} = {profit}")
        pl_prof_by_year[f"pl_prof_y{year}"] = profit

    return pl_prof_by_year


def get_pl_sub_by_year(
    cons_spd: float,
    capsub: float,
    opsub: float,
    system_life: int,
    pl_tot_op_cos_by_year: dict
) -> dict:
    pl_sub_by_year = {}

    # Year 1: capital subsidy only
    pl_sub_by_year["pl_sub_y1"] = cons_spd * capsub
    # logging.info(f"Year 1: cons_spd * capsub = {cons_spd} * {capsub} = {pl_sub_by_year['pl_sub_y1']}")

    # Years 2–10: OpEx subsidy unless beyond system life
    for year in range(2, 11):
        years_elapsed = year - 1

        if years_elapsed > system_life:
            subsidy = 0
            # logging.info(f"Year {year}: Beyond system life, pl_sub_y{year} = 0")
        else:
            previous_year_op_cost = pl_tot_op_cos_by_year.get(f"pl_tot_op_cos_y{year - 1}", 0)
            subsidy = previous_year_op_cost * opsub
            # logging.info(f"Year {year}: pl_tot_op_cos_y{year - 1} = {previous_year_op_cost}, opsub = {opsub}, pl_sub_y{year} = {subsidy}")

        pl_sub_by_year[f"pl_sub_y{year}"] = subsidy

    return pl_sub_by_year


def get_pl_cli_rev_by_year(
        system_life, inf, pop_growth_rate, tu_rates, cli_rev_y3
):
    pl_cli_rev_by_year = {}

    for year in range(1, 11):
        if (year - 3) > system_life:
            cli_rev = 0
            # logging.info(f"Year {year}: system life exceeded, cli_rev_y{year} = 0")
        else:
            if year == 1:
                # cli_rev_y1 = cli_rev_y3 * ((1+inf) * (1+pop_growth_rate))^(-2) * tu_rates[1]
                growth_factor = math.pow((1 + inf) * (1 + pop_growth_rate), -2)
                tu_rate = tu_rates.get(year, 1)
                cli_rev = cli_rev_y3 * growth_factor * tu_rate
                # logging.info(f"Year {year}: growth_factor = {growth_factor}, tu_rate = {tu_rate}, cli_rev_y{year} = {cli_rev}")
            elif year == 2:
                # cli_rev_y2 = cli_rev_y3 * ((1+inf) * (1+pop_growth_rate))^(-1) * tu_rates[2]
                growth_factor = math.pow((1 + inf) * (1 + pop_growth_rate), -1)
                tu_rate = tu_rates.get(year, 1)
                cli_rev = cli_rev_y3 * growth_factor * tu_rate
                # logging.info(f"Year {year}: growth_factor = {growth_factor}, tu_rate = {tu_rate}, cli_rev_y{year} = {cli_rev}")
            elif year == 3:
                # cli_rev_y3 = cli_rev_y3
                cli_rev = cli_rev_y3
                # logging.info(f"Year {year}: cli_rev_y{year} = {cli_rev}")
            else:
                # cli_rev_y(n) = cli_rev_y3 * ((1+inf) * (1+pop_growth_rate))^(n-3)
                growth_factor = math.pow((1 + inf) * (1 + pop_growth_rate), year - 3)
                tu_rate = tu_rates.get(year, 1)
                cli_rev = cli_rev_y3 * growth_factor * tu_rate
                # logging.info(f"Year {year}: growth_factor = {growth_factor}, tu_rate = {tu_rate}, cli_rev_y{year} = {cli_rev}")

        pl_cli_rev_by_year[f"cli_rev_y{year}"] = cli_rev

    return pl_cli_rev_by_year


def get_pl_tot_rev_by_year(
    pl_cli_rev_by_year: dict,
    pl_sub_by_year: dict
) -> dict:
    pl_tot_rev_by_year = {}

    for year in range(1, 11):
        cli_rev = pl_cli_rev_by_year.get(f"cli_rev_y{year}", 0)
        sub = pl_sub_by_year.get(f"pl_sub_y{year}", 0)
        total_rev = cli_rev + sub

        # logging.info(f"Year {year}: cli_rev = {cli_rev}, sub = {sub}, pl_tot_rev_y{year} = {total_rev}")

        pl_tot_rev_by_year[f"pl_tot_rev_y{year}"] = total_rev

    return pl_tot_rev_by_year


def get_cf_cash_in_by_year(
    pl_cli_rev_by_year: dict,
    pl_sub_by_year: dict
) -> dict:
    cf_cash_in_by_year = {}

    for year in range(1, 11):
        cli_rev = pl_cli_rev_by_year.get(f"cli_rev_y{year}", 0)
        sub = pl_sub_by_year.get(f"pl_sub_y{year}", 0)
        cash_in = cli_rev + sub

        # logging.info(f"Year {year}: cli_rev = {cli_rev}, sub = {sub}, cf_cash_in_y{year} = {cash_in}")

        cf_cash_in_by_year[f"cf_cash_in_y{year}"] = cash_in

    return cf_cash_in_by_year


def get_cf_cash_out_by_year(
    pl_lab_cos_by_year: dict,
    pl_oth_sys_op_cos_by_year: dict,
    pl_bh_pow_op_cos_by_year: dict,
    pl_spec_fee_by_year: dict,
    pl_maint_cos_by_year: dict,
    pl_tax_by_year: dict
) -> dict:
    cf_cash_out_by_year = {}

    for year in range(1, 11):
        cash_out = (
            pl_lab_cos_by_year.get(f"pl_lab_cos_y{year}", 0) +
            pl_oth_sys_op_cos_by_year.get(f"pl_oth_sys_op_cos_y{year}", 0) +
            pl_bh_pow_op_cos_by_year.get(f"pl_bh_pow_op_cos_y{year}", 0) +
            pl_spec_fee_by_year.get(f"pl_spec_fee_y{year}", 0) +
            pl_maint_cos_by_year.get(f"pl_maint_cos_y{year}", 0) +
            pl_tax_by_year.get(f"pl_tax_y{year}", 0)
        )
        # logging.info(f"Year {year}: cf_cash_out_y{year} = {cash_out}")
        cf_cash_out_by_year[f"cf_cash_out_y{year}"] = cash_out

    return cf_cash_out_by_year


def get_cf_net_by_year(
    cf_cash_in_by_year: dict,
    cf_cash_out_by_year: dict
) -> dict:
    cf_net_by_year = {}

    for year in range(1, 11):
        cash_in = cf_cash_in_by_year.get(f"cf_cash_in_y{year}", 0)
        cash_out = cf_cash_out_by_year.get(f"cf_cash_out_y{year}", 0)
        net = cash_in - cash_out

        # logging.info(f"Year {year}: cash_in = {cash_in}, cash_out = {cash_out}, cf_net_y{year} = {net}")
        cf_net_by_year[f"cf_net_y{year}"] = net

    return cf_net_by_year


def get_cf_cum_by_year(
    cf_net_by_year: dict,
    cons_spd: float
) -> dict:
    cf_cum_by_year = {}
    cf_net_y0 = -1 * cons_spd
    # logging.info(f"cf_net_out_y0 = {cf_net_y0}")

    for year in range(1, 11):
        if year == 1:
            cum = cf_net_by_year.get("cf_net_y1", 0) + cf_net_y0
        else:
            prev_cum = cf_cum_by_year.get(f"cf_cum_y{year - 1}", 0)
            curr = cf_net_by_year.get(f"cf_net_y{year}", 0)
            cum = prev_cum + curr

        cf_cum_by_year[f"cf_cum_y{year}"] = cum
        # logging.info(f"cf_cum_y{year} = {cum}")

    return cf_cum_by_year


def build_inv_row(label: str, base_key: str, data_dict: dict, year0_value="") -> dict:
    return {
        "label": label,
        "y0": year0_value,
        **{f"y{year}": float(data_dict.get(f"{base_key}_y{year}", 0.0)) for year in range(1, 11)},
    }
