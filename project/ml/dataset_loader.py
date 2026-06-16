# -*- coding: utf-8 -*-
"""酒店运营训练数据加载与预处理工具。"""
from __future__ import annotations

import calendar
import os
from typing import Callable

import numpy as np
import pandas as pd

from cancellation_features import (
    build_lead_time_bucket,
    normalize_common_market_segment,
    normalize_common_meal_plan,
    normalize_room_type,
    safe_ratio,
)

BASE = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE, "data")
EXTERNAL_DATA_DIR = os.path.join(DATA_DIR, "external")
FALLBACK_DATA_PATH = os.path.join(DATA_DIR, "hotel_ops_1095.csv")
STANDARD_ROOM_COUNT = 120

HOLIDAYS = {
    (1, 1), (2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7),
    (4, 4), (4, 5), (4, 6), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5),
    (6, 1), (6, 2), (9, 15), (9, 16), (9, 17),
    (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7),
}

PUBLIC_DATASET_SPECS = {
    "hotel_booking_demand": {
        "display_name": "Hotel Booking Demand",
        "row_count_hint": 119390,
        "source_url": "https://www.sciencedirect.com/science/article/pii/S2352340918315191",
        "filenames": [
            "hotel_bookings.csv",
            "hotel_booking_demand.csv",
            "hotel-booking-demand.csv",
        ],
    },
    "hotel_reservations": {
        "display_name": "Hotel Reservations",
        "row_count_hint": 36275,
        "source_url": "https://www.kaggle.com/datasets/ahsan81/hotel-reservations-classification-dataset",
        "filenames": [
            "hotel_reservations.csv",
            "hotel_reservation.csv",
            "hotel-reservations.csv",
        ],
    },
}


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with normalized snake_case columns."""
    df = frame.copy()
    df.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        for column in df.columns
    ]
    return df


def _month_to_number(value: object) -> int:
    """Convert month names or integers to month number."""
    if pd.isna(value):
        return 1
    if isinstance(value, (int, float)):
        month = int(value)
        return min(max(month, 1), 12)

    text = str(value).strip()
    if text.isdigit():
        month = int(text)
        return min(max(month, 1), 12)

    for month in range(1, 13):
        if text.lower() in {
            calendar.month_name[month].lower(),
            calendar.month_abbr[month].lower(),
        }:
            return month
    return 1


def _coerce_numeric(series: pd.Series) -> pd.Series:
    """Convert a series to numeric and fill missing with zero."""
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _finalize_daily_frame(
    daily: pd.DataFrame,
    source_dataset: str,
    display_name: str,
    source_url: str,
) -> tuple[pd.DataFrame, dict]:
    """Convert aggregated daily booking data into hotel ops training data."""
    if daily.empty:
        raise ValueError(f"{display_name} 数据为空，无法生成训练样本。")

    ordered = daily.sort_values("date").reset_index(drop=True)
    full_dates = pd.date_range(ordered["date"].min(), ordered["date"].max(), freq="D")
    full = ordered.set_index("date").reindex(full_dates).rename_axis("date").reset_index()

    fill_zero_cols = [
        "booking_count",
        "occupied_bookings",
        "occupied_room_nights",
        "cancelled_bookings",
        "special_requests",
        "repeated_guests",
    ]
    for column in fill_zero_cols:
        full[column] = _coerce_numeric(full[column])

    full["avg_adr"] = pd.to_numeric(full["avg_adr"], errors="coerce")
    median_adr = float(full["avg_adr"].dropna().median()) if full["avg_adr"].notna().any() else 260.0
    full["avg_adr"] = full["avg_adr"].fillna(median_adr).clip(lower=120)

    daily_peak = float(full["occupied_bookings"].quantile(0.95))
    if daily_peak <= 0:
        daily_peak = max(float(full["booking_count"].quantile(0.95)), 1.0)
    capacity_proxy = max(daily_peak, 1.0)

    full["date"] = pd.to_datetime(full["date"])
    full["day_of_week"] = full["date"].dt.weekday
    full["month"] = full["date"].dt.month
    full["is_weekend"] = (full["day_of_week"] >= 5).astype(int)
    full["is_holiday"] = full["date"].apply(lambda item: int((item.month, item.day) in HOLIDAYS))
    full["occupancy_rate"] = (full["occupied_bookings"] / capacity_proxy).clip(0, 0.98).round(4)

    demand_threshold = float(full["booking_count"].quantile(0.8)) if full["booking_count"].max() > 0 else 0
    peak_month = full["month"].isin([5, 7, 8, 10]).astype(int)
    full["nearby_event"] = (
        (full["booking_count"] >= demand_threshold).astype(int) | (full["is_weekend"] & peak_month)
    ).astype(int)

    weather_base = full["month"].map({
        1: 2, 2: 2, 3: 3, 4: 4, 5: 4, 6: 5, 7: 5, 8: 4, 9: 4, 10: 3, 11: 2, 12: 2,
    })
    full["weather_score"] = (
        weather_base
        + (full["day_of_week"] == 5).astype(int)
        - (full["day_of_week"] == 1).astype(int)
    ).clip(1, 5)

    cancel_rate = (
        full["cancelled_bookings"] / (full["booking_count"] + 1e-6)
    ).clip(0, 0.95)
    full["cancellation_rate"] = cancel_rate.round(4)
    full["daily_revenue"] = (
        full["occupancy_rate"] * STANDARD_ROOM_COUNT * full["avg_adr"] * (1 + full["nearby_event"] * 0.04)
    ).round(0)
    full["review_score"] = (
        4.10
        + full["occupancy_rate"] * 0.38
        - cancel_rate * 0.22
        + (full["special_requests"] > 0).astype(int) * 0.03
    ).clip(3.4, 5.0).round(2)
    full["negative_rate"] = (
        0.11
        - full["occupancy_rate"] * 0.04
        + cancel_rate * 0.08
        + (full["weather_score"] <= 2).astype(int) * 0.01
    ).clip(0.01, 0.18).round(4)
    full["source_dataset"] = source_dataset

    output = full[
        [
            "date",
            "day_of_week",
            "month",
            "is_weekend",
            "is_holiday",
            "weather_score",
            "nearby_event",
            "booking_count",
            "cancelled_bookings",
            "special_requests",
            "repeated_guests",
            "avg_adr",
            "occupancy_rate",
            "daily_revenue",
            "cancellation_rate",
            "review_score",
            "negative_rate",
            "source_dataset",
        ]
    ].copy()
    output = output.rename(
        columns={
            "special_requests": "special_requests_count",
            "repeated_guests": "repeated_guests_count",
        }
    )

    metadata = {
        "name": source_dataset,
        "display_name": display_name,
        "source_url": source_url,
        "rows": int(len(output)),
        "date_range": [
            output["date"].min().strftime("%Y-%m-%d"),
            output["date"].max().strftime("%Y-%m-%d"),
        ],
        "room_count_standardized": STANDARD_ROOM_COUNT,
    }
    return output, metadata


def _preprocess_hotel_booking_demand(csv_path: str) -> tuple[pd.DataFrame, dict]:
    """Transform Hotel Booking Demand into daily hotel ops samples."""
    raw = _normalize_columns(pd.read_csv(csv_path))
    raw["arrival_month"] = raw["arrival_date_month"].apply(_month_to_number)
    raw["date"] = pd.to_datetime(
        {
            "year": _coerce_numeric(raw["arrival_date_year"]).astype(int),
            "month": _coerce_numeric(raw["arrival_month"]).astype(int),
            "day": _coerce_numeric(raw["arrival_date_day_of_month"]).astype(int).clip(lower=1, upper=28),
        },
        errors="coerce",
    )
    raw = raw.dropna(subset=["date"]).copy()
    raw["room_nights"] = _coerce_numeric(raw["stays_in_weekend_nights"]) + _coerce_numeric(raw["stays_in_week_nights"])
    raw["booking_count"] = 1
    raw["occupied_bookings"] = (1 - _coerce_numeric(raw["is_canceled"]).clip(0, 1)).astype(int)
    raw["occupied_room_nights"] = raw["room_nights"] * raw["occupied_bookings"]
    raw["cancelled_bookings"] = _coerce_numeric(raw["is_canceled"]).clip(0, 1)
    raw["special_requests"] = _coerce_numeric(raw["total_of_special_requests"])
    raw["repeated_guests"] = _coerce_numeric(raw["is_repeated_guest"]).clip(0, 1)
    raw["avg_adr"] = _coerce_numeric(raw["adr"]).replace(0, np.nan)
    if "hotel" not in raw.columns:
        raw["hotel"] = "hotel_booking_demand"
    else:
        raw["hotel"] = raw["hotel"].fillna("hotel_booking_demand")

    frames = []
    parts = []
    for hotel_name, group in raw.groupby("hotel"):
        daily = group.groupby("date", as_index=False).agg(
            booking_count=("booking_count", "sum"),
            occupied_bookings=("occupied_bookings", "sum"),
            occupied_room_nights=("occupied_room_nights", "sum"),
            cancelled_bookings=("cancelled_bookings", "sum"),
            special_requests=("special_requests", "sum"),
            repeated_guests=("repeated_guests", "sum"),
            avg_adr=("avg_adr", "median"),
        )
        source_key = f"hotel_booking_demand_{str(hotel_name).strip().lower().replace(' ', '_')}"
        prepared, meta = _finalize_daily_frame(
            daily=daily,
            source_dataset=source_key,
            display_name=f"Hotel Booking Demand ({hotel_name})",
            source_url=PUBLIC_DATASET_SPECS["hotel_booking_demand"]["source_url"],
        )
        frames.append(prepared)
        parts.append(meta)

    combined = pd.concat(frames, ignore_index=True)
    metadata = {
        "name": "hotel_booking_demand",
        "display_name": PUBLIC_DATASET_SPECS["hotel_booking_demand"]["display_name"],
        "source_url": PUBLIC_DATASET_SPECS["hotel_booking_demand"]["source_url"],
        "raw_rows": int(len(raw)),
        "prepared_rows": int(len(combined)),
        "subsets": parts,
    }
    return combined, metadata


def _preprocess_hotel_reservations(csv_path: str) -> tuple[pd.DataFrame, dict]:
    """Transform Hotel Reservations dataset into daily hotel ops samples."""
    raw = _normalize_columns(pd.read_csv(csv_path))
    raw["date"] = pd.to_datetime(
        {
            "year": _coerce_numeric(raw["arrival_year"]).astype(int),
            "month": _coerce_numeric(raw["arrival_month"]).astype(int).clip(lower=1, upper=12),
            "day": _coerce_numeric(raw["arrival_date"]).astype(int).clip(lower=1, upper=28),
        },
        errors="coerce",
    )
    raw = raw.dropna(subset=["date"]).copy()
    status = raw["booking_status"].astype(str).str.lower()
    is_canceled = status.str.contains("cancel") & ~status.str.contains("not")
    raw["booking_count"] = 1
    raw["occupied_bookings"] = (~is_canceled).astype(int)
    raw["room_nights"] = _coerce_numeric(raw["no_of_weekend_nights"]) + _coerce_numeric(raw["no_of_week_nights"])
    raw["occupied_room_nights"] = raw["room_nights"] * raw["occupied_bookings"]
    raw["cancelled_bookings"] = is_canceled.astype(int)
    raw["special_requests"] = _coerce_numeric(raw["no_of_special_requests"])
    raw["repeated_guests"] = _coerce_numeric(raw["repeated_guest"]).clip(0, 1)
    raw["avg_adr"] = _coerce_numeric(raw["avg_price_per_room"]).replace(0, np.nan)

    daily = raw.groupby("date", as_index=False).agg(
        booking_count=("booking_count", "sum"),
        occupied_bookings=("occupied_bookings", "sum"),
        occupied_room_nights=("occupied_room_nights", "sum"),
        cancelled_bookings=("cancelled_bookings", "sum"),
        special_requests=("special_requests", "sum"),
        repeated_guests=("repeated_guests", "sum"),
        avg_adr=("avg_adr", "median"),
    )
    prepared, subset_meta = _finalize_daily_frame(
        daily=daily,
        source_dataset="hotel_reservations",
        display_name="Hotel Reservations",
        source_url=PUBLIC_DATASET_SPECS["hotel_reservations"]["source_url"],
    )
    metadata = {
        "name": "hotel_reservations",
        "display_name": PUBLIC_DATASET_SPECS["hotel_reservations"]["display_name"],
        "source_url": PUBLIC_DATASET_SPECS["hotel_reservations"]["source_url"],
        "raw_rows": int(len(raw)),
        "prepared_rows": int(len(prepared)),
        "subsets": [subset_meta],
    }
    return prepared, metadata


PREPROCESSORS: dict[str, Callable[[str], tuple[pd.DataFrame, dict]]] = {
    "hotel_booking_demand": _preprocess_hotel_booking_demand,
    "hotel_reservations": _preprocess_hotel_reservations,
}


def _build_booking_demand_order_frame(csv_path: str) -> tuple[pd.DataFrame, dict]:
    """Create order-level cancellation samples from Hotel Booking Demand."""
    raw = _normalize_columns(pd.read_csv(csv_path))
    raw["arrival_month"] = raw["arrival_date_month"].apply(_month_to_number)
    raw["date"] = pd.to_datetime(
        {
            "year": _coerce_numeric(raw["arrival_date_year"]).astype(int),
            "month": _coerce_numeric(raw["arrival_month"]).astype(int),
            "day": _coerce_numeric(raw["arrival_date_day_of_month"]).astype(int).clip(lower=1, upper=28),
        },
        errors="coerce",
    )
    raw = raw.dropna(subset=["date"]).copy()

    adults = _coerce_numeric(raw["adults"])
    children = _coerce_numeric(raw["children"])
    babies = _coerce_numeric(raw["babies"])
    weekend_nights = _coerce_numeric(raw["stays_in_weekend_nights"])
    week_nights = _coerce_numeric(raw["stays_in_week_nights"])
    total_nights = weekend_nights + week_nights
    total_guests = adults + children + babies
    avg_price = _coerce_numeric(raw["adr"]).clip(lower=0)
    special_requests = _coerce_numeric(raw["total_of_special_requests"])
    previous_cancellations = _coerce_numeric(raw["previous_cancellations"])
    previous_bookings_not_canceled = _coerce_numeric(raw["previous_bookings_not_canceled"])
    hotel_type = raw.get("hotel", "City Hotel").astype(str).str.lower().str.contains("resort").astype(int)

    orders = pd.DataFrame({
        "date": raw["date"],
        "day_of_week": raw["date"].dt.weekday.astype(int),
        "month": raw["date"].dt.month.astype(int),
        "week_of_year": _coerce_numeric(raw["arrival_date_week_number"]).replace(0, np.nan).fillna(
            raw["date"].dt.isocalendar().week.astype(int)
        ).astype(int),
        "is_weekend": (raw["date"].dt.weekday >= 5).astype(int),
        "lead_time": _coerce_numeric(raw["lead_time"]),
        "weekend_nights": weekend_nights,
        "week_nights": week_nights,
        "total_nights": total_nights,
        "weekend_ratio": weekend_nights / (total_nights + 1),
        "adults": adults,
        "children": children,
        "babies": babies,
        "total_guests": total_guests,
        "family_flag": ((children + babies) > 0).astype(int),
        "avg_price": avg_price,
        "price_per_guest": (avg_price / total_guests.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan),
        "price_per_night": (avg_price / total_nights.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan),
        "special_requests": special_requests,
        "request_per_guest": (special_requests / total_guests.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan),
        "repeated_guest": _coerce_numeric(raw["is_repeated_guest"]).clip(lower=0, upper=1),
        "previous_cancellations": previous_cancellations,
        "previous_bookings_not_canceled": previous_bookings_not_canceled,
        "history_total": previous_cancellations + previous_bookings_not_canceled,
        "history_cancel_ratio": previous_cancellations / (previous_cancellations + previous_bookings_not_canceled + 1),
        "parking_spaces": _coerce_numeric(raw["required_car_parking_spaces"]),
        "hotel_type_code": hotel_type,
        "booking_changes": _coerce_numeric(raw["booking_changes"]),
        "days_in_waiting_list": _coerce_numeric(raw["days_in_waiting_list"]),
        "meal_plan": raw["meal"].apply(normalize_common_meal_plan),
        "market_segment": raw["market_segment"].apply(normalize_common_market_segment),
        "distribution_channel": raw["distribution_channel"].astype(str).str.strip().str.lower(),
        "deposit_type": raw["deposit_type"].astype(str).str.strip().str.lower(),
        "customer_type": raw["customer_type"].astype(str).str.strip().str.lower(),
        "room_type": raw["reserved_room_type"].apply(normalize_room_type),
        "is_canceled": _coerce_numeric(raw["is_canceled"]).clip(lower=0, upper=1).astype(int),
        "source_dataset": "hotel_booking_demand_orders",
    })
    orders["lead_time_bucket"] = orders["lead_time"].apply(build_lead_time_bucket)
    orders = orders.replace([np.inf, -np.inf], np.nan).fillna({
        "price_per_guest": 0,
        "price_per_night": 0,
        "request_per_guest": 0,
        "meal_plan": "unknown",
        "market_segment": "unknown",
        "distribution_channel": "unknown",
        "deposit_type": "unknown",
        "customer_type": "unknown",
        "room_type": "unknown",
        "lead_time_bucket": "unknown",
    }).fillna(0)

    metadata = {
        "name": "hotel_booking_demand_orders",
        "display_name": "Hotel Booking Demand Orders",
        "source_url": PUBLIC_DATASET_SPECS["hotel_booking_demand"]["source_url"],
        "rows": int(len(orders)),
        "positive_rate": round(float(orders["is_canceled"].mean()), 4),
    }
    return orders, metadata


def _build_reservations_order_frame(csv_path: str) -> tuple[pd.DataFrame, dict]:
    """Create order-level cancellation samples from Hotel Reservations."""
    raw = _normalize_columns(pd.read_csv(csv_path))
    raw["date"] = pd.to_datetime(
        {
            "year": _coerce_numeric(raw["arrival_year"]).astype(int),
            "month": _coerce_numeric(raw["arrival_month"]).astype(int).clip(lower=1, upper=12),
            "day": _coerce_numeric(raw["arrival_date"]).astype(int).clip(lower=1, upper=28),
        },
        errors="coerce",
    )
    raw = raw.dropna(subset=["date"]).copy()
    status = raw["booking_status"].astype(str).str.lower()
    is_canceled = (status.str.contains("cancel") & ~status.str.contains("not")).astype(int)

    adults = _coerce_numeric(raw["no_of_adults"])
    children = _coerce_numeric(raw["no_of_children"])
    babies = 0
    weekend_nights = _coerce_numeric(raw["no_of_weekend_nights"])
    week_nights = _coerce_numeric(raw["no_of_week_nights"])
    total_nights = weekend_nights + week_nights
    total_guests = adults + children
    avg_price = _coerce_numeric(raw["avg_price_per_room"]).clip(lower=0)
    special_requests = _coerce_numeric(raw["no_of_special_requests"])
    previous_cancellations = _coerce_numeric(raw["no_of_previous_cancellations"])
    previous_bookings_not_canceled = _coerce_numeric(raw["no_of_previous_bookings_not_canceled"])

    orders = pd.DataFrame({
        "date": raw["date"],
        "day_of_week": raw["date"].dt.weekday.astype(int),
        "month": raw["date"].dt.month.astype(int),
        "week_of_year": raw["date"].dt.isocalendar().week.astype(int),
        "is_weekend": (raw["date"].dt.weekday >= 5).astype(int),
        "lead_time": _coerce_numeric(raw["lead_time"]),
        "weekend_nights": weekend_nights,
        "week_nights": week_nights,
        "total_nights": total_nights,
        "weekend_ratio": weekend_nights / (total_nights + 1),
        "adults": adults,
        "children": children,
        "babies": babies,
        "total_guests": total_guests,
        "family_flag": (children > 0).astype(int),
        "avg_price": avg_price,
        "price_per_guest": (avg_price / total_guests.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan),
        "price_per_night": (avg_price / total_nights.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan),
        "special_requests": special_requests,
        "request_per_guest": (special_requests / total_guests.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan),
        "repeated_guest": _coerce_numeric(raw["repeated_guest"]).clip(lower=0, upper=1),
        "previous_cancellations": previous_cancellations,
        "previous_bookings_not_canceled": previous_bookings_not_canceled,
        "history_total": previous_cancellations + previous_bookings_not_canceled,
        "history_cancel_ratio": previous_cancellations / (previous_cancellations + previous_bookings_not_canceled + 1),
        "parking_spaces": _coerce_numeric(raw["required_car_parking_space"]),
        "hotel_type_code": 0,
        "booking_changes": 0,
        "days_in_waiting_list": 0,
        "meal_plan": raw["type_of_meal_plan"].apply(normalize_common_meal_plan),
        "market_segment": raw["market_segment_type"].apply(normalize_common_market_segment),
        "distribution_channel": "unknown",
        "deposit_type": "unknown",
        "customer_type": "unknown",
        "room_type": raw["room_type_reserved"].apply(normalize_room_type),
        "is_canceled": is_canceled,
        "source_dataset": "hotel_reservations_orders",
    })
    orders["lead_time_bucket"] = orders["lead_time"].apply(build_lead_time_bucket)
    orders = orders.replace([np.inf, -np.inf], np.nan).fillna({
        "price_per_guest": 0,
        "price_per_night": 0,
        "request_per_guest": 0,
        "meal_plan": "unknown",
        "market_segment": "unknown",
        "distribution_channel": "unknown",
        "deposit_type": "unknown",
        "customer_type": "unknown",
        "room_type": "unknown",
        "lead_time_bucket": "unknown",
    }).fillna(0)

    metadata = {
        "name": "hotel_reservations_orders",
        "display_name": "Hotel Reservations Orders",
        "source_url": PUBLIC_DATASET_SPECS["hotel_reservations"]["source_url"],
        "rows": int(len(orders)),
        "positive_rate": round(float(orders["is_canceled"].mean()), 4),
    }
    return orders, metadata


def _load_fallback_dataset() -> tuple[pd.DataFrame, dict]:
    """Load the local synthetic dataset kept for demo fallback."""
    fallback = pd.read_csv(FALLBACK_DATA_PATH)
    fallback["date"] = pd.to_datetime(fallback["date"])
    # Keep a synthetic cancellation proxy for development-only mode.
    fallback["cancellation_rate"] = (
        fallback["negative_rate"] * 1.8 + (1 - fallback["occupancy_rate"]) * 0.2
    ).clip(0.01, 0.55).round(4)
    fallback["source_dataset"] = "development_support_data"
    metadata = {
        "name": "development_support_data",
        "display_name": "开发联调数据",
        "source_url": "",
        "role": "development_only",
        "subsets": [
            {
                "name": "development_support_data",
                "display_name": "开发联调数据",
                "role": "development_only",
            }
        ],
    }
    return fallback, metadata


def list_available_external_datasets() -> list[dict]:
    """Inspect local external dataset directory and return matches."""
    matches = []
    os.makedirs(EXTERNAL_DATA_DIR, exist_ok=True)
    for dataset_key, spec in PUBLIC_DATASET_SPECS.items():
        matched_path = ""
        for filename in spec["filenames"]:
            candidate = os.path.join(EXTERNAL_DATA_DIR, filename)
            if os.path.exists(candidate):
                matched_path = candidate
                break
        matches.append(
            {
                "name": dataset_key,
                "display_name": spec["display_name"],
                "path": matched_path,
                "available": bool(matched_path),
                "row_count_hint": spec["row_count_hint"],
                "source_url": spec["source_url"],
            }
        )
    return matches


def load_training_dataset(mode: str = "official") -> tuple[pd.DataFrame, dict]:
    """Load official public datasets first, with optional development fallback."""
    frames = []
    metadata_sources = []
    external_matches = list_available_external_datasets()
    has_public_data = any(match["available"] for match in external_matches)

    for match in external_matches:
        if not match["available"]:
            continue
        prepared, metadata = PREPROCESSORS[match["name"]](match["path"])
        frames.append(prepared)
        metadata_sources.append(metadata)

    if not has_public_data or mode == "development":
        fallback_frame, fallback_meta = _load_fallback_dataset()
        frames.append(fallback_frame)
        metadata_sources.append(fallback_meta)

    if not frames:
        raise ValueError("未找到可用训练数据。请先放入公开数据集，或启用 development 模式。")

    combined = pd.concat(frames, ignore_index=True).sort_values(["source_dataset", "date"]).reset_index(drop=True)
    if has_public_data and any(item.get("role") == "development_only" for item in metadata_sources):
        raise ValueError("公开数据集训练模式下不应混入开发联调数据。")

    metadata = {
        "training_mode": "public_dataset_pipeline" if has_public_data and mode != "development" else "development_mode",
        "external_candidates": external_matches,
        "sources": metadata_sources,
        "prepared_source_count": int(len(metadata_sources)),
    }
    return combined, metadata


def load_cancellation_orders_dataset(mode: str = "official") -> tuple[pd.DataFrame, dict]:
    """Load order-level cancellation training data from public booking datasets."""
    external_matches = list_available_external_datasets()
    frames = []
    sources = []

    for match in external_matches:
        if not match["available"]:
            continue
        if match["name"] == "hotel_booking_demand":
            frame, metadata = _build_booking_demand_order_frame(match["path"])
        elif match["name"] == "hotel_reservations":
            frame, metadata = _build_reservations_order_frame(match["path"])
        else:
            continue
        frames.append(frame)
        sources.append(metadata)

    if not frames:
        if mode == "official":
            raise ValueError("订单级取消模型需要公开订单数据集，请先准备 external 目录下的公开 CSV。")
        fallback_frame, fallback_meta = _load_fallback_dataset()
        fallback_orders = pd.DataFrame({
            "date": fallback_frame["date"],
            "day_of_week": fallback_frame["date"].dt.weekday.astype(int),
            "month": fallback_frame["date"].dt.month.astype(int),
            "is_weekend": (fallback_frame["date"].dt.weekday >= 5).astype(int),
            "lead_time": 14,
            "weekend_nights": 1,
            "week_nights": 2,
            "adults": 2,
            "children": 0,
            "babies": 0,
            "total_guests": 2,
            "avg_price": 100,
            "special_requests": 1,
            "repeated_guest": 0,
            "previous_cancellations": 0,
            "previous_bookings_not_canceled": 0,
            "parking_spaces": 0,
            "hotel_type_code": 0,
            "is_canceled": (fallback_frame["cancellation_rate"] >= 0.15).astype(int),
            "source_dataset": "development_support_orders",
        })
        frames.append(fallback_orders)
        sources.append({
            "name": "development_support_orders",
            "display_name": "开发联调订单数据",
            "source_url": "",
            "rows": int(len(fallback_orders)),
            "positive_rate": round(float(fallback_orders["is_canceled"].mean()), 4),
            "role": "development_only",
        })

    combined = pd.concat(frames, ignore_index=True).reset_index(drop=True)
    metadata = {
        "training_mode": "public_order_cancellation_pipeline" if sources and not any(
            item.get("role") == "development_only" for item in sources
        ) else "development_order_cancellation_mode",
        "rows": int(len(combined)),
        "sources": sources,
    }
    return combined, metadata
