#!/usr/bin/env python3
"""Jev / System One 客服工单分流示例（Python ≥ 3.10，仅标准库）。

下载：curl -O https://typesafe-jev.com/examples/python/triage.py
运行方式：
    TYPESAFE_API_KEY=你的Key python3 triage.py      # 真实调用
    TYPESAFE_USE_FIXTURE=1 python3 triage.py        # 模拟响应（不联网）

本站未在浏览器中运行此脚本：API Key 只能出现在服务端环境变量中。
请求/响应字段依据官方 API 参考（docs.typesafe.ai/api，2026-09-22 核验）。
官方 SDK 为 `pip install typesafe-sdk`（typesafe-sdk），此处用标准库展示同一 HTTP 契约。
"""

import json
import os
import sys
import requests

API_URL = "https://api.typesafe.ai/v1/systemone"
USE_FIXTURE = os.environ.get("TYPESAFE_USE_FIXTURE") == "1"
API_KEY = os.environ.get("TYPESAFE_API_KEY", "")

# 与官方 Quick start 同一结构：state + model + questions（三类题型各一）。
PAYLOAD = {
    "model": "jev-latest",
    "state": (
        "Hi, I've been trying to connect my Stripe account for 3 days and the "
        "integration keeps failing. I'm losing sales. Please refund my "
        "subscription and help ASAP."
    ),
    "questions": {
        "department": {
            "type": "choice",
            "instructions": "Which team should handle this",
            "criteria": {
                "billing": "Payment or subscription issues",
                "technical": "Bugs or integration problems",
                "sales": "Pricing or account questions",
            },
        },
        "frustration": {
            "type": "score",
            "instructions": "How frustrated the customer appears",
            "criteria": [
                "Calm, just stating facts",
                "Frustrated but civil",
                "Very angry, strong language",
            ],
        },
        "asks_refund": {
            "type": "noul",
            "instructions": "The customer explicitly requests a refund",
        },
    },
}

# 固定 fixture：结构与官方文档示例响应一致，仅数值为模拟，用于无凭据时演示解析逻辑。
FIXTURE_RESPONSE = {
    "model": "jev-1.13.0",
    "answers": {
        "department": {
            "type": "choice",
            "choice": "technical",
            "confidence": 0.78,
            "probabilities": {
                "technical": 0.85,
                "sales": 0.0,
                "billing": 0.15,
            },
        },
        "frustration": {
            "type": "score",
            "score": 1.0,
            "confidence": 1.0,
            "legend": {
                0: "Calm, just stating facts",
                1: "Frustrated but civil",
                2: "Very angry, strong language",
            },
            "probabilities": {
                0: 0.0,
                1: 1.0,
                2: 0.0,
            },
        },
        "asks_refund": {
            "type": "noul",
            "noul": 0.91,
        },
    },
    "usage": {
        "input_tokens": 412,
        "output_tokens": 67,
    },
}

CONFIDENCE_THRESHOLD = 0.7
REFUND_AUTO = 0.9
REFUND_HUMAN = 0.5


def call_jev() -> dict:
    if USE_FIXTURE:
        print(
            "[SIMULATED] TYPESAFE_USE_FIXTURE=1 —— "
            "以下为固定 fixture，不是真实 API 调用。"
        )
        return FIXTURE_RESPONSE

    if not API_KEY:
        print(
            "缺少 TYPESAFE_API_KEY。设置它，或用 "
            "TYPESAFE_USE_FIXTURE=1 运行模拟。",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        response = requests.post(
            API_URL,
            json=PAYLOAD,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        response.raise_for_status()
        return response.json()

    except requests.HTTPError as error:
        status_code = (
            error.response.status_code
            if error.response is not None
            else "unknown"
        )

        response_text = (
            error.response.text
            if error.response is not None
            else str(error)
        )

        # 官方错误码：401 鉴权失败 / 422 请求校验失败 /
        # 429 限流 / 529 过载（应退避重试）。
        print(
            f"HTTP {status_code}: {response_text}",
            file=sys.stderr,
        )
        sys.exit(1)

    except requests.RequestException as error:
        print(
            f"Request error: {error}",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    result = call_jev()
    answers = result["answers"]
    department = answers["department"]
    frustration = answers["frustration"]
    asks_refund = answers["asks_refund"]

    print(f"model:            {result['model']}")
    print(
        f"department:       {department['choice']} "
        f"(confidence {department['confidence']})"
    )
    print(
        f"  probabilities:  "
        f"{json.dumps(department['probabilities'])}"
    )
    print(
        f"frustration:      {frustration['score']} "
        f"(confidence {frustration['confidence']})"
    )
    print(f"asks_refund:      {asks_refund['noul']}")
    print(f"usage:            {json.dumps(result['usage'])}")

    # 代码层分流：高置信度自动执行，中间段转人工。
    if department["confidence"] >= CONFIDENCE_THRESHOLD:
        route = f"auto-assign to {department['choice']}"
    else:
        route = "route to human triage (low confidence)"

    print(f"decision:         {route}")

    if asks_refund["noul"] >= REFUND_AUTO:
        refund_action = "create refund ticket automatically"
    elif asks_refund["noul"] >= REFUND_HUMAN:
        refund_action = "flag for human review of refund"
    else:
        refund_action = "no refund action"

    print(f"refund decision:  {refund_action}")


if __name__ == "__main__":
    main()
