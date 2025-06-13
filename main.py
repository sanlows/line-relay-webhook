# LINE Webhook Relay Server (FastAPI)
# ✅ 接收 LINE webhook → 回覆 200 → 轉送到 Google Apps Script 與 Whisper+GPT

from fastapi import FastAPI, Request
import httpx
import os

app = FastAPI()

# 你的 Google Apps Script Webhook
gas_webhook_url = "https://script.google.com/macros/s/AKfycbzaAdyK9hYBiV-nr_Wvubi3_CJJjOgaJP0Yfao3sd0u5A1T5idWJniQF-p3P6M7PTt4qA/exec"

# Colab Whisper + GPT 的 URL（可選）
colab_whisper_api = "https://a49b-34-91-10-233.ngrok-free.app/api/evaluate"

@app.post("/webhook")
async def relay_webhook(request: Request):
    body = await request.body()
    headers = dict(request.headers)

    # 轉發給你的 GAS webhook
    async with httpx.AsyncClient() as client:
        try:
            await client.post(gas_webhook_url, content=body, headers=headers)
        except Exception as e:
            print("GAS 轉發失敗：", e)

    return {"status": "ok"}

@app.post("/relay_eval")
async def relay_eval(request: Request):
    data = await request.json()
    async with httpx.AsyncClient() as client:
        resp = await client.post(colab_whisper_api, json=data)
        return resp.json()
