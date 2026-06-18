from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from src.config import CSV_DIR, RAW_DATA_DIR, WORKBOOK_PATH


BASELINE_DATE = "2026-04-30"
DATE_RANGE = pd.date_range("2023-01-31", BASELINE_DATE, freq="ME")
DATA_SOURCE = "synthetic_v1_dataset_generator"

PRIVATE_ASSET_CLASSES = {
    "Private Equity",
    "Venture Capital / Growth",
    "Private Credit",
    "Real Estate",
    "Infrastructure",
}

PRESERVED_TABLES = [
    "capital_calls",
    "capital_statements",
    "distributions",
    "document_metadata",
    "document_update_map",
    "expected_position_updates",
    "fund_aliases",
    "ground_truth_extractions",
    "newsletter_updates",
    "review_queue",
    "validation_results",
    "validation_rules",
]

GEOGRAPHY_OVERRIDES = {
    "PF_DRAGONBRIDGE": "Greater China",
    "PF_SEEDSPRING_I": "Southeast Asia",
    "PF_INDIA_DIGITAL": "India",
    "PF_LIONROCK_CREDIT": "Southeast Asia",
    "PF_APAC_LOGISTICS": "Japan",
    "PF_METRO_LOGISTICS": "Southeast Asia",
}

MANDATE_SECTOR_OVERRIDES = {
    "PF_NORTHSTAR_IV": "Industrials",
    "PF_HARBOR_PEAK_V": "Diversified / Secondaries",
    "PF_ATLAS_COINV_I": "Business Services",
    "PF_APEX_SECONDARIES_II": "Diversified / Secondaries",
    "PF_DRAGONBRIDGE": "Consumer / Industrials",
    "PF_BLUE_HORIZON_III": "Information Technology",
    "PF_GLOBAL_GROWTH_II": "Information Technology / Consumer",
    "PF_SEEDSPRING_I": "Information Technology / Consumer",
    "PF_INDIA_DIGITAL": "Information Technology",
    "PF_CLIMATE_ALPHA": "Climate / Industrials",
    "PF_CRESCENT_DIRECT_LEND": "Diversified Credit",
    "PF_SPRING_OPP_CREDIT": "Special Situations Credit",
    "PF_COVE_SPECIALTY_FIN": "Financials",
    "PF_LIONROCK_CREDIT": "Diversified Credit",
    "PF_HARBOUR_CORE_RE": "Real Estate",
    "PF_METRO_LOGISTICS": "Industrial Real Estate",
    "PF_HOME_MULTIFAMILY": "Residential Real Estate",
    "PF_APAC_LOGISTICS": "Industrial Real Estate",
    "PF_INFRA_CORE": "Infrastructure",
    "PF_RENEWABLES_II": "Utilities / Infrastructure",
}

PRIVATE_PROXY_MAP = {
    "Private Equity": "ACWI",
    "Venture Capital / Growth": "QQQ",
    "Private Credit": "HYG",
    "Real Estate": "VNQ",
    "Infrastructure": "IFRA",
}

PRIVATE_REPORTING_PROFILES = {
    "PF_NORTHSTAR_IV": {
        "reporting_cadence": "Quarterly",
        "last_statement_date": "2026-03-31",
        "valuation_status": "Quarterly manager statement received for Q1 2026.",
    },
    "PF_HARBOR_PEAK_V": {
        "reporting_cadence": "Quarterly",
        "last_statement_date": "2026-03-31",
        "valuation_status": "Quarterly manager statement received for Q1 2026.",
    },
    "PF_ATLAS_COINV_I": {
        "reporting_cadence": "Quarterly",
        "last_statement_date": "2026-03-31",
        "valuation_status": "Quarterly co-investment marks carried from Q1 2026 close.",
    },
    "PF_APEX_SECONDARIES_II": {
        "reporting_cadence": "Quarterly",
        "last_statement_date": "2026-03-31",
        "valuation_status": "Quarterly secondaries report received for Q1 2026.",
    },
    "PF_DRAGONBRIDGE": {
        "reporting_cadence": "Quarterly",
        "last_statement_date": "2026-02-28",
        "valuation_status": "Quarterly GP package pending; February 2026 internal mark held.",
    },
    "PF_BLUE_HORIZON_III": {
        "reporting_cadence": "Quarterly",
        "last_statement_date": "2026-03-31",
        "valuation_status": "Quarterly venture marks received for Q1 2026.",
    },
    "PF_GLOBAL_GROWTH_II": {
        "reporting_cadence": "Quarterly",
        "last_statement_date": "2026-03-31",
        "valuation_status": "Quarterly growth equity statement received for Q1 2026.",
    },
    "PF_SEEDSPRING_I": {
        "reporting_cadence": "Quarterly",
        "last_statement_date": "2026-02-28",
        "valuation_status": "Quarterly Southeast Asia VC report pending; February 2026 estimate retained.",
    },
    "PF_INDIA_DIGITAL": {
        "reporting_cadence": "Quarterly",
        "last_statement_date": "2026-02-28",
        "valuation_status": "Quarterly India growth report pending; February 2026 estimate retained.",
    },
    "PF_CLIMATE_ALPHA": {
        "reporting_cadence": "Quarterly",
        "last_statement_date": "2026-03-15",
        "valuation_status": "Quarterly climate fund package partially received; mid-March estimate applied.",
    },
    "PF_CRESCENT_DIRECT_LEND": {
        "reporting_cadence": "Monthly",
        "last_statement_date": "2026-04-15",
        "valuation_status": "Monthly lender report received through April 15, 2026.",
    },
    "PF_SPRING_OPP_CREDIT": {
        "reporting_cadence": "Monthly",
        "last_statement_date": "2026-04-10",
        "valuation_status": "Monthly credit marks received through April 10, 2026.",
    },
    "PF_COVE_SPECIALTY_FIN": {
        "reporting_cadence": "Monthly",
        "last_statement_date": "2026-04-20",
        "valuation_status": "Monthly specialty finance statement received through April 20, 2026.",
    },
    "PF_LIONROCK_CREDIT": {
        "reporting_cadence": "Monthly",
        "last_statement_date": "2026-04-12",
        "valuation_status": "Monthly Asia private credit statement received through April 12, 2026.",
    },
    "PF_HARBOUR_CORE_RE": {
        "reporting_cadence": "Monthly",
        "last_statement_date": "2026-03-31",
        "valuation_status": "Monthly real estate operating report received through March 31, 2026.",
    },
    "PF_METRO_LOGISTICS": {
        "reporting_cadence": "Monthly",
        "last_statement_date": "2026-03-31",
        "valuation_status": "Monthly logistics property report received through March 31, 2026.",
    },
    "PF_HOME_MULTIFAMILY": {
        "reporting_cadence": "Monthly",
        "last_statement_date": "2026-03-31",
        "valuation_status": "Monthly multifamily operating report received through March 31, 2026.",
    },
    "PF_APAC_LOGISTICS": {
        "reporting_cadence": "Monthly",
        "last_statement_date": "2026-03-15",
        "valuation_status": "Monthly APAC logistics report received through March 15, 2026.",
    },
    "PF_INFRA_CORE": {
        "reporting_cadence": "Quarterly",
        "last_statement_date": "2026-03-31",
        "valuation_status": "Quarterly infrastructure valuation received for Q1 2026.",
    },
    "PF_RENEWABLES_II": {
        "reporting_cadence": "Monthly",
        "last_statement_date": "2026-03-31",
        "valuation_status": "Monthly renewables operating report received through March 31, 2026.",
    },
    "PF_DIGITAL_INFRA": {
        "reporting_cadence": "Quarterly",
        "last_statement_date": "2026-03-31",
        "valuation_status": "Quarterly digital infrastructure statement received for Q1 2026.",
    },
}

PUBLIC_HOLDINGS = [
    {
        "holding_id": "H_SPY",
        "holding_name": "SPDR S&P 500 ETF",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "US Large Cap Core",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "SPY",
        "final_value_usd_m": 40.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 40.0,
        "current_gross_notional_usd_m": 40.0,
        "current_delta_adjusted_exposure_usd_m": 40.0,
        "gics_sector": "Multi-Sector / Diversified",
        "gics_industry_group": "Broad Market ETF",
        "market_cap_bucket": "Multi Cap",
        "lookthrough_method": "lookthrough",
        "classification_status": "lookthrough",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Broad US equity beta.",
    },
    {
        "holding_id": "H_QQQ",
        "holding_name": "Invesco QQQ Trust",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "US Technology / Growth",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "QQQ",
        "final_value_usd_m": 24.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 24.0,
        "current_gross_notional_usd_m": 24.0,
        "current_delta_adjusted_exposure_usd_m": 24.0,
        "gics_sector": "Information Technology",
        "gics_industry_group": "Growth / Technology ETF",
        "market_cap_bucket": "Mega Cap",
        "lookthrough_method": "lookthrough",
        "classification_status": "lookthrough",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Technology-heavy growth proxy.",
    },
    {
        "holding_id": "H_ACWI",
        "holding_name": "iShares MSCI ACWI ETF",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "Global Equity Core",
        "region_taxonomy": "Global / Multi-region",
        "country": "Global",
        "currency": "USD",
        "ticker": "ACWI",
        "final_value_usd_m": 20.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 20.0,
        "current_gross_notional_usd_m": 20.0,
        "current_delta_adjusted_exposure_usd_m": 20.0,
        "gics_sector": "Multi-Sector / Diversified",
        "gics_industry_group": "Broad Market ETF",
        "market_cap_bucket": "Multi Cap",
        "lookthrough_method": "lookthrough",
        "classification_status": "lookthrough",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Global developed and emerging exposure.",
    },
    {
        "holding_id": "H_BRKB",
        "holding_name": "Berkshire Hathaway Class B",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "US Quality Compounder",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "BRK.B",
        "final_value_usd_m": 12.0,
        "instrument_type": "equity",
        "position_side_current": "long",
        "current_exposure_usd_m": 12.0,
        "current_gross_notional_usd_m": 12.0,
        "current_delta_adjusted_exposure_usd_m": 12.0,
        "gics_sector": "Financials",
        "gics_industry_group": "Multi-Sector Holdings",
        "market_cap_bucket": "Mega Cap",
        "lookthrough_method": "direct",
        "classification_status": "direct",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Single-name equity.",
    },
    {
        "holding_id": "H_MSFT",
        "holding_name": "Microsoft",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "US Mega-cap Technology",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "MSFT",
        "final_value_usd_m": 10.0,
        "instrument_type": "equity",
        "position_side_current": "long",
        "current_exposure_usd_m": 10.0,
        "current_gross_notional_usd_m": 10.0,
        "current_delta_adjusted_exposure_usd_m": 10.0,
        "gics_sector": "Information Technology",
        "gics_industry_group": "Software",
        "market_cap_bucket": "Mega Cap",
        "lookthrough_method": "direct",
        "classification_status": "direct",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Single-name equity.",
    },
    {
        "holding_id": "H_GOOGL",
        "holding_name": "Alphabet Class A",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "US Mega-cap Technology",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "GOOGL",
        "final_value_usd_m": 9.0,
        "instrument_type": "equity",
        "position_side_current": "long",
        "current_exposure_usd_m": 9.0,
        "current_gross_notional_usd_m": 9.0,
        "current_delta_adjusted_exposure_usd_m": 9.0,
        "gics_sector": "Communication Services",
        "gics_industry_group": "Interactive Media",
        "market_cap_bucket": "Mega Cap",
        "lookthrough_method": "direct",
        "classification_status": "direct",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Single-name equity.",
    },
    {
        "holding_id": "H_NVDA",
        "holding_name": "NVIDIA",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "US Semiconductor Growth",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "NVDA",
        "final_value_usd_m": 8.0,
        "instrument_type": "equity",
        "position_side_current": "long",
        "current_exposure_usd_m": 8.0,
        "current_gross_notional_usd_m": 8.0,
        "current_delta_adjusted_exposure_usd_m": 8.0,
        "gics_sector": "Information Technology",
        "gics_industry_group": "Semiconductors",
        "market_cap_bucket": "Mega Cap",
        "lookthrough_method": "direct",
        "classification_status": "direct",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Single-name equity.",
    },
    {
        "holding_id": "H_2800HK",
        "holding_name": "Tracker Fund of Hong Kong ETF",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "Hong Kong Broad Market",
        "region_taxonomy": "Greater China",
        "country": "Hong Kong",
        "currency": "HKD",
        "ticker": "2800.HK",
        "final_value_usd_m": 12.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 12.0,
        "current_gross_notional_usd_m": 12.0,
        "current_delta_adjusted_exposure_usd_m": 12.0,
        "gics_sector": "Multi-Sector / Diversified",
        "gics_industry_group": "Hong Kong Equity ETF",
        "market_cap_bucket": "Large Cap",
        "lookthrough_method": "lookthrough",
        "classification_status": "lookthrough",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Greater China public equity exposure.",
    },
    {
        "holding_id": "H_HSTECH",
        "holding_name": "Hang Seng TECH ETF-style Exposure",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "Hong Kong / China Technology",
        "region_taxonomy": "Greater China",
        "country": "Hong Kong",
        "currency": "HKD",
        "ticker": "3067.HK",
        "final_value_usd_m": 10.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 10.0,
        "current_gross_notional_usd_m": 10.0,
        "current_delta_adjusted_exposure_usd_m": 10.0,
        "gics_sector": "Information Technology",
        "gics_industry_group": "Technology ETF",
        "market_cap_bucket": "Large Cap",
        "lookthrough_method": "lookthrough",
        "classification_status": "lookthrough",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Greater China technology beta.",
    },
    {
        "holding_id": "H_BABA",
        "holding_name": "Alibaba ADR",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "China Internet ADR",
        "region_taxonomy": "Greater China",
        "country": "China",
        "currency": "USD",
        "ticker": "BABA",
        "final_value_usd_m": 7.0,
        "instrument_type": "equity",
        "position_side_current": "long",
        "current_exposure_usd_m": 7.0,
        "current_gross_notional_usd_m": 7.0,
        "current_delta_adjusted_exposure_usd_m": 7.0,
        "gics_sector": "Consumer Discretionary",
        "gics_industry_group": "Broadline Retail",
        "market_cap_bucket": "Large Cap",
        "lookthrough_method": "direct",
        "classification_status": "direct",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Single-name equity.",
    },
    {
        "holding_id": "H_PDD",
        "holding_name": "PDD Holdings ADR",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "China Internet ADR",
        "region_taxonomy": "Greater China",
        "country": "China",
        "currency": "USD",
        "ticker": "PDD",
        "final_value_usd_m": 6.0,
        "instrument_type": "equity",
        "position_side_current": "long",
        "current_exposure_usd_m": 6.0,
        "current_gross_notional_usd_m": 6.0,
        "current_delta_adjusted_exposure_usd_m": 6.0,
        "gics_sector": "Consumer Discretionary",
        "gics_industry_group": "Broadline Retail",
        "market_cap_bucket": "Large Cap",
        "lookthrough_method": "direct",
        "classification_status": "direct",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Single-name equity.",
    },
    {
        "holding_id": "H_JD",
        "holding_name": "JD.com ADR",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "China E-commerce ADR",
        "region_taxonomy": "Greater China",
        "country": "China",
        "currency": "USD",
        "ticker": "JD",
        "final_value_usd_m": 5.0,
        "instrument_type": "equity",
        "position_side_current": "long",
        "current_exposure_usd_m": 5.0,
        "current_gross_notional_usd_m": 5.0,
        "current_delta_adjusted_exposure_usd_m": 5.0,
        "gics_sector": "Consumer Discretionary",
        "gics_industry_group": "Broadline Retail",
        "market_cap_bucket": "Large Cap",
        "lookthrough_method": "direct",
        "classification_status": "direct",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Single-name equity.",
    },
    {
        "holding_id": "H_CNYA",
        "holding_name": "iShares MSCI China A ETF",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "China A-Shares",
        "region_taxonomy": "Greater China",
        "country": "China",
        "currency": "USD",
        "ticker": "CNYA",
        "final_value_usd_m": 8.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 8.0,
        "current_gross_notional_usd_m": 8.0,
        "current_delta_adjusted_exposure_usd_m": 8.0,
        "gics_sector": "Multi-Sector / Diversified",
        "gics_industry_group": "China A-Shares ETF",
        "market_cap_bucket": "All Cap",
        "lookthrough_method": "lookthrough",
        "classification_status": "lookthrough",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "A-shares allocation.",
    },
    {
        "holding_id": "H_EWJ",
        "holding_name": "iShares MSCI Japan ETF",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "Japan Equities",
        "region_taxonomy": "Japan",
        "country": "Japan",
        "currency": "USD",
        "ticker": "EWJ",
        "final_value_usd_m": 7.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 7.0,
        "current_gross_notional_usd_m": 7.0,
        "current_delta_adjusted_exposure_usd_m": 7.0,
        "gics_sector": "Multi-Sector / Diversified",
        "gics_industry_group": "Japan Equity ETF",
        "market_cap_bucket": "Large Cap",
        "lookthrough_method": "lookthrough",
        "classification_status": "lookthrough",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Japan allocation.",
    },
    {
        "holding_id": "H_INDA",
        "holding_name": "iShares MSCI India ETF",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "India Equities",
        "region_taxonomy": "India",
        "country": "India",
        "currency": "USD",
        "ticker": "INDA",
        "final_value_usd_m": 7.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 7.0,
        "current_gross_notional_usd_m": 7.0,
        "current_delta_adjusted_exposure_usd_m": 7.0,
        "gics_sector": "Multi-Sector / Diversified",
        "gics_industry_group": "India Equity ETF",
        "market_cap_bucket": "All Cap",
        "lookthrough_method": "lookthrough",
        "classification_status": "lookthrough",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "India allocation.",
    },
    {
        "holding_id": "H_EWY",
        "holding_name": "iShares MSCI South Korea ETF",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "Korea Equities",
        "region_taxonomy": "Korea",
        "country": "South Korea",
        "currency": "USD",
        "ticker": "EWY",
        "final_value_usd_m": 5.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 5.0,
        "current_gross_notional_usd_m": 5.0,
        "current_delta_adjusted_exposure_usd_m": 5.0,
        "gics_sector": "Multi-Sector / Diversified",
        "gics_industry_group": "Korea Equity ETF",
        "market_cap_bucket": "Large Cap",
        "lookthrough_method": "lookthrough",
        "classification_status": "lookthrough",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Korea allocation.",
    },
    {
        "holding_id": "H_EWS",
        "holding_name": "iShares MSCI Singapore ETF",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "Southeast Asia Equities",
        "region_taxonomy": "Southeast Asia",
        "country": "Singapore",
        "currency": "USD",
        "ticker": "EWS",
        "final_value_usd_m": 3.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 3.0,
        "current_gross_notional_usd_m": 3.0,
        "current_delta_adjusted_exposure_usd_m": 3.0,
        "gics_sector": "Multi-Sector / Diversified",
        "gics_industry_group": "Southeast Asia Equity ETF",
        "market_cap_bucket": "Large Cap",
        "lookthrough_method": "lookthrough",
        "classification_status": "lookthrough",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Southeast Asia allocation.",
    },
    {
        "holding_id": "H_EEM",
        "holding_name": "iShares MSCI Emerging Markets ETF",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "Emerging Markets Core",
        "region_taxonomy": "Global / Multi-region",
        "country": "Global",
        "currency": "USD",
        "ticker": "EEM",
        "final_value_usd_m": 7.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 7.0,
        "current_gross_notional_usd_m": 7.0,
        "current_delta_adjusted_exposure_usd_m": 7.0,
        "gics_sector": "Multi-Sector / Diversified",
        "gics_industry_group": "EM Equity ETF",
        "market_cap_bucket": "All Cap",
        "lookthrough_method": "lookthrough",
        "classification_status": "lookthrough",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Broad EM exposure.",
    },
    {
        "holding_id": "H_AGG",
        "holding_name": "iShares Core US Aggregate Bond ETF",
        "asset_class": "Fixed Income & Liquid Credit",
        "sub_asset_class": "US Aggregate Bonds",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "AGG",
        "final_value_usd_m": 24.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 24.0,
        "current_gross_notional_usd_m": 24.0,
        "current_delta_adjusted_exposure_usd_m": 24.0,
        "gics_sector": "Fixed Income / Credit",
        "gics_industry_group": "Aggregate Bonds",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "benchmark_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Bond beta.",
    },
    {
        "holding_id": "H_TLT",
        "holding_name": "iShares 20+ Year Treasury Bond ETF",
        "asset_class": "Fixed Income & Liquid Credit",
        "sub_asset_class": "Long Duration Treasuries",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "TLT",
        "final_value_usd_m": 14.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 14.0,
        "current_gross_notional_usd_m": 14.0,
        "current_delta_adjusted_exposure_usd_m": 14.0,
        "gics_sector": "Fixed Income / Sovereign",
        "gics_industry_group": "Government Bonds",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "benchmark_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Rates exposure.",
    },
    {
        "holding_id": "H_IGIB",
        "holding_name": "iShares 5-10 Year Investment Grade Corporate Bond ETF",
        "asset_class": "Fixed Income & Liquid Credit",
        "sub_asset_class": "Investment Grade Credit",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "IGIB",
        "final_value_usd_m": 12.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 12.0,
        "current_gross_notional_usd_m": 12.0,
        "current_delta_adjusted_exposure_usd_m": 12.0,
        "gics_sector": "Fixed Income / Credit",
        "gics_industry_group": "Investment Grade Credit",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "benchmark_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Credit exposure.",
    },
    {
        "holding_id": "H_HYG",
        "holding_name": "iShares High Yield Corporate Bond ETF",
        "asset_class": "Fixed Income & Liquid Credit",
        "sub_asset_class": "High Yield Credit",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "HYG",
        "final_value_usd_m": 9.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 9.0,
        "current_gross_notional_usd_m": 9.0,
        "current_delta_adjusted_exposure_usd_m": 9.0,
        "gics_sector": "Fixed Income / Credit",
        "gics_industry_group": "High Yield Credit",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "benchmark_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "High-yield exposure.",
    },
    {
        "holding_id": "H_EMB",
        "holding_name": "iShares Emerging Markets Bond ETF",
        "asset_class": "Fixed Income & Liquid Credit",
        "sub_asset_class": "EM Sovereign / Credit",
        "region_taxonomy": "Global / Multi-region",
        "country": "Global",
        "currency": "USD",
        "ticker": "EMB",
        "final_value_usd_m": 8.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 8.0,
        "current_gross_notional_usd_m": 8.0,
        "current_delta_adjusted_exposure_usd_m": 8.0,
        "gics_sector": "Fixed Income / Credit",
        "gics_industry_group": "EM Debt",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "benchmark_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Emerging market debt exposure.",
    },
    {
        "holding_id": "H_LQD",
        "holding_name": "iShares Investment Grade Corporate Bond ETF",
        "asset_class": "Fixed Income & Liquid Credit",
        "sub_asset_class": "Investment Grade Credit",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "LQD",
        "final_value_usd_m": 8.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 8.0,
        "current_gross_notional_usd_m": 8.0,
        "current_delta_adjusted_exposure_usd_m": 8.0,
        "gics_sector": "Fixed Income / Credit",
        "gics_industry_group": "Investment Grade Credit",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "benchmark_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Additional credit exposure.",
    },
    {
        "holding_id": "H_GLD",
        "holding_name": "SPDR Gold Shares",
        "asset_class": "Hedge Funds / Absolute Return",
        "sub_asset_class": "Gold / Defensive",
        "region_taxonomy": "Global / Multi-region",
        "country": "Global",
        "currency": "USD",
        "ticker": "GLD",
        "final_value_usd_m": 10.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 10.0,
        "current_gross_notional_usd_m": 10.0,
        "current_delta_adjusted_exposure_usd_m": 10.0,
        "gics_sector": "Commodities / Precious Metals",
        "gics_industry_group": "Gold",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "benchmark_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Defensive gold allocation.",
    },
    {
        "holding_id": "H_BIL",
        "holding_name": "SPDR 1-3 Month T-Bill ETF",
        "asset_class": "Fixed Income & Liquid Credit",
        "sub_asset_class": "Treasury Bills",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "BIL",
        "final_value_usd_m": 8.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 8.0,
        "current_gross_notional_usd_m": 8.0,
        "current_delta_adjusted_exposure_usd_m": 8.0,
        "gics_sector": "Fixed Income / Sovereign",
        "gics_industry_group": "Treasury Bills",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "benchmark_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "T-bill sleeve and risk-free proxy anchor.",
    },
    {
        "holding_id": "H_DBMF",
        "holding_name": "Managed Futures ETF Proxy",
        "asset_class": "Hedge Funds / Absolute Return",
        "sub_asset_class": "Managed Futures",
        "region_taxonomy": "Global / Multi-region",
        "country": "Global",
        "currency": "USD",
        "ticker": "DBMF",
        "final_value_usd_m": 10.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 10.0,
        "current_gross_notional_usd_m": 10.0,
        "current_delta_adjusted_exposure_usd_m": 10.0,
        "gics_sector": "Multi-Strategy",
        "gics_industry_group": "Managed Futures",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "benchmark_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Liquid alternatives sleeve.",
    },
    {
        "holding_id": "H_QAI",
        "holding_name": "Multi-Strategy Liquid Alternatives ETF Proxy",
        "asset_class": "Hedge Funds / Absolute Return",
        "sub_asset_class": "Multi-Strategy Absolute Return",
        "region_taxonomy": "Global / Multi-region",
        "country": "Global",
        "currency": "USD",
        "ticker": "QAI",
        "final_value_usd_m": 7.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 7.0,
        "current_gross_notional_usd_m": 7.0,
        "current_delta_adjusted_exposure_usd_m": 7.0,
        "gics_sector": "Multi-Strategy",
        "gics_industry_group": "Absolute Return",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "benchmark_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Liquid alternatives sleeve.",
    },
    {
        "holding_id": "H_ES_SHORT",
        "holding_name": "S&P 500 Overlay Short Future",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "Equity Index Overlay",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "ES1",
        "final_value_usd_m": 3.0,
        "instrument_type": "future",
        "position_side_current": "short",
        "current_exposure_usd_m": -18.0,
        "current_gross_notional_usd_m": 18.0,
        "current_delta_adjusted_exposure_usd_m": -18.0,
        "gics_sector": "Multi-Sector / Diversified",
        "gics_industry_group": "Equity Index Future",
        "market_cap_bucket": "Multi Cap",
        "lookthrough_method": "underlying_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Signed notional retained for short overlay.",
    },
    {
        "holding_id": "H_NQ_SHORT",
        "holding_name": "Nasdaq Overlay Short Future",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "Technology Overlay",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "NQ1",
        "final_value_usd_m": 2.0,
        "instrument_type": "future",
        "position_side_current": "short",
        "current_exposure_usd_m": -12.0,
        "current_gross_notional_usd_m": 12.0,
        "current_delta_adjusted_exposure_usd_m": -12.0,
        "gics_sector": "Information Technology",
        "gics_industry_group": "Equity Index Future",
        "market_cap_bucket": "Mega Cap",
        "lookthrough_method": "underlying_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Short technology beta hedge.",
    },
    {
        "holding_id": "H_SPY_PUT",
        "holding_name": "S&P 500 Protective Put Overlay",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "Options Overlay",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "SPY_PUT",
        "final_value_usd_m": 2.0,
        "instrument_type": "listed_option",
        "position_side_current": "long",
        "current_exposure_usd_m": -8.0,
        "current_gross_notional_usd_m": 12.0,
        "current_delta_adjusted_exposure_usd_m": -8.0,
        "gics_sector": "Multi-Sector / Diversified",
        "gics_industry_group": "Equity Index Option",
        "market_cap_bucket": "Multi Cap",
        "lookthrough_method": "underlying_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Delta-adjusted option hedge.",
    },
    {
        "holding_id": "H_HSI_FUT",
        "holding_name": "Hang Seng Index Tactical Long Future",
        "asset_class": "Global Public Equities",
        "sub_asset_class": "Greater China Tactical Overlay",
        "region_taxonomy": "Greater China",
        "country": "Hong Kong",
        "currency": "HKD",
        "ticker": "HSI1",
        "final_value_usd_m": 2.5,
        "instrument_type": "future",
        "position_side_current": "long",
        "current_exposure_usd_m": 9.0,
        "current_gross_notional_usd_m": 9.0,
        "current_delta_adjusted_exposure_usd_m": 9.0,
        "gics_sector": "Multi-Sector / Diversified",
        "gics_industry_group": "Equity Index Future",
        "market_cap_bucket": "Large Cap",
        "lookthrough_method": "underlying_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Directional Greater China tactical future.",
    },
    {
        "holding_id": "H_GMACRO",
        "holding_name": "Global Macro Hedge Fund Sleeve",
        "asset_class": "Hedge Funds / Absolute Return",
        "sub_asset_class": "Global Macro",
        "region_taxonomy": "Global / Multi-region",
        "country": "Global",
        "currency": "USD",
        "ticker": "GMACRO",
        "final_value_usd_m": 18.0,
        "instrument_type": "fund",
        "position_side_current": "long",
        "current_exposure_usd_m": 18.0,
        "current_gross_notional_usd_m": 18.0,
        "current_delta_adjusted_exposure_usd_m": 18.0,
        "gics_sector": "Multi-Strategy",
        "gics_industry_group": "Global Macro",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "mandate_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "proxy",
        "liquidity_bucket": "Semi-Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Monthly-dealing macro sleeve.",
    },
    {
        "holding_id": "H_MKTNEUT",
        "holding_name": "Equity Market Neutral Fund Sleeve",
        "asset_class": "Hedge Funds / Absolute Return",
        "sub_asset_class": "Equity Market Neutral",
        "region_taxonomy": "Global / Multi-region",
        "country": "Global",
        "currency": "USD",
        "ticker": "MKTNEUT",
        "final_value_usd_m": 16.0,
        "instrument_type": "fund",
        "position_side_current": "long",
        "current_exposure_usd_m": 16.0,
        "current_gross_notional_usd_m": 16.0,
        "current_delta_adjusted_exposure_usd_m": 16.0,
        "gics_sector": "Multi-Strategy",
        "gics_industry_group": "Equity Market Neutral",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "mandate_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "proxy",
        "liquidity_bucket": "Semi-Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Absolute return sleeve.",
    },
    {
        "holding_id": "H_DBC",
        "holding_name": "Broad Commodities ETF Proxy",
        "asset_class": "Hedge Funds / Absolute Return",
        "sub_asset_class": "Commodities",
        "region_taxonomy": "Global / Multi-region",
        "country": "Global",
        "currency": "USD",
        "ticker": "DBC",
        "final_value_usd_m": 8.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 8.0,
        "current_gross_notional_usd_m": 8.0,
        "current_delta_adjusted_exposure_usd_m": 8.0,
        "gics_sector": "Commodities",
        "gics_industry_group": "Broad Commodities",
        "market_cap_bucket": "Non-classifiable",
        "lookthrough_method": "benchmark_proxy",
        "classification_status": "proxy",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Commodity diversifier.",
    },
    {
        "holding_id": "H_VNQ",
        "holding_name": "US Listed REIT ETF Proxy",
        "asset_class": "Hedge Funds / Absolute Return",
        "sub_asset_class": "Listed Real Estate",
        "region_taxonomy": "North America",
        "country": "United States",
        "currency": "USD",
        "ticker": "VNQ",
        "final_value_usd_m": 6.0,
        "instrument_type": "etf",
        "position_side_current": "long",
        "current_exposure_usd_m": 6.0,
        "current_gross_notional_usd_m": 6.0,
        "current_delta_adjusted_exposure_usd_m": 6.0,
        "gics_sector": "Real Estate",
        "gics_industry_group": "REITs",
        "market_cap_bucket": "Mid Cap",
        "lookthrough_method": "lookthrough",
        "classification_status": "lookthrough",
        "proxy_mapping_status": "direct",
        "liquidity_bucket": "Liquid",
        "data_source": "synthetic_public_market_seed",
        "notes": "Listed real estate proxy.",
    },
]

SHEET_NAME_MAP = {
    "position_exposure_history": "position_exposure_hist",
    "public_instrument_classification": "public_instrument_class",
    "public_proxy_risk_map": "public_proxy_risk_map",
    "region_taxonomy_reference": "region_taxonomy_ref",
    "risk_free_proxy_monthly": "risk_free_proxy_monthly",
}


def _load_existing_csvs() -> dict[str, pd.DataFrame]:
    existing: dict[str, pd.DataFrame] = {}
    for path in sorted(CSV_DIR.glob("*.csv")):
        existing[path.stem] = pd.read_csv(path)
    return existing


def _month_factor(index: int, base: float, amplitude: float, phase: float, shock_scale: float = 0.0) -> float:
    cyclical = amplitude * math.sin((index + phase) / 3.0) + (amplitude / 2.5) * math.cos((index + phase) / 5.0)
    shock = shock_scale * math.sin((index + 2.0) / 1.7)
    return 1.0 + base + cyclical + shock


def _build_price_path(length: int, start: float, base: float, amplitude: float, phase: float, shock_scale: float = 0.0) -> list[float]:
    values = [start]
    for idx in range(1, length):
        values.append(values[-1] * _month_factor(idx, base=base, amplitude=amplitude, phase=phase, shock_scale=shock_scale))
    return values


def _history_ratios(driver: str) -> list[float]:
    driver_params = {
        "us_equity": (0.0105, 0.020, 0.5, 0.004),
        "global_equity": (0.0090, 0.017, 1.1, 0.003),
        "china_equity": (0.0065, 0.030, 1.8, 0.006),
        "india_equity": (0.0120, 0.024, 0.9, 0.005),
        "japan_equity": (0.0085, 0.018, 1.6, 0.003),
        "korea_equity": (0.0080, 0.022, 2.0, 0.004),
        "sea_equity": (0.0090, 0.021, 2.5, 0.004),
        "bond": (0.0035, 0.010, 1.0, 0.002),
        "gold": (0.0060, 0.018, 0.7, 0.003),
        "alts": (0.0050, 0.014, 1.4, 0.003),
        "private_equity": (0.0075, 0.007, 0.3, 0.001),
        "venture": (0.0085, 0.010, 1.2, 0.002),
        "private_credit": (0.0060, 0.004, 1.7, 0.001),
        "real_estate": (0.0055, 0.006, 2.2, 0.001),
        "infrastructure": (0.0058, 0.005, 2.7, 0.001),
        "cash": (0.0015, 0.002, 0.4, 0.0),
    }
    params = driver_params[driver]
    series = _build_price_path(len(DATE_RANGE), start=100.0, base=params[0], amplitude=params[1], phase=params[2], shock_scale=params[3])
    last = series[-1]
    return [value / last for value in series]


def _public_driver(row: dict[str, object]) -> str:
    ticker = str(row.get("ticker"))
    region = str(row.get("region_taxonomy"))
    asset_class = str(row.get("asset_class"))
    if ticker in {"AGG", "TLT", "IGIB", "HYG", "EMB", "LQD", "BIL"}:
        return "bond"
    if ticker == "GLD":
        return "gold"
    if region == "Greater China":
        return "china_equity"
    if region == "India":
        return "india_equity"
    if region == "Japan":
        return "japan_equity"
    if region == "Korea":
        return "korea_equity"
    if region == "Southeast Asia":
        return "sea_equity"
    if asset_class == "Hedge Funds / Absolute Return":
        return "alts"
    if region == "Global / Multi-region":
        return "global_equity"
    return "us_equity"


def _private_driver(asset_class: str) -> str:
    mapping = {
        "Private Equity": "private_equity",
        "Venture Capital / Growth": "venture",
        "Private Credit": "private_credit",
        "Real Estate": "real_estate",
        "Infrastructure": "infrastructure",
    }
    return mapping.get(asset_class, "private_equity")


def _build_private_master(existing: dict[str, pd.DataFrame]) -> pd.DataFrame:
    master = existing["private_fund_master"].copy()
    master["geography"] = master["fund_id"].map(GEOGRAPHY_OVERRIDES).fillna(master["geography"])
    master["investment_geography"] = master["geography"]
    master["mandate_sector"] = master["fund_id"].map(MANDATE_SECTOR_OVERRIDES).fillna("Diversified")
    master["sub_strategy"] = master["strategy"].astype(str)
    master["proxy_ticker_or_bucket"] = master["asset_class"].map(PRIVATE_PROXY_MAP).fillna("ACWI")
    master["proxy_mapping_confidence"] = master["asset_class"].map(
        {
            "Private Equity": 0.74,
            "Venture Capital / Growth": 0.70,
            "Private Credit": 0.82,
            "Real Estate": 0.76,
            "Infrastructure": 0.72,
        }
    )
    return master


def _build_private_positions(existing: dict[str, pd.DataFrame], private_master: pd.DataFrame) -> pd.DataFrame:
    positions = existing["private_fund_positions"].copy()
    for column in [
        "asset_class",
        "strategy",
        "sub_strategy",
        "investment_geography",
        "mandate_sector",
        "proxy_ticker_or_bucket",
        "proxy_mapping_confidence",
    ]:
        if column in positions.columns:
            positions = positions.drop(columns=column)
    enrich = private_master[
        [
            "fund_id",
            "asset_class",
            "strategy",
            "sub_strategy",
            "investment_geography",
            "mandate_sector",
            "proxy_ticker_or_bucket",
            "proxy_mapping_confidence",
        ]
    ]
    positions = positions.merge(enrich, on="fund_id", how="left")
    positions["proxy_mapping_flag"] = True
    positions["reporting_cadence"] = positions["fund_id"].map(
        lambda fund_id: PRIVATE_REPORTING_PROFILES.get(str(fund_id), {}).get("reporting_cadence", "Quarterly")
    )
    positions["valuation_status"] = positions["fund_id"].map(
        lambda fund_id: PRIVATE_REPORTING_PROFILES.get(
            str(fund_id),
            {"valuation_status": "Quarterly private fund marks carried into the April 30, 2026 baseline."},
        )["valuation_status"]
    )
    positions["last_statement_date"] = positions["fund_id"].map(
        lambda fund_id: PRIVATE_REPORTING_PROFILES.get(str(fund_id), {}).get("last_statement_date", "2026-03-31")
    )
    return positions


def _build_enriched_capital_calls(existing: dict[str, pd.DataFrame]) -> pd.DataFrame:
    capital_calls = existing["capital_calls"].copy()
    extra_rows = [
        {
            "event_id": "CC_PRE_003",
            "document_id": None,
            "event_date": "2025-08-14",
            "notice_date": "2025-08-14",
            "fund_id": "PF_CRESCENT_DIRECT_LEND",
            "raw_fund_name": "Crescent Direct Lending Fund",
            "mapped_fund_name": "Crescent Direct Lending Fund",
            "investor_entity_id": "ENT_ATLAS_INV_USD",
            "due_date": "2025-08-29",
            "currency": "USD",
            "amount_due_usd_m": 1.8,
            "investment_call_usd_m": 1.6,
            "management_fee_usd_m": 0.15,
            "partnership_expense_usd_m": 0.05,
            "unfunded_commitment_before_usd_m": 17.0,
            "unfunded_commitment_after_usd_m": 15.2,
            "extraction_confidence": 1.0,
            "validation_status": "Passed",
            "review_status": "Approved",
            "source": "historical_event",
        },
        {
            "event_id": "CC_PRE_004",
            "document_id": None,
            "event_date": "2025-10-18",
            "notice_date": "2025-10-18",
            "fund_id": "PF_HOME_MULTIFAMILY",
            "raw_fund_name": "HomeStone Multifamily Fund",
            "mapped_fund_name": "HomeStone Multifamily Fund",
            "investor_entity_id": "ENT_ATLAS_INV_USD",
            "due_date": "2025-11-03",
            "currency": "USD",
            "amount_due_usd_m": 2.2,
            "investment_call_usd_m": 2.0,
            "management_fee_usd_m": 0.15,
            "partnership_expense_usd_m": 0.05,
            "unfunded_commitment_before_usd_m": 18.0,
            "unfunded_commitment_after_usd_m": 15.8,
            "extraction_confidence": 1.0,
            "validation_status": "Passed",
            "review_status": "Approved",
            "source": "historical_event",
        },
        {
            "event_id": "CC_PRE_005",
            "document_id": None,
            "event_date": "2026-03-11",
            "notice_date": "2026-03-11",
            "fund_id": "PF_INFRA_CORE",
            "raw_fund_name": "Evergreen Core Infrastructure Fund",
            "mapped_fund_name": "Evergreen Core Infrastructure Fund",
            "investor_entity_id": "ENT_ATLAS_INV_USD",
            "due_date": "2026-03-27",
            "currency": "USD",
            "amount_due_usd_m": 1.6,
            "investment_call_usd_m": 1.4,
            "management_fee_usd_m": 0.15,
            "partnership_expense_usd_m": 0.05,
            "unfunded_commitment_before_usd_m": 11.6,
            "unfunded_commitment_after_usd_m": 10.0,
            "extraction_confidence": 1.0,
            "validation_status": "Passed",
            "review_status": "Approved",
            "source": "historical_event",
        },
    ]
    return pd.concat([capital_calls, pd.DataFrame(extra_rows)], ignore_index=True)


def _build_enriched_distributions(existing: dict[str, pd.DataFrame]) -> pd.DataFrame:
    distributions = existing["distributions"].copy()
    extra_rows = [
        {
            "event_id": "DIST_PRE_002",
            "document_id": None,
            "event_date": "2025-07-18",
            "notice_date": "2025-07-18",
            "fund_id": "PF_HARBOUR_CORE_RE",
            "raw_fund_name": "Harbour Core Real Estate Fund",
            "mapped_fund_name": "Harbour Core Real Estate Fund",
            "investor_entity_id": "ENT_ATLAS_INV_USD",
            "payment_date": "2025-07-31",
            "currency": "USD",
            "gross_distribution_usd_m": 1.4,
            "return_of_capital_usd_m": 1.0,
            "realized_gain_usd_m": 0.2,
            "income_usd_m": 0.2,
            "fees_expenses_usd_m": 0.0,
            "net_distribution_usd_m": 1.4,
            "extraction_confidence": 1.0,
            "validation_status": "Passed",
            "review_status": "Approved",
            "source": "historical_event",
        },
        {
            "event_id": "DIST_PRE_003",
            "document_id": None,
            "event_date": "2025-10-16",
            "notice_date": "2025-10-16",
            "fund_id": "PF_CRESCENT_DIRECT_LEND",
            "raw_fund_name": "Crescent Direct Lending Fund",
            "mapped_fund_name": "Crescent Direct Lending Fund",
            "investor_entity_id": "ENT_ATLAS_INV_USD",
            "payment_date": "2025-10-31",
            "currency": "USD",
            "gross_distribution_usd_m": 1.7,
            "return_of_capital_usd_m": 1.2,
            "realized_gain_usd_m": 0.3,
            "income_usd_m": 0.2,
            "fees_expenses_usd_m": 0.0,
            "net_distribution_usd_m": 1.7,
            "extraction_confidence": 1.0,
            "validation_status": "Passed",
            "review_status": "Approved",
            "source": "historical_event",
        },
        {
            "event_id": "DIST_PRE_004",
            "document_id": None,
            "event_date": "2025-12-19",
            "notice_date": "2025-12-19",
            "fund_id": "PF_INFRA_CORE",
            "raw_fund_name": "Evergreen Core Infrastructure Fund",
            "mapped_fund_name": "Evergreen Core Infrastructure Fund",
            "investor_entity_id": "ENT_ATLAS_INV_USD",
            "payment_date": "2025-12-31",
            "currency": "USD",
            "gross_distribution_usd_m": 1.2,
            "return_of_capital_usd_m": 0.8,
            "realized_gain_usd_m": 0.2,
            "income_usd_m": 0.2,
            "fees_expenses_usd_m": 0.0,
            "net_distribution_usd_m": 1.2,
            "extraction_confidence": 1.0,
            "validation_status": "Passed",
            "review_status": "Approved",
            "source": "historical_event",
        },
        {
            "event_id": "DIST_PRE_005",
            "document_id": None,
            "event_date": "2026-03-18",
            "notice_date": "2026-03-18",
            "fund_id": "PF_BLUE_HORIZON_III",
            "raw_fund_name": "Blue Horizon Ventures III",
            "mapped_fund_name": "Blue Horizon Ventures III",
            "investor_entity_id": "ENT_ATLAS_INV_USD",
            "payment_date": "2026-03-31",
            "currency": "USD",
            "gross_distribution_usd_m": 0.9,
            "return_of_capital_usd_m": 0.4,
            "realized_gain_usd_m": 0.3,
            "income_usd_m": 0.2,
            "fees_expenses_usd_m": 0.0,
            "net_distribution_usd_m": 0.9,
            "extraction_confidence": 1.0,
            "validation_status": "Passed",
            "review_status": "Approved",
            "source": "historical_event",
        },
    ]
    return pd.concat([distributions, pd.DataFrame(extra_rows)], ignore_index=True)


def _build_enriched_newsletter_updates(existing: dict[str, pd.DataFrame]) -> pd.DataFrame:
    newsletters = existing["newsletter_updates"].copy()
    extra_rows = [
        {
            "update_id": "NEWS_PRE_002",
            "document_id": None,
            "fund_id": "PF_GLOBAL_GROWTH_II",
            "raw_fund_name": "Redwood Growth Fund II",
            "mapped_fund_name": "Redwood Growth Fund II",
            "period": "Q3 2025",
            "market_themes": "AI application software and slower private exit environment.",
            "new_investments": "Selective follow-on support for existing software names.",
            "valuation_commentary": "Marks broadly stable with modest pressure on late-stage multiples.",
            "risk_notes": "Exit timing and financing conditions remain uneven.",
            "expected_capital_activity": "Moderate follow-on activity expected over the next two quarters.",
            "extraction_confidence": 1.0,
            "validation_status": "Passed",
            "review_status": "Approved",
            "source": "historical_event",
        },
        {
            "update_id": "NEWS_PRE_003",
            "document_id": None,
            "fund_id": "PF_CRESCENT_DIRECT_LEND",
            "raw_fund_name": "Crescent Direct Lending Fund",
            "mapped_fund_name": "Crescent Direct Lending Fund",
            "period": "Q4 2025",
            "market_themes": "Higher base rates supported lender economics in senior direct lending.",
            "new_investments": "Two add-on loans closed in healthcare services and industrial software.",
            "valuation_commentary": "Portfolio marks stable and coupon carry remained supportive.",
            "risk_notes": "Watch leverage and sponsor-driven refinancing risk.",
            "expected_capital_activity": "Steady repayment and modest recycling activity expected.",
            "extraction_confidence": 1.0,
            "validation_status": "Passed",
            "review_status": "Approved",
            "source": "historical_event",
        },
        {
            "update_id": "NEWS_PRE_004",
            "document_id": None,
            "fund_id": "PF_HARBOUR_CORE_RE",
            "raw_fund_name": "Harbour Core Real Estate Fund",
            "mapped_fund_name": "Harbour Core Real Estate Fund",
            "period": "Q1 2026",
            "market_themes": "Occupancy held up in core assets while financing spreads remained elevated.",
            "new_investments": "No new acquisitions; asset management focused on leasing and refinancing.",
            "valuation_commentary": "Income-producing assets were broadly stable with limited mark movement.",
            "risk_notes": "Refinancing cost and cap-rate expansion remain key watch items.",
            "expected_capital_activity": "Low near-term capital activity expected outside routine property capex.",
            "extraction_confidence": 1.0,
            "validation_status": "Passed",
            "review_status": "Approved",
            "source": "historical_event",
        },
    ]
    return pd.concat([newsletters, pd.DataFrame(extra_rows)], ignore_index=True)


def _build_cash_accounts() -> pd.DataFrame:
    rows = [
        {
            "as_of_date": BASELINE_DATE,
            "cash_account_id": "CASH_OPS_USD",
            "account_name": "USD Operating Cash",
            "currency": "USD",
            "entity_id": "ENT_ATLAS_INV_USD",
            "balance_usd_m": 12.0,
            "liquidity_bucket": "Cash",
            "purpose": "Operating cash for calls and distributions",
            "is_operating_cash": True,
            "is_soft_liquidity_eligible": True,
        },
        {
            "as_of_date": BASELINE_DATE,
            "cash_account_id": "CASH_RESERVE_USD",
            "account_name": "USD Liquidity Reserve",
            "currency": "USD",
            "entity_id": "ENT_ATLAS_INV_USD",
            "balance_usd_m": 4.5,
            "liquidity_bucket": "Cash",
            "purpose": "Reserve liquidity",
            "is_operating_cash": False,
            "is_soft_liquidity_eligible": True,
        },
        {
            "as_of_date": BASELINE_DATE,
            "cash_account_id": "CASH_HKD",
            "account_name": "HKD Working Capital",
            "currency": "HKD",
            "entity_id": "ENT_ATLAS_INV_USD",
            "balance_usd_m": 2.4,
            "liquidity_bucket": "Cash",
            "purpose": "Asia working capital",
            "is_operating_cash": False,
            "is_soft_liquidity_eligible": True,
        },
        {
            "as_of_date": BASELINE_DATE,
            "cash_account_id": "CASH_JPY",
            "account_name": "JPY Treasury Buffer",
            "currency": "JPY",
            "entity_id": "ENT_ATLAS_INV_USD",
            "balance_usd_m": 1.6,
            "liquidity_bucket": "Cash",
            "purpose": "Regional treasury buffer",
            "is_operating_cash": False,
            "is_soft_liquidity_eligible": True,
        },
        {
            "as_of_date": BASELINE_DATE,
            "cash_account_id": "CASH_SGD",
            "account_name": "SGD Near-Term Reserve",
            "currency": "SGD",
            "entity_id": "ENT_ATLAS_INV_USD",
            "balance_usd_m": 2.0,
            "liquidity_bucket": "Cash",
            "purpose": "Southeast Asia reserve",
            "is_operating_cash": False,
            "is_soft_liquidity_eligible": True,
        },
    ]
    return pd.DataFrame(rows)


def _build_cash_accounts_post_approved(cash_df: pd.DataFrame) -> pd.DataFrame:
    updated = cash_df.copy()
    operating_mask = updated["cash_account_id"] == "CASH_OPS_USD"
    updated.loc[operating_mask, "balance_usd_m"] = updated.loc[operating_mask, "balance_usd_m"] - 4.2 + 3.1
    return updated


def _build_family_entities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "entity_id": "ENT_ATLAS_INV_USD",
                "entity_name": "Atlas Family Office Investment Entity",
                "entity_type": "Investment Vehicle",
                "jurisdiction": "Singapore",
                "reporting_currency": "USD",
                "owner_group": "Atlas Family Office",
                "base_location": "Singapore",
                "status": "Active",
            },
            {
                "entity_id": "ENT_ATLAS_TREASURY",
                "entity_name": "Atlas Family Office Treasury",
                "entity_type": "Treasury Vehicle",
                "jurisdiction": "Singapore",
                "reporting_currency": "USD",
                "owner_group": "Atlas Family Office",
                "base_location": "Singapore",
                "status": "Active",
            },
            {
                "entity_id": "ENT_ATLAS_HOLDCO",
                "entity_name": "Atlas Family Office HoldCo",
                "entity_type": "HoldCo",
                "jurisdiction": "Singapore",
                "reporting_currency": "USD",
                "owner_group": "Atlas Family Office",
                "base_location": "Singapore",
                "status": "Active",
            },
            {
                "entity_id": "ENT_ATLAS_CHARITY",
                "entity_name": "Atlas Family Office Foundation",
                "entity_type": "Foundation",
                "jurisdiction": "Singapore",
                "reporting_currency": "USD",
                "owner_group": "Atlas Family Office",
                "base_location": "Singapore",
                "status": "Active",
            },
        ]
    )


def _build_public_holdings_df() -> pd.DataFrame:
    public_df = pd.DataFrame(PUBLIC_HOLDINGS)
    public_df["entity_id"] = "ENT_ATLAS_INV_USD"
    public_df["region"] = public_df["region_taxonomy"]
    public_df["current_market_cap_bucket"] = public_df["market_cap_bucket"]
    public_df["is_public_liquid_asset"] = True
    public_df["is_private_asset"] = False
    public_df["as_of_date"] = BASELINE_DATE
    return public_df


def _build_cash_holdings_df(cash_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in cash_df.itertuples(index=False):
        rows.append(
            {
                "holding_id": f"H_{row.cash_account_id}",
                "holding_name": row.account_name,
                "asset_class": "Cash & Liquidity",
                "sub_asset_class": "Cash Accounts",
                "region_taxonomy": "Global / Multi-region",
                "region": "Global / Multi-region",
                "country": "Cash Pool",
                "currency": row.currency,
                "entity_id": row.entity_id,
                "ticker": "",
                "final_value_usd_m": row.balance_usd_m,
                "instrument_type": "cash",
                "position_side_current": "long",
                "current_exposure_usd_m": row.balance_usd_m,
                "current_gross_notional_usd_m": row.balance_usd_m,
                "current_delta_adjusted_exposure_usd_m": row.balance_usd_m,
                "gics_sector": "Cash",
                "gics_industry_group": "Cash",
                "market_cap_bucket": "Non-classifiable",
                "current_market_cap_bucket": "Non-classifiable",
                "lookthrough_method": "direct",
                "classification_status": "direct",
                "proxy_mapping_status": "direct",
                "liquidity_bucket": row.liquidity_bucket,
                "data_source": DATA_SOURCE,
                "notes": row.purpose,
                "is_public_liquid_asset": False,
                "is_private_asset": False,
                "as_of_date": row.as_of_date,
            }
        )
    return pd.DataFrame(rows)


def _build_private_holdings_df(private_positions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in private_positions.itertuples(index=False):
        rows.append(
            {
                "holding_id": f"H_{row.fund_id}",
                "holding_name": row.fund_name,
                "asset_class": row.asset_class,
                "sub_asset_class": row.strategy,
                "region_taxonomy": row.investment_geography,
                "region": row.investment_geography,
                "country": row.investment_geography,
                "currency": "USD",
                "entity_id": "ENT_ATLAS_INV_USD",
                "ticker": "",
                "final_value_usd_m": row.current_nav_usd_m,
                "instrument_type": "private_fund",
                "position_side_current": "long",
                "current_exposure_usd_m": row.current_nav_usd_m,
                "current_gross_notional_usd_m": row.current_nav_usd_m,
                "current_delta_adjusted_exposure_usd_m": row.current_nav_usd_m,
                "gics_sector": row.mandate_sector,
                "gics_industry_group": row.strategy,
                "market_cap_bucket": "Non-classifiable",
                "current_market_cap_bucket": "Non-classifiable",
                "lookthrough_method": "mandate_proxy",
                "classification_status": "proxy",
                "proxy_mapping_status": "proxy" if row.proxy_mapping_flag else "unknown",
                "liquidity_bucket": "Illiquid",
                "data_source": DATA_SOURCE,
                "notes": row.valuation_status,
                "is_public_liquid_asset": False,
                "is_private_asset": True,
                "as_of_date": row.as_of_date,
            }
        )
    return pd.DataFrame(rows)


def _build_portfolio_holdings(public_df: pd.DataFrame, private_df: pd.DataFrame, cash_df: pd.DataFrame) -> pd.DataFrame:
    holdings = pd.concat([public_df, private_df, cash_df], ignore_index=True)
    holdings["allocation_pct"] = holdings["final_value_usd_m"] / holdings["final_value_usd_m"].sum()
    return holdings.sort_values(["asset_class", "holding_name"]).reset_index(drop=True)


def _build_public_instrument_classification(public_df: pd.DataFrame) -> pd.DataFrame:
    classification = public_df.copy()
    classification["underlying_type"] = classification["instrument_type"].replace(
        {
            "future": "equity_index",
            "listed_option": "equity_index",
            "etf": "basket",
            "equity": "equity",
            "fund": "mandate_proxy",
        }
    )
    classification["underlying_reference"] = classification["ticker"].replace(
        {
            "ES1": "SPY",
            "NQ1": "QQQ",
            "SPY_PUT": "SPY",
            "HSI1": "2800.HK",
            "GMACRO": "ACWI",
            "MKTNEUT": "ACWI",
        }
    )
    classification["lookthrough_available_flag"] = classification["instrument_type"].isin(["equity", "etf"])
    classification["benchmark_proxy"] = classification["underlying_reference"]
    classification["gics_sector_current"] = classification["gics_sector"]
    classification["gics_industry_group_current"] = classification["gics_industry_group"]
    classification["region_taxonomy_current"] = classification["region_taxonomy"]
    classification["market_cap_bucket_current"] = classification["market_cap_bucket"]
    classification["classification_notes"] = classification["notes"]
    return classification[
        [
            "holding_id",
            "ticker",
            "instrument_type",
            "underlying_type",
            "underlying_reference",
            "lookthrough_available_flag",
            "lookthrough_method",
            "benchmark_proxy",
            "gics_sector_current",
            "gics_industry_group_current",
            "region_taxonomy_current",
            "market_cap_bucket_current",
            "classification_status",
            "classification_notes",
        ]
    ]


def _build_public_proxy_maps(public_df: pd.DataFrame, private_positions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    risk_map_rows = []
    legacy_rows = []
    for row in public_df.itertuples(index=False):
        proxy = row.ticker
        if row.ticker == "ES1":
            proxy = "SPY"
        elif row.ticker == "NQ1":
            proxy = "QQQ"
        elif row.ticker == "SPY_PUT":
            proxy = "SPY"
        elif row.ticker == "HSI1":
            proxy = "2800.HK"
        elif row.ticker == "GMACRO":
            proxy = "ACWI"
        elif row.ticker == "MKTNEUT":
            proxy = "ACWI"
        risk_map_rows.append(
            {
                "holding_id": row.holding_id,
                "holding_name": row.holding_name,
                "ticker_or_proxy": proxy,
                "proxy_name": proxy,
                "risk_proxy_bucket": row.asset_class,
                "asset_class": row.asset_class,
                "gics_sector": row.gics_sector,
                "region_taxonomy": row.region_taxonomy,
                "liquidity_bucket": row.liquidity_bucket,
                "use_in_final_risk_module": True,
                "mapping_confidence": 1.0 if proxy == row.ticker else 0.82,
                "mapping_method": row.lookthrough_method,
                "mapping_notes": row.notes,
            }
        )
        legacy_rows.append(
            {
                "holding_id": row.holding_id,
                "holding_name": row.holding_name,
                "ticker_or_proxy": proxy,
                "use_in_final_risk_module": True,
                "current_dataset_source": DATA_SOURCE,
                "final_dataset_source": DATA_SOURCE,
                "notes": row.notes,
            }
        )

    for row in private_positions.itertuples(index=False):
        risk_map_rows.append(
            {
                "holding_id": f"H_{row.fund_id}",
                "holding_name": row.fund_name,
                "ticker_or_proxy": row.proxy_ticker_or_bucket,
                "proxy_name": row.proxy_ticker_or_bucket,
                "risk_proxy_bucket": row.asset_class,
                "asset_class": row.asset_class,
                "gics_sector": row.mandate_sector,
                "region_taxonomy": row.investment_geography,
                "liquidity_bucket": "Illiquid",
                "use_in_final_risk_module": True,
                "mapping_confidence": row.proxy_mapping_confidence,
                "mapping_method": "mandate_proxy",
                "mapping_notes": "Private asset included through defensible public proxy overlay.",
            }
        )

    return pd.DataFrame(risk_map_rows), pd.DataFrame(legacy_rows)


def _build_private_fund_monthly(private_positions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in private_positions.itertuples(index=False):
        ratios = _history_ratios(_private_driver(row.asset_class))
        scale = 1.0 + (sum(ord(ch) for ch in row.fund_id) % 7) / 100.0
        adjusted = [ratio * (0.97 + (scale - 1.0)) for ratio in ratios]
        last = adjusted[-1]
        normalized = [value / last for value in adjusted]
        for date, ratio in zip(DATE_RANGE, normalized):
            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "fund_id": row.fund_id,
                    "fund_name": row.fund_name,
                    "nav_usd_m": round(row.current_nav_usd_m * ratio, 4),
                    "investment_geography": row.investment_geography,
                    "mandate_sector": row.mandate_sector,
                    "strategy": row.strategy,
                    "source": DATA_SOURCE,
                }
            )
    return pd.DataFrame(rows)


def _build_cash_history(cash_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    cash_ratios = _history_ratios("cash")
    for row in cash_df.itertuples(index=False):
        scale = 1.0 + (sum(ord(ch) for ch in row.cash_account_id) % 5) / 200.0
        adjusted = [ratio * scale for ratio in cash_ratios]
        last = adjusted[-1]
        normalized = [value / last for value in adjusted]
        holding_id = f"H_{row.cash_account_id}"
        for date, ratio in zip(DATE_RANGE, normalized):
            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "holding_id": holding_id,
                    "holding_name": row.account_name,
                    "asset_class": "Cash & Liquidity",
                    "value_usd_m": round(row.balance_usd_m * ratio, 4),
                    "source": DATA_SOURCE,
                }
            )
    return pd.DataFrame(rows)


def _build_public_price_history(public_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in public_df.itertuples(index=False):
        if not row.ticker:
            continue
        ratios = _history_ratios(_public_driver(row._asdict()))
        start_price = 85.0 + (sum(ord(ch) for ch in row.ticker) % 70)
        price_path = [round(start_price * ratio / ratios[0], 4) for ratio in ratios]
        for date, price in zip(DATE_RANGE, price_path):
            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "ticker": row.ticker,
                    "currency": row.currency,
                    "close_price": price,
                    "source_type": "synthetic",
                    "note": DATA_SOURCE,
                }
            )
    return pd.DataFrame(rows)


def _build_public_value_history(public_df: pd.DataFrame, prices_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in public_df.itertuples(index=False):
        if row.ticker:
            ticker_prices = prices_df.loc[prices_df["ticker"] == row.ticker, ["date", "close_price"]].copy()
            ticker_prices["ratio"] = ticker_prices["close_price"] / ticker_prices["close_price"].iloc[-1]
            ratios = ticker_prices["ratio"].tolist()
        else:
            ratios = _history_ratios(_public_driver(row._asdict()))
        for date, ratio in zip(DATE_RANGE, ratios):
            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "holding_id": row.holding_id,
                    "holding_name": row.holding_name,
                    "asset_class": row.asset_class,
                    "value_usd_m": round(row.final_value_usd_m * ratio, 4),
                    "source": DATA_SOURCE,
                }
            )
    return pd.DataFrame(rows)


def _build_portfolio_monthly_by_holding(public_history: pd.DataFrame, private_monthly: pd.DataFrame, cash_history: pd.DataFrame, private_positions: pd.DataFrame) -> pd.DataFrame:
    private_meta = private_positions[["fund_id", "fund_name", "asset_class"]].copy()
    private_history = private_monthly.merge(private_meta, on=["fund_id", "fund_name"], how="left")
    private_history = private_history.rename(columns={"nav_usd_m": "value_usd_m"})[
        ["date", "fund_id", "fund_name", "asset_class", "value_usd_m", "source"]
    ]
    private_history = private_history.rename(columns={"fund_id": "holding_id", "fund_name": "holding_name"})
    private_history["holding_id"] = "H_" + private_history["holding_id"].astype(str)

    combined = pd.concat([public_history, private_history, cash_history], ignore_index=True)
    return combined.sort_values(["date", "holding_id"]).reset_index(drop=True)


def _build_portfolio_monthly_summary(monthly_by_holding: pd.DataFrame, holdings_df: pd.DataFrame, cash_df: pd.DataFrame) -> pd.DataFrame:
    flags = holdings_df[["holding_id", "is_public_liquid_asset", "is_private_asset", "asset_class"]].copy()
    merged = monthly_by_holding.merge(flags, on=["holding_id", "asset_class"], how="left")
    merged["value_usd_m"] = pd.to_numeric(merged["value_usd_m"], errors="coerce")

    summaries = []
    operating_ids = {f"H_{row.cash_account_id}" for row in cash_df.loc[cash_df["is_operating_cash"], ["cash_account_id"]].itertuples(index=False)}
    for date, group in merged.groupby("date"):
        total_aum = float(group["value_usd_m"].sum())
        public_markets = float(group.loc[group["is_public_liquid_asset"].fillna(False), "value_usd_m"].sum())
        private_nav = float(group.loc[group["is_private_asset"].fillna(False), "value_usd_m"].sum())
        cash_total = float(group.loc[group["asset_class"] == "Cash & Liquidity", "value_usd_m"].sum())
        operating_cash = float(group.loc[group["holding_id"].isin(operating_ids), "value_usd_m"].sum())
        summaries.append(
            {
                "date": date,
                "total_aum_usd_m": round(total_aum, 4),
                "public_markets_usd_m": round(public_markets, 4),
                "closed_end_private_fund_nav_usd_m": round(private_nav, 4),
                "cash_liquidity_usd_m": round(cash_total, 4),
                "operating_cash_usd_m": round(operating_cash, 4),
                "hard_liquidity_usd_m": round(operating_cash, 4),
                "soft_liquidity_usd_m": round(cash_total * 1.18, 4),
                "source": DATA_SOURCE,
                "return_series_label": "full_portfolio_synthetic",
                "source_label": DATA_SOURCE,
            }
        )

    summary_df = pd.DataFrame(summaries).sort_values("date").reset_index(drop=True)
    summary_df["portfolio_monthly_return"] = summary_df["total_aum_usd_m"].pct_change()
    return summary_df


def _build_position_exposure_history(holdings_df: pd.DataFrame, monthly_by_holding: pd.DataFrame) -> pd.DataFrame:
    meta_columns = [
        "holding_id",
        "holding_name",
        "asset_class",
        "sub_asset_class",
        "instrument_type",
        "position_side_current",
        "gics_sector",
        "gics_industry_group",
        "region_taxonomy",
        "market_cap_bucket",
        "liquidity_bucket",
        "current_exposure_usd_m",
        "current_gross_notional_usd_m",
        "current_delta_adjusted_exposure_usd_m",
        "lookthrough_method",
        "classification_status",
        "ticker",
    ]
    history = monthly_by_holding.merge(holdings_df[meta_columns], on=["holding_id", "holding_name", "asset_class"], how="left")
    total_by_date = history.groupby("date")["value_usd_m"].transform("sum")
    scaling_ratio = history["value_usd_m"] / history.groupby("holding_id")["value_usd_m"].transform("last")
    history["signed_notional_usd_m"] = history["current_exposure_usd_m"] * scaling_ratio
    history["gross_notional_usd_m"] = history["current_gross_notional_usd_m"].abs() * scaling_ratio.abs()
    history["delta_adjusted_exposure_usd_m"] = history["current_delta_adjusted_exposure_usd_m"] * scaling_ratio
    history["position_id"] = history["holding_id"]
    history["position_side"] = history["position_side_current"]
    history["market_value_usd_m"] = history["value_usd_m"]
    history["nav_weight"] = history["market_value_usd_m"] / total_by_date
    history["gross_weight"] = history["gross_notional_usd_m"] / total_by_date
    history["net_weight"] = history["signed_notional_usd_m"] / total_by_date
    history["gics_sector_pti"] = history["gics_sector"]
    history["gics_industry_group_pti"] = history["gics_industry_group"]
    history["region_taxonomy_pti"] = history["region_taxonomy"]
    history["market_cap_bucket_pti"] = history["market_cap_bucket"]
    history["underlying_reference"] = history["ticker"].replace({"ES1": "SPY", "NQ1": "QQQ", "SPY_PUT": "SPY", "HSI1": "2800.HK"})
    history["current_exposure_basis"] = history["instrument_type"].replace(
        {
            "future": "signed_notional",
            "listed_option": "delta_adjusted_exposure",
        }
    ).fillna("market_value")
    return history[
        [
            "date",
            "position_id",
            "holding_id",
            "holding_name",
            "instrument_type",
            "position_side",
            "market_value_usd_m",
            "signed_notional_usd_m",
            "gross_notional_usd_m",
            "delta_adjusted_exposure_usd_m",
            "current_exposure_basis",
            "nav_weight",
            "gross_weight",
            "net_weight",
            "asset_class",
            "sub_asset_class",
            "gics_sector_pti",
            "gics_industry_group_pti",
            "region_taxonomy_pti",
            "market_cap_bucket_pti",
            "liquidity_bucket",
            "underlying_reference",
            "lookthrough_method",
            "classification_status",
        ]
    ].sort_values(["date", "holding_id"])


def _build_risk_free_proxy_monthly() -> pd.DataFrame:
    rows = []
    for idx, date in enumerate(DATE_RANGE):
        annualized = 0.043 + 0.004 * math.sin((idx + 1) / 5.0) + 0.002 * math.cos((idx + 1) / 8.0)
        monthly_return = (1.0 + annualized) ** (1.0 / 12.0) - 1.0
        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "rf_monthly_return": round(monthly_return, 8),
                "rf_annualized_rate": round(annualized, 6),
                "source_label": "synthetic_3m_tbill_proxy",
            }
        )
    return pd.DataFrame(rows)


def _build_region_taxonomy_reference() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"region_code": "NA", "region_taxonomy": "North America", "parent_region": "Americas", "description": "United States and Canada exposure."},
            {"region_code": "GC", "region_taxonomy": "Greater China", "parent_region": "Asia", "description": "China, Hong Kong, and Taiwan-related exposure."},
            {"region_code": "IN", "region_taxonomy": "India", "parent_region": "Asia", "description": "India exposure."},
            {"region_code": "SEA", "region_taxonomy": "Southeast Asia", "parent_region": "Asia", "description": "Singapore and ASEAN exposure."},
            {"region_code": "JP", "region_taxonomy": "Japan", "parent_region": "Asia", "description": "Japan exposure."},
            {"region_code": "KR", "region_taxonomy": "Korea", "parent_region": "Asia", "description": "South Korea exposure."},
            {"region_code": "EU", "region_taxonomy": "Europe", "parent_region": "EMEA", "description": "Europe exposure."},
            {"region_code": "GL", "region_taxonomy": "Global / Multi-region", "parent_region": "Global", "description": "Diversified or global exposure."},
        ]
    )


def _build_fx_rates() -> pd.DataFrame:
    currencies = {
        "USD": 1.0,
        "HKD": 7.80,
        "JPY": 140.0,
        "INR": 82.0,
        "SGD": 1.34,
        "CNY": 7.10,
        "EUR": 0.92,
    }
    rows = []
    for idx, date in enumerate(DATE_RANGE):
        for currency, base in currencies.items():
            variation = 1.0 + 0.015 * math.sin((idx + 1) / 6.0 + len(currency))
            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "currency": currency,
                    "usd_to_local_rate": round(base * variation, 6),
                    "source": DATA_SOURCE,
                }
            )
    return pd.DataFrame(rows)


def _build_table_name_map(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name in sorted(tables):
        rows.append(
            {
                "report_conceptual_table": name,
                "actual_csv_name": f"{name}.csv",
                "workbook_sheet": SHEET_NAME_MAP.get(name, name[:31]),
                "notes": "Synthetic V1 canonical table",
            }
        )
    return pd.DataFrame(rows)


def _build_data_dictionary(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    known = {
        "position_side_current": "Current signed direction of the position.",
        "current_exposure_usd_m": "Current net exposure in USD millions.",
        "current_gross_notional_usd_m": "Current gross notional retained separately from market value.",
        "current_delta_adjusted_exposure_usd_m": "Current delta-adjusted exposure for options and derivatives.",
        "gics_sector": "Primary sector taxonomy for V1 reporting.",
        "market_cap_bucket": "Current reporting market-cap bucket for public and equity-linked assets.",
        "region_taxonomy": "Primary region taxonomy used in dashboard reporting.",
        "rf_monthly_return": "Monthly risk-free return proxy used for Sharpe calculations.",
        "proxy_ticker_or_bucket": "Defensible public-market proxy used for risk overlay.",
    }
    rows = []
    for table_name, df in tables.items():
        for column in df.columns:
            rows.append(
                {
                    "table_name": table_name,
                    "column_name": column,
                    "description": known.get(column, f"Synthetic V1 field for `{column}`."),
                    "data_type": str(df[column].dtype),
                    "notes": "Generated by src.generate_dataset",
                }
            )
    return pd.DataFrame(rows)


def _write_package_docs(tables: dict[str, pd.DataFrame]) -> None:
    package_readme = RAW_DATA_DIR / "README_corrected_data_package.md"
    qa_summary = RAW_DATA_DIR / "QA_validation_summary.md"
    package_readme.write_text(
        "\n".join(
            [
                "# Synthetic Family Office Dataset V1",
                "",
                "This package is the regenerated synthetic V1 dataset for the project portfolio dashboard proof of concept.",
                "",
                "## Baseline Assumptions",
                "",
                "- Baseline snapshot date: `2026-04-30`",
                "- Total AUM: `USD 750.0m`",
                "- Public / liquid assets: `USD 367.5m`",
                "- Closed-end private fund NAV: `USD 360.0m`",
                "- Cash and liquidity: `USD 22.5m`",
                "- Total private commitments: `USD 500.0m`",
                "- Paid-in capital: `USD 365.0m`",
                "- Unfunded commitments: `USD 135.0m`",
                "",
                "## V1 Dataset Features",
                "",
                "- public/liquid long-short support with signed notional and delta-adjusted option exposure",
                "- GICS sector classification for public holdings",
                "- market-cap buckets for public and equity-linked exposure",
                "- region taxonomy including Greater China, India, Southeast Asia, Japan, Korea, and Global / Multi-region",
                "- synthetic monthly risk-free proxy for Sharpe calculations",
                "- public proxy risk overlay mapping",
                "",
                "## Tables",
                "",
                *[f"- `{name}.csv`" for name in sorted(tables)],
            ]
        ),
        encoding="utf-8",
    )
    qa_summary.write_text(
        "\n".join(
            [
                "# Dataset QA Validation Summary",
                "",
                "- `portfolio_monthly_summary.csv` ends at `USD 750.0m` total AUM.",
                "- `private_fund_positions.csv` totals reconcile to `USD 500.0m` commitments, `USD 365.0m` paid-in, `USD 135.0m` unfunded, and `USD 360.0m` NAV.",
                "- `cash_accounts.csv` totals reconcile to `USD 22.5m` cash and liquidity.",
                "- `documents/` contains 6 mock May 2026 PDF files.",
                "- V1 enrichment tables include `position_exposure_history.csv`, `public_instrument_classification.csv`, `public_proxy_risk_map.csv`, `risk_free_proxy_monthly.csv`, and `region_taxonomy_reference.csv`.",
            ]
        ),
        encoding="utf-8",
    )


def _write_workbook(tables: dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(WORKBOOK_PATH, engine="openpyxl") as writer:
        for table_name, df in sorted(tables.items()):
            df.to_excel(writer, sheet_name=SHEET_NAME_MAP.get(table_name, table_name[:31]), index=False)


def run() -> dict[str, object]:
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    existing = _load_existing_csvs()

    private_master = _build_private_master(existing)
    private_positions = _build_private_positions(existing, private_master)
    cash_accounts = _build_cash_accounts()
    cash_accounts_post_approved = _build_cash_accounts_post_approved(cash_accounts)
    public_holdings = _build_public_holdings_df()
    private_holdings = _build_private_holdings_df(private_positions)
    cash_holdings = _build_cash_holdings_df(cash_accounts)
    portfolio_holdings = _build_portfolio_holdings(public_holdings, private_holdings, cash_holdings)
    public_classification = _build_public_instrument_classification(public_holdings)
    public_proxy_risk_map, legacy_proxy_map = _build_public_proxy_maps(public_holdings, private_positions)
    private_fund_monthly = _build_private_fund_monthly(private_positions)
    public_prices = _build_public_price_history(public_holdings)
    public_history = _build_public_value_history(public_holdings, public_prices)
    cash_history = _build_cash_history(cash_accounts)
    portfolio_monthly_by_holding = _build_portfolio_monthly_by_holding(public_history, private_fund_monthly, cash_history, private_positions)
    portfolio_monthly_summary = _build_portfolio_monthly_summary(portfolio_monthly_by_holding, portfolio_holdings, cash_accounts)
    position_exposure_history = _build_position_exposure_history(portfolio_holdings, portfolio_monthly_by_holding)
    risk_free = _build_risk_free_proxy_monthly()
    region_taxonomy_reference = _build_region_taxonomy_reference()
    fx_rates = _build_fx_rates()
    family_entities = _build_family_entities()

    tables: dict[str, pd.DataFrame] = {
        "cash_accounts": cash_accounts,
        "cash_accounts_post_approved": cash_accounts_post_approved,
        "family_entities": family_entities,
        "fx_rates": fx_rates,
        "portfolio_holdings": portfolio_holdings,
        "portfolio_monthly_by_holding": portfolio_monthly_by_holding,
        "portfolio_monthly_summary": portfolio_monthly_summary,
        "position_exposure_history": position_exposure_history,
        "private_fund_master": private_master,
        "private_fund_monthly": private_fund_monthly,
        "private_fund_positions": private_positions,
        "public_instrument_classification": public_classification,
        "public_monthly_prices_synthetic": public_prices,
        "public_proxy_risk_map": public_proxy_risk_map,
        "real_public_market_proxy_map": legacy_proxy_map,
        "region_taxonomy_reference": region_taxonomy_reference,
        "risk_free_proxy_monthly": risk_free,
    }

    for name in PRESERVED_TABLES:
        if name in existing:
            tables[name] = existing[name]

    if "capital_calls" in tables:
        tables["capital_calls"] = _build_enriched_capital_calls({"capital_calls": tables["capital_calls"]})
    if "distributions" in tables:
        tables["distributions"] = _build_enriched_distributions({"distributions": tables["distributions"]})
    if "newsletter_updates" in tables:
        tables["newsletter_updates"] = _build_enriched_newsletter_updates({"newsletter_updates": tables["newsletter_updates"]})

    tables["table_name_map"] = _build_table_name_map(tables)
    tables["data_dictionary"] = _build_data_dictionary(tables)

    for table_name, df in sorted(tables.items()):
        df.to_csv(CSV_DIR / f"{table_name}.csv", index=False)

    _write_workbook(tables)
    _write_package_docs(tables)

    return {
        "table_count": len(tables),
        "csv_dir": CSV_DIR,
        "workbook_path": WORKBOOK_PATH,
    }


def main() -> int:
    result = run()
    print(
        f"dataset_tables={result['table_count']} "
        f"csv_dir={result['csv_dir']} workbook={result['workbook_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
