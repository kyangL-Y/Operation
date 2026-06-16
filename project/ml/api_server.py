# -*- coding: utf-8 -*-
"""酒店运营支持系统 - ML API 服务
提供：入住率预测 / 营收预测 / 订单取消风险预测 / 决策分析 / 语义检索 / RAG 问答
端口：5000
"""
import json
import os

import joblib
import numpy as np
import pandas as pd
import requests as http_req
from flask import Flask, jsonify, request

from cancellation_features import CANCELLATION_ORDER_FEATURES, enrich_cancellation_feature_dict

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
for proxy_key in [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
]:
    os.environ[proxy_key] = ""
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

app = Flask(__name__)

BASE = os.path.dirname(__file__)


def load_joblib_model(filename):
    """Load a trained model if present; otherwise keep the demo service runnable."""
    model_path = os.path.join(BASE, "models", filename)
    try:
        return joblib.load(model_path)
    except FileNotFoundError:
        print(f"[WARN] {filename} not found, prediction API will use heuristic fallback.")
    except Exception as exc:
        print(f"[WARN] {filename} load failed, prediction API will use heuristic fallback: {exc}")
    return None


print("[1/5] Loading occupancy prediction model...")
occ_model = load_joblib_model("rf_occupancy.joblib")
DAILY_BASE_FEATURES = [
    "day_of_week",
    "month",
    "is_weekend",
    "is_holiday",
    "weather_score",
    "nearby_event",
    "occ_lag1",
    "occ_lag7",
    "occ_roll7",
    "rev_lag1",
    "rev_lag7",
    "rev_roll7",
    "cancel_lag1",
    "cancel_lag7",
    "cancel_roll7",
    "adr_lag1",
    "adr_lag7",
    "adr_roll7",
    "booking_lag1",
    "booking_lag7",
    "booking_roll7",
    "request_lag1",
    "request_lag7",
    "request_roll7",
    "repeat_guest_lag1",
    "repeat_guest_lag7",
    "repeat_guest_roll7",
    "review_lag1",
    "review_lag7",
    "review_roll7",
    "negative_lag1",
    "negative_lag7",
    "negative_roll7",
    "occ_roll14",
    "occ_roll30",
    "rev_roll14",
    "weekend_event",
    "holiday_event",
    "occ_rev_ratio",
    "weather_weekend",
    "month_sin",
    "month_cos",
    "dow_sin",
    "dow_cos",
    "occ_trend",
    "rev_trend",
]
OCC_FEATURES = DAILY_BASE_FEATURES

print("[2/5] Loading revenue prediction model...")
rev_model = load_joblib_model("rf_revenue.joblib")
REV_FEATURES = DAILY_BASE_FEATURES

print("[3/5] Loading cancellation prediction model...")
cancel_model = load_joblib_model("rf_cancellation.joblib")
CANCEL_FEATURES = CANCELLATION_ORDER_FEATURES

print("[4/5] Loading text2vec embedding model...")
try:
    if SentenceTransformer is None:
        raise ImportError("sentence_transformers is not installed")
    try:
        # Prefer local cached weights to avoid startup failures in restricted networks.
        embed_model = SentenceTransformer(
            "shibing624/text2vec-base-chinese",
            local_files_only=True,
        )
        embedding_mode = "text2vec"
    except Exception as local_exc:
        print(f"[INFO] 本地缓存不可用，尝试在线加载 text2vec: {local_exc}")
        embed_model = SentenceTransformer("shibing624/text2vec-base-chinese")
        embedding_mode = "text2vec"
except Exception as exc:
    embed_model = None
    embedding_mode = "keyword_fallback"
    print(f"[WARN] text2vec 加载失败，已降级为关键词检索: {exc}")

print("[5/5] Initializing decision engine...")
kb_store = []  # [{id, title, content, embedding}]

MIN_RAG_SCORE = 0.3


def first_non_empty(*values):
    """Return the first non-empty environment-style value."""
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def build_chat_completions_url(base_url: str) -> str:
    """Normalize a provider base URL into a chat-completions endpoint."""
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


CHAT_API_KEY = first_non_empty(
    os.environ.get("CHAT_API_KEY"),
    os.environ.get("OPENAI_API_KEY"),
    os.environ.get("DEEPSEEK_API_KEY"),
)
CHAT_BASE_URL = first_non_empty(
    os.environ.get("CHAT_BASE_URL"),
    os.environ.get("OPENAI_BASE_URL"),
    os.environ.get("DEEPSEEK_BASE_URL"),
    "https://api.deepseek.com",
)
CHAT_MODEL = first_non_empty(
    os.environ.get("CHAT_MODEL"),
    os.environ.get("OPENAI_MODEL"),
    os.environ.get("DEEPSEEK_MODEL"),
    "deepseek-chat",
)
CHAT_COMPLETIONS_URL = build_chat_completions_url(CHAT_BASE_URL)

print("\nAll models loaded.")
print(
    "Generation API key: "
    + ("configured" if CHAT_API_KEY else "NOT SET (export OPENAI_API_KEY / CHAT_API_KEY=...)")
)
print(f"Generation model: {CHAT_MODEL if CHAT_API_KEY else 'template_fallback'}")
print(f"Embedding mode: {embedding_mode}")


def current_retrieval_mode():
    return "text2vec" if embed_model is not None else "keyword_fallback"


def current_generation_mode():
    return CHAT_MODEL if CHAT_API_KEY else "template_fallback"


def build_status_payload():
    return {
        "retrievalMode": current_retrieval_mode(),
        "generationMode": current_generation_mode(),
        "generationProvider": "openai_compatible" if CHAT_API_KEY else "template_fallback",
        "generationModel": CHAT_MODEL if CHAT_API_KEY else "",
        "knowledgeCount": len(kb_store),
        "deepseekConfigured": bool(CHAT_API_KEY),
    }


def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Auth-Token"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.after_request
def after_request(resp):
    return add_cors(resp)


def validate_features(features, required_fields):
    missing = [field for field in required_fields if field not in features]
    if missing:
        return False, missing
    return True, []


def safe_float(value, default=0.0):
    """Convert an incoming value into float with graceful fallback."""
    if value is None:
        return float(default)
    try:
        return float(value)
    except Exception:
        return float(default)


def enrich_daily_feature_dict(raw_features):
    """Expand partial daily prediction features into the full training schema."""
    features = dict(raw_features or {})
    day_of_week = int(safe_float(features.get("day_of_week"), 0))
    month = int(safe_float(features.get("month"), 1))
    is_weekend = int(safe_float(features.get("is_weekend"), 0))
    is_holiday = int(safe_float(features.get("is_holiday"), 0))
    weather_score = safe_float(features.get("weather_score"), 4)
    nearby_event = int(safe_float(features.get("nearby_event"), 0))

    occ_lag1 = safe_float(features.get("occ_lag1"), safe_float(features.get("occupancy_rate"), 0.8))
    occ_lag7 = safe_float(features.get("occ_lag7"), occ_lag1)
    occ_roll7 = safe_float(features.get("occ_roll7"), (occ_lag1 + occ_lag7) / 2.0)
    occ_roll14 = safe_float(features.get("occ_roll14"), occ_roll7)
    occ_roll30 = safe_float(features.get("occ_roll30"), occ_roll7)

    rev_lag1 = safe_float(features.get("rev_lag1"), safe_float(features.get("daily_revenue"), 120000))
    rev_lag7 = safe_float(features.get("rev_lag7"), rev_lag1)
    rev_roll7 = safe_float(features.get("rev_roll7"), (rev_lag1 + rev_lag7) / 2.0)
    rev_roll14 = safe_float(features.get("rev_roll14"), rev_roll7)

    cancel_lag1 = safe_float(features.get("cancel_lag1"), safe_float(features.get("cancellation_rate"), 0.16))
    cancel_lag7 = safe_float(features.get("cancel_lag7"), cancel_lag1)
    cancel_roll7 = safe_float(features.get("cancel_roll7"), (cancel_lag1 + cancel_lag7) / 2.0)

    adr_lag1 = safe_float(features.get("adr_lag1"), safe_float(features.get("avg_price"), 668))
    adr_lag7 = safe_float(features.get("adr_lag7"), adr_lag1)
    adr_roll7 = safe_float(features.get("adr_roll7"), (adr_lag1 + adr_lag7) / 2.0)

    booking_lag1 = safe_float(features.get("booking_lag1"), occ_lag1 * 120.0)
    booking_lag7 = safe_float(features.get("booking_lag7"), occ_lag7 * 120.0)
    booking_roll7 = safe_float(features.get("booking_roll7"), occ_roll7 * 120.0)

    request_lag1 = safe_float(features.get("request_lag1"), safe_float(features.get("special_requests"), 1) * 35.0)
    request_lag7 = safe_float(features.get("request_lag7"), request_lag1)
    request_roll7 = safe_float(features.get("request_roll7"), (request_lag1 + request_lag7) / 2.0)

    repeat_guest_lag1 = safe_float(features.get("repeat_guest_lag1"), 10.0)
    repeat_guest_lag7 = safe_float(features.get("repeat_guest_lag7"), repeat_guest_lag1)
    repeat_guest_roll7 = safe_float(features.get("repeat_guest_roll7"), (repeat_guest_lag1 + repeat_guest_lag7) / 2.0)

    review_lag1 = safe_float(features.get("review_lag1"), safe_float(features.get("review_score"), 4.4))
    review_lag7 = safe_float(features.get("review_lag7"), review_lag1)
    review_roll7 = safe_float(features.get("review_roll7"), (review_lag1 + review_lag7) / 2.0)

    negative_lag1 = safe_float(features.get("negative_lag1"), safe_float(features.get("negative_rate"), 0.06))
    negative_lag7 = safe_float(features.get("negative_lag7"), negative_lag1)
    negative_roll7 = safe_float(features.get("negative_roll7"), (negative_lag1 + negative_lag7) / 2.0)

    enriched = dict(features)
    enriched.update(
        {
            "day_of_week": day_of_week,
            "month": month,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday,
            "weather_score": weather_score,
            "nearby_event": nearby_event,
            "occ_lag1": occ_lag1,
            "occ_lag7": occ_lag7,
            "occ_roll7": occ_roll7,
            "rev_lag1": rev_lag1,
            "rev_lag7": rev_lag7,
            "rev_roll7": rev_roll7,
            "cancel_lag1": cancel_lag1,
            "cancel_lag7": cancel_lag7,
            "cancel_roll7": cancel_roll7,
            "adr_lag1": adr_lag1,
            "adr_lag7": adr_lag7,
            "adr_roll7": adr_roll7,
            "booking_lag1": booking_lag1,
            "booking_lag7": booking_lag7,
            "booking_roll7": booking_roll7,
            "request_lag1": request_lag1,
            "request_lag7": request_lag7,
            "request_roll7": request_roll7,
            "repeat_guest_lag1": repeat_guest_lag1,
            "repeat_guest_lag7": repeat_guest_lag7,
            "repeat_guest_roll7": repeat_guest_roll7,
            "review_lag1": review_lag1,
            "review_lag7": review_lag7,
            "review_roll7": review_roll7,
            "negative_lag1": negative_lag1,
            "negative_lag7": negative_lag7,
            "negative_roll7": negative_roll7,
            "occ_roll14": occ_roll14,
            "occ_roll30": occ_roll30,
            "rev_roll14": rev_roll14,
            "weekend_event": safe_float(features.get("weekend_event"), is_weekend * nearby_event),
            "holiday_event": safe_float(features.get("holiday_event"), is_holiday * nearby_event),
            "occ_rev_ratio": safe_float(features.get("occ_rev_ratio"), occ_lag1 * rev_lag1 / 10000.0),
            "weather_weekend": safe_float(features.get("weather_weekend"), weather_score * is_weekend),
            "month_sin": safe_float(features.get("month_sin"), np.sin(2 * np.pi * month / 12.0)),
            "month_cos": safe_float(features.get("month_cos"), np.cos(2 * np.pi * month / 12.0)),
            "dow_sin": safe_float(features.get("dow_sin"), np.sin(2 * np.pi * day_of_week / 7.0)),
            "dow_cos": safe_float(features.get("dow_cos"), np.cos(2 * np.pi * day_of_week / 7.0)),
            "occ_trend": safe_float(features.get("occ_trend"), occ_lag1 - occ_lag7),
            "rev_trend": safe_float(features.get("rev_trend"), rev_lag1 - rev_lag7),
        }
    )
    return enriched


def keyword_score(query: str, content: str) -> float:
    """Fallback retrieval score using bigram tokenization for better Chinese matching."""
    def bigrams(text: str):
        t = text.lower().strip()
        return {t[i:i+2] for i in range(len(t) - 1)} if len(t) >= 2 else set(t)
    query_tokens = bigrams(query)
    content_tokens = bigrams(content)
    if not query_tokens or not content_tokens:
        return 0.0
    overlap = len(query_tokens & content_tokens)
    return round(overlap / max(len(query_tokens), 1), 4)


def heuristic_occupancy_prediction(features) -> float:
    """Estimate occupancy when the serialized model cannot run."""
    latest_occ = safe_float(features.get("occ_lag1"), safe_float(features.get("occ_roll7"), 0.78))
    occ_lag7 = safe_float(features.get("occ_lag7"), latest_occ)
    is_weekend = safe_float(features.get("is_weekend"), 0.0)
    is_holiday = safe_float(features.get("is_holiday"), 0.0)
    nearby_event = safe_float(features.get("nearby_event"), 0.0)
    review_score = safe_float(features.get("review_lag1"), safe_float(features.get("review_roll7"), 4.4))
    negative_rate = safe_float(features.get("negative_lag1"), safe_float(features.get("negative_roll7"), 0.06))

    trend = latest_occ - occ_lag7
    prediction = (
        latest_occ
        + trend * 0.35
        + is_weekend * 0.025
        + is_holiday * 0.03
        + nearby_event * 0.02
        + (review_score - 4.4) * 0.04
        - negative_rate * 0.25
    )
    return float(np.clip(prediction, 0.35, 0.98))


def heuristic_revenue_prediction(features) -> float:
    """Estimate revenue when the serialized model cannot run."""
    rev_lag1 = safe_float(features.get("rev_lag1"), safe_float(features.get("rev_roll7"), 120000.0))
    occ_lag1 = max(safe_float(features.get("occ_lag1"), 0.78), 0.35)
    predicted_occ = heuristic_occupancy_prediction(features)
    adr_lag1 = safe_float(features.get("adr_lag1"), safe_float(features.get("avg_price"), 980.0))
    request_lag1 = safe_float(features.get("request_lag1"), safe_float(features.get("request_roll7"), 42.0))
    review_score = safe_float(features.get("review_lag1"), safe_float(features.get("review_roll7"), 4.4))
    negative_rate = safe_float(features.get("negative_lag1"), safe_float(features.get("negative_roll7"), 0.06))

    occ_factor = predicted_occ / occ_lag1
    event_factor = (
        1.0
        + safe_float(features.get("is_weekend"), 0.0) * 0.04
        + safe_float(features.get("is_holiday"), 0.0) * 0.06
        + safe_float(features.get("nearby_event"), 0.0) * 0.03
    )
    demand_factor = 1.0 + min(request_lag1 / 300.0, 0.08)
    quality_factor = 1.0 + max((review_score - 4.4) * 0.03, -0.05) - negative_rate * 0.2
    baseline = max(rev_lag1 * occ_factor * event_factor * demand_factor * quality_factor, adr_lag1 * 65.0)
    return float(np.clip(baseline, rev_lag1 * 0.75, rev_lag1 * 1.4))


def heuristic_cancellation_prediction(features) -> float:
    """Estimate cancellation probability when the serialized model cannot run."""
    base_rate = safe_float(features.get("cancel_lag1"), safe_float(features.get("cancel_roll7"), 0.12))
    lead_time = safe_float(features.get("lead_time"), 18.0)
    is_weekend = safe_float(features.get("is_weekend"), 0.0)
    is_holiday = safe_float(features.get("is_holiday"), 0.0)
    nearby_event = safe_float(features.get("nearby_event"), 0.0)
    previous_cancellations = safe_float(features.get("previous_cancellations"), 0.0)
    repeated_guest = safe_float(features.get("repeat_guest_lag1"), safe_float(features.get("repeated_guest"), 0.0))
    deposit_type = str(features.get("deposit_type", "")).lower()

    prediction = (
        base_rate
        + min(lead_time / 365.0, 0.06)
        + is_weekend * 0.012
        + is_holiday * 0.015
        + nearby_event * 0.01
        + min(previous_cancellations, 3.0) * 0.02
        - min(repeated_guest, 12.0) * 0.002
    )
    if "non" in deposit_type and "refund" in deposit_type:
        prediction -= 0.03
    return float(np.clip(prediction, 0.01, 0.45))


def predict_numeric(model, features, required_fields, round_digits=4, fallback_fn=None):
    is_valid, missing = validate_features(features, required_fields)
    if not is_valid:
        return None, missing, "validation_error"
    row = pd.DataFrame([{field: features[field] for field in required_fields}])
    vector = np.array([[features[field] for field in required_fields]])
    errors = []
    try:
        prediction = model.predict(row)[0]
        return round(float(prediction), round_digits), [], "model"
    except Exception as exc:
        errors.append(f"dataframe:{exc}")
    try:
        prediction = model.predict(vector)[0]
        return round(float(prediction), round_digits), [], "model"
    except Exception as exc:
        errors.append(f"ndarray:{exc}")
    if fallback_fn is None:
        raise RuntimeError("; ".join(errors))
    app.logger.warning("Numeric model prediction failed, fallback engaged: %s", " | ".join(errors))
    prediction = fallback_fn(features)
    return round(float(prediction), round_digits), [], "heuristic_fallback"


def predict_probability(model, features, required_fields, round_digits=4, fallback_fn=None):
    """Return a probability-like output for cancellation prediction."""
    is_valid, missing = validate_features(features, required_fields)
    if not is_valid:
        return None, missing, "validation_error"
    row = pd.DataFrame([{field: features[field] for field in required_fields}])
    vector = np.array([[features[field] for field in required_fields]])
    errors = []
    try:
        if hasattr(model, "predict_proba"):
            prediction = model.predict_proba(row)[0][1]
        else:
            prediction = model.predict(row)[0]
        prediction = float(np.clip(prediction, 0.0, 1.0))
        return round(prediction, round_digits), [], "model"
    except Exception as exc:
        errors.append(f"dataframe:{exc}")
    try:
        if hasattr(model, "predict_proba"):
            prediction = model.predict_proba(vector)[0][1]
        else:
            prediction = model.predict(vector)[0]
        prediction = float(np.clip(prediction, 0.0, 1.0))
        return round(prediction, round_digits), [], "model"
    except Exception as exc:
        errors.append(f"ndarray:{exc}")
    if fallback_fn is None:
        raise RuntimeError("; ".join(errors))
    app.logger.warning("Probability model prediction failed, fallback engaged: %s", " | ".join(errors))
    prediction = float(np.clip(fallback_fn(features), 0.0, 1.0))
    return round(prediction, round_digits), [], "heuristic_fallback"


@app.route("/api/occupancy/predict", methods=["POST", "OPTIONS"])
def predict_occupancy():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json() or {}
    features = enrich_daily_feature_dict(data.get("features", {}))
    prediction, missing, prediction_mode = predict_numeric(
        occ_model,
        features,
        OCC_FEATURES,
        round_digits=4,
        fallback_fn=heuristic_occupancy_prediction,
    )
    if missing:
        return jsonify({"code": 400, "message": f"Missing features: {missing}"}), 400
    return jsonify({
        "code": 200,
        "data": {
            "predicted_occupancy": prediction,
            "features_used": OCC_FEATURES,
            "prediction_mode": prediction_mode,
        },
    })


@app.route("/api/revenue/predict", methods=["POST", "OPTIONS"])
def predict_revenue():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json() or {}
    features = enrich_daily_feature_dict(data.get("features", {}))
    prediction, missing, prediction_mode = predict_numeric(
        rev_model,
        features,
        REV_FEATURES,
        round_digits=0,
        fallback_fn=heuristic_revenue_prediction,
    )
    if missing:
        return jsonify({"code": 400, "message": f"Missing features: {missing}"}), 400
    return jsonify({
        "code": 200,
        "data": {
            "predicted_revenue": prediction,
            "features_used": REV_FEATURES,
            "prediction_mode": prediction_mode,
        },
    })


@app.route("/api/cancellation/predict", methods=["POST", "OPTIONS"])
def predict_cancellation():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json() or {}
    features = enrich_cancellation_feature_dict(data.get("features", {}))
    prediction, missing, prediction_mode = predict_probability(
        cancel_model,
        features,
        CANCEL_FEATURES,
        round_digits=4,
        fallback_fn=heuristic_cancellation_prediction,
    )
    if missing:
        return jsonify({"code": 400, "message": f"Missing features: {missing}"}), 400
    return jsonify({
        "code": 200,
        "data": {
            "predicted_cancellation_rate": prediction,
            "features_used": CANCEL_FEATURES,
            "prediction_mode": prediction_mode,
        },
    })


def semantic_search(query, top_k=3):
    if not kb_store:
        return []
    scored = []
    if embed_model is not None:
        q_emb = embed_model.encode([query], normalize_embeddings=True)[0]
        for doc in kb_store:
            sim = float(np.dot(q_emb, doc["embedding"]))
            scored.append({
                "id": doc["id"],
                "title": doc["title"],
                "content": doc["content"],
                "score": round(sim, 4),
            })
    else:
        for doc in kb_store:
            sim = keyword_score(query, f"{doc['title']} {doc['content']}")
            scored.append({
                "id": doc["id"],
                "title": doc["title"],
                "content": doc["content"],
                "score": sim,
            })
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def build_query_plan(question):
    normalized = (question or "").strip()
    if not normalized:
        return []
    variants = [
        normalized,
        f"处理流程 {normalized}",
        f"{normalized} 处理流程",
        f"{normalized} 值班经理检查项",
    ]
    seen = set()
    return [item for item in variants if item and not (item in seen or seen.add(item))]


def retrieve_deep_context(question, top_k=5):
    query_plan = build_query_plan(question)
    merged = {}
    for index, query in enumerate(query_plan):
        hits = semantic_search(query, top_k=3)
        weight = max(1.0, 1.2 - index * 0.1)
        for hit in hits:
            doc_id = str(hit.get("id", ""))
            score = round(float(hit.get("score", 0)) * weight, 4)
            current = merged.get(doc_id)
            if current is None:
                merged[doc_id] = {
                    "id": hit.get("id"),
                    "title": hit.get("title"),
                    "score": score,
                    "matched_queries": [query],
                    "snippet": str(hit.get("content", ""))[:220],
                }
                continue
            current["score"] = round(float(current.get("score", 0)) + score, 4)
            current["matched_queries"] = sorted(set(current.get("matched_queries", []) + [query]))
            snippet = str(hit.get("content", ""))[:220]
            if len(snippet) > len(current.get("snippet", "")):
                current["snippet"] = snippet
    citations = sorted(merged.values(), key=lambda item: item.get("score", 0), reverse=True)[:top_k]
    search_depth = "high" if len(citations) >= 3 else "medium" if citations else "low"
    confidence = "高" if len(citations) >= 4 else "中" if citations else "低"
    return {
        "queryPlan": query_plan,
        "citations": citations,
        "searchDepth": search_depth,
        "confidence": confidence,
    }


def build_deep_search_answer(question, query_plan, citations):
    if not citations:
        return "未检索到足够相关的分析依据，建议补充处理流程、岗位协同或异常处置资料后重试。"
    lines = ["已按深度搜索模式聚合知识证据，建议优先关注以下内容："]
    for item in citations:
        title = item.get("title", "未命名文档")
        snippet = item.get("snippet", "")
        matched = "、".join(item.get("matched_queries", []))
        lines.append(f"- {title}：{snippet}")
        if matched:
            lines.append(f"  命中检索：{matched}")
    lines.append("建议先核对证据，再由值班经理拆分岗位执行动作。")
    return "\n".join(lines)


def build_rag_context(hits):
    """Build a text context block from either raw hits or deep-search citations."""
    return "\n\n".join(
        [
            f"[文档{i + 1}] {hit.get('title', '未命名文档')}\n"
            f"{hit.get('content') or hit.get('snippet') or ''}"
            for i, hit in enumerate(hits)
        ]
    )


def default_suggestions():
    return [
        "请把结论拆成岗位执行清单",
        "请补充值班经理复盘要点",
        "如果今天入住率承压，这个方案如何与渠道和价格联动？",
    ]


def build_rag_payload(answer, citations, query_plan, search_depth, confidence, mode, source, retrieval_hits=None):
    payload = {
        "answer": answer,
        "citations": citations,
        "suggestions": default_suggestions(),
        "queryPlan": query_plan,
        "searchDepth": search_depth,
        "confidence": confidence,
        "mode": mode,
        "source": source,
    }
    payload.update(build_status_payload())
    if retrieval_hits is not None:
        payload["search_results"] = retrieval_hits
    return payload


def extract_chat_message_content(message: object) -> str:
    """Read string content from OpenAI-compatible message payloads."""
    if isinstance(message, str):
        return message
    if not isinstance(message, dict):
        return str(message)
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(str(item.get("text", "")))
            else:
                chunks.append(str(item))
        return "".join(chunks)
    return str(content)


def call_chat_completion(messages):
    resp = http_req.post(
        CHAT_COMPLETIONS_URL,
        timeout=30,
        headers={
            "Authorization": f"Bearer {CHAT_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": CHAT_MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 512,
        },
    )
    resp.raise_for_status()
    payload = resp.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("chat completions response missing choices")
    message = choices[0].get("message", {})
    return extract_chat_message_content(message)


def generate_rag_answer(question, hits, mode):
    context = build_rag_context(hits) or "当前没有高置信度资料命中，请基于酒店运营管理通用经验给出稳健建议。"
    if not CHAT_API_KEY:
        answer = "根据知识库检索结果，建议如下：\n"
        for hit in hits:
            content = hit.get("content") or hit.get("snippet") or ""
            answer += f"- {content[:200]}\n"
        answer += "\n（提示：配置问答服务密钥后可获得更完整的生成式回答）"
        return answer, "template-fallback"

    user_prompt = question if mode == "standard" else f"请按深度搜索方式回答，并综合多条证据：{question}"
    try:
        answer = call_chat_completion([
            {
                "role": "system",
                "content": (
                    "你是一个面向酒店管理层的运营支持助手。请优先参考以下资料回答问题；"
                    "如果资料不足或相关度较低，可以基于酒店运营管理通用经验给出稳健、可执行的建议，"
                    "但不要声称这些通用建议来自资料库。请先给出结论，再拆分为岗位动作和复盘要点。\n\n"
                    f"参考资料：\n{context}"
                ),
            },
            {"role": "user", "content": user_prompt},
        ])
        return answer, CHAT_MODEL
    except Exception as exc:
        answer = f"问答生成暂未成功，已切换为资料检索回答：{str(exc)}\n\n"
        for hit in hits:
            content = hit.get("content") or hit.get("snippet") or ""
            answer += f"- {content[:200]}\n"
        return answer, "template-fallback"


def decision_rules(metrics):
    current_occ = float(metrics.get("current_occupancy", 0))
    predicted_occ = float(metrics.get("predicted_occupancy", current_occ))
    current_revenue = float(metrics.get("current_revenue", 0))
    predicted_revenue = float(metrics.get("predicted_revenue", current_revenue))
    current_cancellation = float(metrics.get("current_cancellation_rate", 0))
    predicted_cancellation = float(metrics.get("predicted_cancellation_rate", current_cancellation))
    review_score = float(metrics.get("review_score", 0))
    negative_rate = float(metrics.get("negative_rate", 0))
    is_holiday = int(metrics.get("is_holiday", 0))
    nearby_event = int(metrics.get("nearby_event", 0))

    occ_delta = predicted_occ - current_occ
    rev_delta = predicted_revenue - current_revenue
    cancel_delta = predicted_cancellation - current_cancellation
    causes = []
    actions = []
    level = "stable"

    if occ_delta <= -0.05:
        level = "warning"
        causes.append("未来入住率预计明显回落，存在房量利用不足风险。")
        actions.append("优先检查房价策略、OTA 库存曝光和周边活动投放。")
    elif occ_delta >= 0.05:
        causes.append("未来入住率预计上升，可提前安排排班与客房准备。")
        actions.append("提前锁定保洁排班和高峰接待资源，避免前台拥堵。")

    if rev_delta <= -10000:
        level = "warning"
        causes.append("营收预测低于当前水平，单房收益和客源结构需要重点排查。")
        actions.append("联动渠道价格策略，核查是否存在高折扣低收益订单。")
    elif rev_delta >= 10000:
        causes.append("营收预测上升，可提前准备高价值客户接待与增购服务。")
        actions.append("推动早餐、延迟退房、房型升级等附加销售。")

    if predicted_cancellation >= 0.25 or cancel_delta >= 0.03:
        level = "warning" if level == "stable" else level
        causes.append("订单取消风险预测上升，后续到店转化存在下滑风险。")
        actions.append("对高风险订单分层二次确认，优化限时优惠与担保策略。")
    elif predicted_cancellation <= 0.12:
        causes.append("订单取消风险较低，订单稳定性处于可控区间。")

    if negative_rate >= 0.08:
        level = "critical"
        causes.append("差评率偏高，服务质量波动可能影响复购和品牌口碑。")
        actions.append("优先排查保洁响应、隔音投诉和前台高峰时段服务。")

    if review_score <= 4.2:
        level = "warning" if level == "stable" else level
        causes.append("综合评分偏低，说明客户体验存在持续性问题。")
        actions.append("安排值班经理复盘高频投诉，并更新一线服务处理流程。")

    if nearby_event == 1:
        causes.append("周边活动将提升客流波动，预测结果受临时需求放大影响。")
        actions.append("结合活动高峰预留房量，并准备临时应急服务话术。")

    if is_holiday == 1:
        causes.append("节假日因素会放大客流和投诉并发，需要更强的现场调度。")
        actions.append("安排节假日值守方案，并提前同步投诉处理和换房预案。")

    if not causes:
        causes.append("核心指标整体平稳，暂无明显经营异常。")
        actions.append("维持当前排班与房价策略，持续观察评分和差评率变化。")

    summary = (
        f"风险等级：{level}；入住率预测变化 {occ_delta:+.2%}；"
        f"营收预测变化 {rev_delta:+.0f} 元；订单取消风险变化 {cancel_delta:+.2%}。"
    )
    return {
        "risk_level": level,
        "summary": summary,
        "root_causes": causes,
        "recommended_actions": actions,
    }


@app.route("/api/decision/analyze", methods=["POST", "OPTIONS"])
def analyze_decision():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json() or {}
    metrics = data.get("metrics", {})
    if not metrics:
        return jsonify({"code": 400, "message": "metrics is required"}), 400
    decision = decision_rules(metrics)
    return jsonify({"code": 200, "data": decision})


@app.route("/api/knowledge/index", methods=["POST", "OPTIONS"])
def index_knowledge():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json() or {}
    docs = data.get("documents", [])
    if not docs:
        return jsonify({"code": 400, "message": "documents is required"}), 400

    texts = [doc.get("content", "") for doc in docs]
    embeddings = embed_model.encode(texts, normalize_embeddings=True) if embed_model is not None else [None] * len(docs)

    for index, doc in enumerate(docs):
        entry = {
            "id": doc.get("id", str(index + 1)),
            "title": doc.get("title", ""),
            "content": doc.get("content", ""),
            "embedding": embeddings[index],
        }
        kb_store[:] = [item for item in kb_store if item["id"] != entry["id"]]
        kb_store.append(entry)

    return jsonify({"code": 200, "data": {"indexed": len(docs), "total": len(kb_store)}})


@app.route("/api/search/semantic", methods=["POST", "OPTIONS"])
def search_semantic():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json() or {}
    query = data.get("query", "")
    top_k = data.get("top_k", 3)
    results = semantic_search(query, top_k)
    return jsonify({"code": 200, "data": {"query": query, "results": results}})


@app.route("/api/rag/answer", methods=["POST", "OPTIONS"])
def rag_answer():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json() or {}
    question = data.get("question", "")
    if not question:
        return jsonify({"code": 400, "message": "question is required"}), 400

    hits = semantic_search(question, top_k=3)
    citations = [{"id": hit["id"], "title": hit["title"], "score": hit["score"]} for hit in hits]

    answer, source = generate_rag_answer(question, hits, "standard")
    top_score = hits[0]["score"] if hits else 0
    confidence = "高" if source != "template-fallback" and top_score >= 0.6 else "中"
    return jsonify({
        "code": 200,
        "data": build_rag_payload(
            answer,
            citations,
            [question],
            "standard" if top_score >= MIN_RAG_SCORE else "low",
            confidence,
            "standard",
            source,
            hits,
        ),
    })


@app.route("/api/rag/deep-search", methods=["POST", "OPTIONS"])
def rag_deep_search():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json() or {}
    question = data.get("question", "")
    if not question:
        return jsonify({"code": 400, "message": "question is required"}), 400

    deep_context = retrieve_deep_context(question, top_k=5)
    query_plan = deep_context.get("queryPlan", [])
    citations = deep_context.get("citations", [])
    if not citations:
        answer, source = generate_rag_answer(question, [], "deep-search")
        return jsonify({
            "code": 200,
            "data": build_rag_payload(
                answer,
                [],
                query_plan,
                "low",
                "中" if source != "template-fallback" else "低",
                "deep-search",
                source,
            ),
        })

    retrieval_hits = [{
        "id": item.get("id"),
        "title": item.get("title"),
        "score": item.get("score"),
        "matched_queries": item.get("matched_queries", []),
        "snippet": item.get("snippet", ""),
    } for item in citations]
    answer, source = generate_rag_answer(question, citations, "deep-search")
    confidence = deep_context.get("confidence", "中")
    if source == "template-fallback" and confidence == "高":
        confidence = "中"

    return jsonify({
        "code": 200,
        "data": build_rag_payload(
            answer,
            citations,
            query_plan,
            deep_context.get("searchDepth", "medium"),
            confidence,
            "deep-search",
            source,
            retrieval_hits,
        ),
    })


@app.route("/api/health", methods=["GET"])
def health():
    status = build_status_payload()
    return jsonify({
        "code": 200,
        "data": {
            "status": "running",
            "models": [
                "occupancy(RandomForest)",
                "revenue(RandomForest)",
                "cancellation(RandomForestProbability)",
                "decision-engine(rule-based)",
                f"retrieval({status['retrievalMode']})",
            ],
            "knowledgeCount": len(kb_store),
            "deepseek": bool(CHAT_API_KEY),
            "retrievalMode": status["retrievalMode"],
            "generationMode": status["generationMode"],
            "deepseekConfigured": status["deepseekConfigured"],
        },
    })


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Hotel Ops ML API Server")
    print("=" * 50)
    print("Endpoints:")
    print("  POST /api/occupancy/predict   - 入住率预测")
    print("  POST /api/revenue/predict     - 营收预测")
    print("  POST /api/cancellation/predict - 订单取消风险预测")
    print("  POST /api/decision/analyze    - 决策分析")
    print("  POST /api/knowledge/index     - 知识库索引")
    print("  POST /api/search/semantic     - 语义检索")
    print("  POST /api/rag/answer          - RAG 问答")
    print("  POST /api/rag/deep-search     - RAG 深度搜索")
    print("  GET  /api/health              - 健康检查")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)
