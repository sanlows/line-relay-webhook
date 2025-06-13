
from fastapi import FastAPI, Request
import httpx
import openai
import os
import tempfile

app = FastAPI()

# ✉️ 你的 Google Apps Script Webhook（處理文字訊息）
GAS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzaAdyK9hYBiV-nr_Wvubi3_CJJjOgaJP0Yfao3sd0u5A1T5idWJniQF-p3P6M7PTt4qA/exec"

# 🔑 OpenAI API Key（建議從環境變數中讀取）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
LINE_TOKEN = os.getenv("LINE_CHANNEL_TOKEN", "ganIRVtULkft8djgQYLV5LRqathbFbRbR3WB7YT/12V8G10pXzOZ+yl/CJweIS4a2eZnH4YXtvjJimSG9dBq9s3ijSB7P1mhObfkQ6aGkNq1Huw6noyNYJDtei/AkbnjMzbvvn5AjJrMztQuUrO3cQdB04t89/1O/w1cDnyilFU=")
LINE_REPLY_ENDPOINT = "https://api.line.me/v2/bot/message/push"

openai.api_key = OPENAI_API_KEY


@app.post("/webhook")
async def relay_webhook(request: Request):
    """📨 接收 LINE 訊息並轉發給 Google Apps Script"""
    body = await request.body()
    headers = dict(request.headers)

    async with httpx.AsyncClient() as client:
        try:
            await client.post(GAS_WEBHOOK_URL, content=body, headers=headers)
        except Exception as e:
            print("❌ GAS webhook 轉發失敗：", e)

    return {"status": "ok"}


@app.post("/api/evaluate")
async def evaluate(request: Request):
    """
    🎧 語音分析 API：
    接收：audio_url, expected_sentence, user_id
    回傳：GPT 評語 → 傳給 LINE
    """
    data = await request.json()
    audio_url = data["audio_url"]
    expected_sentence = data["expected_sentence"]
    user_id = data["user_id"]

    # 🔽 下載語音內容
    headers = {"Authorization": "Bearer " + LINE_TOKEN}
    audio_resp = await httpx.AsyncClient().get(audio_url, headers=headers)
    audio_content = audio_resp.content

    # 🧠 Whisper 語音辨識
    with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as temp_audio:
        temp_audio.write(audio_content)
        temp_path = temp_audio.name

    with open(temp_path, "rb") as f:
        whisper_resp = openai.Audio.transcribe("whisper-1", f)

    os.remove(temp_path)
    spoken_text = whisper_resp["text"].strip()

    # ✍️ GPT 評語
    gpt_prompt = f"""
You are an English pronunciation coach.
The student was expected to say: "{expected_sentence}"
But they actually said: "{spoken_text}"

Please give feedback:
1. Transcription of what the student said.
2. Pronunciation score from 0 to 100.
3. Short comment on how to improve.
4. A friendly sentence to motivate the learner.
"""

    gpt_resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": gpt_prompt}]
    )
    reply = gpt_resp["choices"][0]["message"]["content"]

    # 📤 傳回 LINE
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": reply}]
    }

    await httpx.AsyncClient().post(
        LINE_REPLY_ENDPOINT,
        headers={
            "Authorization": "Bearer " + LINE_TOKEN,
            "Content-Type": "application/json"
        },
        json=payload
    )

    return {"status": "ok", "transcription": spoken_text}
