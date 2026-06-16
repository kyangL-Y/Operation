# -*- coding: utf-8 -*-
"""Cancellation feature schema and shared feature engineering helpers."""
from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

CANCELLATION_NUMERIC_FEATURES = [
    "day_of_week",
    "month",
    "week_of_year",
    "is_weekend",
    "lead_time",
    "weekend_nights",
    "week_nights",
    "total_nights",
    "weekend_ratio",
    "adults",
    "children",
    "babies",
    "total_guests",
    "family_flag",
    "avg_price",
    "price_per_guest",
    "price_per_night",
    "special_requests",
    "request_per_guest",
    "repeated_guest",
    "previous_cancellations",
    "previous_bookings_not_canceled",
    "history_total",
    "history_cancel_ratio",
    "parking_spaces",
    "hotel_type_code",
    "booking_changes",
    "days_in_waiting_list",
]

CANCELLATION_CATEGORICAL_FEATURES = [
    "meal_plan",
    "market_segment",
    "distribution_channel",
    "deposit_type",
    "customer_type",
    "room_type",
    "lead_time_bucket",
]

CANCELLATION_ORDER_FEATURES = CANCELLATION_NUMERIC_FEATURES + CANCELLATION_CATEGORICAL_FEATURES


def safe_ratio(numerator: object, denominator: object) -> float:
    """Return a stable ratio value for zero-heavy booking features."""
    numerator_value = float(pd.to_numeric(pd.Series([numerator]), errors="coerce").fillna(0).iloc[0])
    denominator_value = float(pd.to_numeric(pd.Series([denominator]), errors="coerce").fillna(0).iloc[0])
    if denominator_value <= 0:
        return 0.0
    return numerator_value / denominator_value


def normalize_common_meal_plan(value: object) -> str:
    """Map meal plans from different public datasets into a shared space."""
    text = str(value).strip().lower()
    if text in {"bb", "meal plan 1"}:
        return "basic"
    if text in {"hb", "fb", "meal plan 2", "meal plan 3"}:
        return "enhanced"
    if text in {"sc", "meal plan not selected", "not selected", "undefined"}:
        return "none"
    return text or "unknown"


def normalize_common_market_segment(value: object) -> str:
    """Map booking source segments from different datasets into shared buckets."""
    text = str(value).strip().lower()
    mapping = {
        "online ta": "online",
        "offline ta/to": "offline",
        "offline": "offline",
        "direct": "direct",
        "corporate": "corporate",
        "groups": "group",
        "group": "group",
        "complementary": "other",
        "aviation": "other",
    }
    return mapping.get(text, text or "unknown")


def normalize_room_type(value: object) -> str:
    """Return a stable room-type token."""
    text = str(value).strip().lower()
    if not text or text == "nan":
        return "unknown"
    return text


def build_lead_time_bucket(value: object) -> str:
    """Bucketize lead time for tree models and API fallbacks."""
    lead_time = int(max(float(pd.to_numeric(pd.Series([value]), errors="coerce").fillna(0).iloc[0]), 0))
    if lead_time <= 3:
        return "vshort"
    if lead_time <= 7:
        return "short"
    if lead_time <= 14:
        return "w1_2"
    if lead_time <= 30:
        return "m1"
    if lead_time <= 90:
        return "m3"
    if lead_time <= 180:
        return "m6"
    return "long"


def enrich_cancellation_feature_dict(raw_features: Mapping[str, object]) -> dict:
    """Expand a partial cancellation feature payload into the full training schema."""
    features = dict(raw_features)

    day_of_week = int(float(features.get("day_of_week", 0) or 0))
    month = int(float(features.get("month", 1) or 1))
    week_of_year = int(float(features.get("week_of_year", month * 4) or month * 4))
    is_weekend = int(float(features.get("is_weekend", 0) or 0))
    lead_time = float(features.get("lead_time", 14) or 14)
    weekend_nights = float(features.get("weekend_nights", 1 if is_weekend else 0) or 0)
    week_nights = float(features.get("week_nights", 2 if not is_weekend else 1) or 0)
    total_nights = float(features.get("total_nights", weekend_nights + week_nights) or 0)
    adults = float(features.get("adults", 2) or 0)
    children = float(features.get("children", 0) or 0)
    babies = float(features.get("babies", 0) or 0)
    total_guests = float(features.get("total_guests", adults + children + babies) or 0)
    special_requests = float(features.get("special_requests", 1) or 0)
    avg_price = float(features.get("avg_price", 680) or 0)
    previous_cancellations = float(features.get("previous_cancellations", 0) or 0)
    previous_bookings_not_canceled = float(features.get("previous_bookings_not_canceled", 0) or 0)

    enriched = {
        "day_of_week": day_of_week,
        "month": month,
        "week_of_year": week_of_year,
        "is_weekend": is_weekend,
        "lead_time": lead_time,
        "weekend_nights": weekend_nights,
        "week_nights": week_nights,
        "total_nights": total_nights,
        "weekend_ratio": float(features.get("weekend_ratio", safe_ratio(weekend_nights, total_nights + 1)) or 0),
        "adults": adults,
        "children": children,
        "babies": babies,
        "total_guests": total_guests,
        "family_flag": int(float(features.get("family_flag", 1 if (children + babies) > 0 else 0) or 0)),
        "avg_price": avg_price,
        "price_per_guest": float(features.get("price_per_guest", safe_ratio(avg_price, max(total_guests, 1))) or 0),
        "price_per_night": float(features.get("price_per_night", safe_ratio(avg_price, max(total_nights, 1))) or 0),
        "special_requests": special_requests,
        "request_per_guest": float(
            features.get("request_per_guest", safe_ratio(special_requests, max(total_guests, 1))) or 0
        ),
        "repeated_guest": float(features.get("repeated_guest", 0) or 0),
        "previous_cancellations": previous_cancellations,
        "previous_bookings_not_canceled": previous_bookings_not_canceled,
        "history_total": float(
            features.get("history_total", previous_cancellations + previous_bookings_not_canceled) or 0
        ),
        "history_cancel_ratio": float(
            features.get(
                "history_cancel_ratio",
                safe_ratio(previous_cancellations, previous_cancellations + previous_bookings_not_canceled + 1),
            )
            or 0
        ),
        "parking_spaces": float(features.get("parking_spaces", 0) or 0),
        "hotel_type_code": float(features.get("hotel_type_code", 0) or 0),
        "booking_changes": float(features.get("booking_changes", 0) or 0),
        "days_in_waiting_list": float(features.get("days_in_waiting_list", 0) or 0),
        "meal_plan": normalize_common_meal_plan(features.get("meal_plan", "basic")),
        "market_segment": normalize_common_market_segment(features.get("market_segment", "direct")),
        "distribution_channel": str(features.get("distribution_channel", "direct")).strip().lower() or "unknown",
        "deposit_type": str(features.get("deposit_type", "no deposit")).strip().lower() or "unknown",
        "customer_type": str(features.get("customer_type", "transient")).strip().lower() or "unknown",
        "room_type": normalize_room_type(features.get("room_type", "room_type_1")),
        "lead_time_bucket": build_lead_time_bucket(features.get("lead_time_bucket", lead_time)),
    }
    return enriched

