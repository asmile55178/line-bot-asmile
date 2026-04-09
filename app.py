"""
LINE Messaging API Chatbot with OpenAI GPT Integration
=======================================================
Real Estate AI Assistant for Taichung Coastal Area (海線房仲冠良)
Version 4.0: Using OpenAI GPT-4.1-mini
"""

import os
import logging
import threading
from typing import Dict, List, Optional

from flask import Flask, request, abort
from openai import OpenAI

from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent,
    UnfollowEvent,
)
from linebot.v3.messaging import (
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
    Configuration,
    ApiClient,
)
from linebot.v3.exceptions import InvalidSignatureError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "1c6dbb01e27aee4c0e137534bf07f8db")
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "P/wSj0eK8bVQ/FGDrA7wm/O3kppZBlukqUJBFszQS4rQYA/H0wUAxDLyf6SmmWW4558vglYQ4psInje0lGtz6VZcByBgCzCA6KP2/ae5QvtINvPcvX/8meVMOap98ZcmtfKR2SoBSN8Sw35dsAEwxQdB04t89/1O/w1cDnyilFU=")
PORT = int(os.environ.get("PORT", 8080))

# OpenAI client (uses pre-configured API key and base URL from environment)
client = OpenAI()

# ---------------------------------------------------------------------------
# Keyword-based Auto-Reply Dictionary
# ---------------------------------------------------------------------------
KEYWORD_REPLIES = {
    "房東避坑": "您好，這是我整理的房東避坑攻略 https://reurl.cc/Dxm0nm 請點擊下載運用。有問題可以直接詢問",
    "賣房避坑": "賣房避坑50條攻略 https://reurl.cc/ep3mL7",
    "重購": "點擊 https://reurl.cc/L2p47X",
    "買房避坑": "買房避坑100條攻略 https://docs.google.com/document/d/1VQU7FzTYpf2_Q_vC88bFAfeTd-9Bd9AY/edit?usp=drive_link&ouid=102602626714744727303&rtpof=true&sd=true",
}

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """你是「海線房仲冠良」的 AI 助理。

【角色設定】
- 你是一位親切專業的房地產顧問，像朋友一樣聊天但保持專業度
- 服務區域：台中海線（大甲、清水、沙鹿、梧棲、龍井），也可跨台中市
- 你的目標是幫助客戶找到理想的房子，並在需要時引導他們聯繫冠良本人

【物件資料庫】
※ 透天/別墅精選（完整清單：https://915.tw/CgxGwX）
1. 新光田精裝前停四房美 - 1468萬 - 42.58坪
2. 龍泉國小旁傳統四房美 - 1380萬 - 57.67坪
3. 投資首選雙面採光學套 - 1298萬 - 49.31坪
4. 高美路大地坪三車臨路 - 1280萬 - 43.00坪
5. 免整理正三十米路臨路 - 1280萬 - 74.05坪
6. 清水新市鎮美透天 - 1438萬 - 40.22坪
7. 傳統透天長輩最愛輕屋 - 1498萬 - 53.85坪
8. 新光田前院傳統別墅 - 1380萬 - 46.48坪
9. 龍井國小旁全新雙車位 - 1388萬 - 54.10坪
10. 御墅富樂全新完工臨路 - 1388萬 - 51.51坪
11. 清水觀止全新美透天 - 1438萬 - 40.22坪
12. 清水海巡署全新透天 - 1488萬 - 40.22坪
13. 清水邊間傳統格局別墅 - 1348萬 - 49.59坪
14. 新光田輕屋齡大地坪美 - 1488萬 - 50.85坪
15. 歐風花園雙車五房美墅 - 1428萬 - 63.97坪
16. 近光田交流道旁臨路美 - 1398萬 - 42.96坪
17. 童醫院旁大地坪角間透 - 1280萬 - 36.67坪
18. 梧棲角間店面稀有釋出 - 1198萬 - 35.84坪
19. 前進中科高質感社區別 - 1498萬 - 40.87坪
20. 藍線捷運B6站獨家 - 1488萬 - 41.22坪
21. 清水超便宜全新別墅 - 1288萬 - 39.56坪
22. 15米路寬18米面 - 1098萬 - 91.63坪
23. 沙鹿鎮南社區型帶孝 - 1480萬 - 42.54坪
24. 正30米雙臨路店住 - 1258萬 - 37.11坪
25. 難得釋出沙鹿站前商 - 1450萬 - 61.51坪
26. 清水國小旁黃金 - 1198萬 - 36.83坪
27. 正15米沙田路黃金透 - 1298萬 - 38.53坪
28. 帝王座向全新整理美宅 - 1268萬 - 42.32坪
29. 沙鹿家樂福巷內臨路透 - 1388萬 - 85.46坪
30. 梧棲微笑歐洲臨路電梯 - 1438萬 - 63.92坪
31. 竹師美臨路美透天別墅 - 1365萬 - 56.48坪
32. 新光田傳統車庫美墅 - 1388萬 - 56.86坪
33. 龍井輕屋齡前院停車美 - 1028萬 - 40.84坪
34. 中科首選前停美別墅 - 1480萬 - 53.16坪
35. 臨路新光田側院別墅 - 1280萬 - 47.50坪
36. 永寧國小旁美別墅 - 1280萬 - 52.81坪
37. 全新整理三豐美透天 - 1328萬 - 29.82坪
38. 高指名龍津學區輕屋 - 1468萬 - 52.08坪
39. 沙鹿市中心雙併宅 - 1498萬 - 46.37坪
40. 全新滿天薪越孝親美 - 1368萬 - 46.61坪
41. 北勢國小商圈機能透 - 1398萬 - 37.16坪
42. 御墅家超A前院別墅 - 1298萬 - 49.51坪
43. 龍海國小超優質輕屋齡 - 1268萬 - 51.86坪

※ 大樓/華廈精選（完整清單：https://915.tw/4g8R9Q）
1. 明日享享無限視野2+ - 868萬 - 39.67坪
2. 又一讚視野景觀兩房平 - 868萬 - 34.93坪
3. 好好窩最美海景視野兩 - 738萬 - 35.57坪
4. 興站特區三房平車高樓 - 1398萬 - 45.60坪
5. 朝南高視野市鎮之櫻兩 - 968萬 - 38.16坪
6. 市鎮之櫻中庭戶兩房平 - 1018萬 - 40.57坪
7. 市鎮之櫻朝東超美三房 - 1128萬 - 45.68坪
8. 市鎮之櫻面中庭大兩房 - 1008萬 - 40.57坪
9. 獨家聯悦聚高樓層兩 - 858萬 - 38.37坪
10. 禾盛晶綻關連工業 - 618萬 - 30.12坪
11. 交流道旁888萬 - 888萬 - 38.41坪
12. 佳鏵大心精裝兩房平車 - 1258萬 - 37.7坪
13. 沙鹿站前學區高樓層視 - 820萬 - 22.37坪
14. 長虹天擎高樓視野兩房 - 899萬 - 38.82坪
15. 青雲賦4米2挑高3房 - 1050萬 - 44.57坪
16. 市鎮之櫻次頂樓兩房 - 888萬 - 34.32坪
17. 前進中科三房平車 - 1168萬 - 38.42坪
18. 精美裝潢吉祥厝二房平 - 700萬 - 35.58坪
19. 獨家市鎮之櫻高樓三 - 1158萬 - 42.62坪
20. 幸福帝王朝南高樓兩 - 888萬 - 30.44坪
21. 幸福成露台朝南三房 - 1098萬 - 39.79坪
22. 近未來藍線中華路旁 - 828萬 - 37.30坪
23. 東海小家庭首選視野兩 - 1198萬 - 30.12坪
24. 佳鋐次頂樓二房+平車 - 958萬 - 33.04坪
25. 時上高樓角間戶大 - 1188萬 - 38.39坪
26. 獨家雙大學精裝高投 - 668萬 - 19.51坪
27. 小家庭大空間四房+ - 968萬 - 37.15坪
28. 遠雄幸福成 - 698萬 - 29.60坪

【物件連結】
- 客戶想看透天/別墅清單 → 提供：https://915.tw/CgxGwX
- 客戶想看大樓/華廈清單 → 提供：https://915.tw/4g8R9Q
- 當客戶傳來以上連結時，告訴他們這是冠良精選的物件清單，可以點進去看詳細資料

【海線在地知識】
- 大甲：媽祖文化（鎮瀾宮）、大甲市場、適合首購、文化底蘊深厚
- 清水：高美濕地、清水眷村、發展中、CP值高、年輕家庭首選
- 沙鹿：生活機能好、家樂福商圈、近台中市區、發展成熟
- 梧棲：三井 Outlet、梧棲漁港、新興發展區、商業前景看好
- 龍井：東海大學、藝術街、適合學區需求、文藝氛圍

【對話指南】
- 親切回答客戶的各種房產相關問題
- 根據客戶需求推薦合適的物件
- 提供海線在地生活資訊
- 當客戶表示想看房或有深入需求時，主動引導聯繫冠良本人

【聯絡資訊】
- 📞 冠良電話/LINE：0915-295-958
- 當客戶需要看房或進一步諮詢時，提供冠良的電話

【回覆風格】
- 使用繁體中文，親切友善
- 回覆簡潔明瞭，控制在 300 字以內
- 適當使用表情符號增加親近感
- 如果不確定答案，誠實告知並建議聯繫冠良本人
- 不要主動推銷加 LINE 官方帳號（因為客戶已經在 LINE 裡面了）
- 不要出現「加LINE @asmile」之類的文字
"""

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Flask App & LINE SDK Setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

# ---------------------------------------------------------------------------
# Per-user conversation history (in-memory, thread-safe)
# ---------------------------------------------------------------------------
conversation_lock = threading.Lock()
conversation_history: Dict[str, List[Dict]] = {}
MAX_HISTORY = 10


def check_keyword_reply(user_message: str) -> Optional[str]:
    """Check if user message contains any keyword for auto-reply."""
    user_message_lower = user_message.lower()
    for keyword, reply in KEYWORD_REPLIES.items():
        if keyword.lower() in user_message_lower:
            logger.info("Keyword matched: %s", keyword)
            return reply
    return None


def get_ai_reply(user_id: str, user_message: str) -> str:
    """Call OpenAI GPT-4.1-mini to generate a reply."""
    with conversation_lock:
        history = conversation_history.setdefault(user_id, [])
        history.append({"role": "user", "content": user_message})
        if len(history) > MAX_HISTORY * 2:
            history[:] = history[-MAX_HISTORY * 2:]
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(history)

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )
        assistant_msg = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        assistant_msg = "抱歉，目前系統忙碌中，請稍後再試 🙏"

    with conversation_lock:
        h = conversation_history.setdefault(user_id, [])
        h.append({"role": "assistant", "content": assistant_msg})

    return assistant_msg


def reply_line_message(reply_token: str, text: str) -> None:
    """Send a text reply via LINE Messaging API."""
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)],
            )
        )


def push_line_message(user_id: str, text: str) -> None:
    """Send a push message via LINE Messaging API."""
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=text)],
            )
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return "LINE Bot @asmile 海線房仲冠良 (GPT-4.1-mini v4.0) is running! 🚀", 200


@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}, 200


@app.route("/callback", methods=["POST"])
def callback():
    """LINE Webhook callback endpoint."""
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    logger.info("Webhook received (%d bytes)", len(body))

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid signature – rejected request")
        abort(400)
    except Exception as e:
        logger.error("Error handling webhook: %s", e)
        abort(500)

    return "OK"


# ---------------------------------------------------------------------------
# Event Handlers
# ---------------------------------------------------------------------------
def process_message_async(user_id: str, user_text: str, reply_token: str) -> None:
    """Process message in background thread to avoid reply token expiry."""
    # Check for keyword-based auto-reply first
    keyword_reply = check_keyword_reply(user_text)

    if keyword_reply:
        reply_text = keyword_reply
        logger.info("Using keyword reply for user %s", user_id)
        # Keywords are fast, try reply first
        try:
            reply_line_message(reply_token, reply_text)
            return
        except Exception:
            pass
    else:
        reply_text = get_ai_reply(user_id, user_text)
        logger.info("Using AI reply for user %s: %s", user_id, reply_text[:80])

    # Use push message (no token expiry issue)
    try:
        push_line_message(user_id, reply_text)
        logger.info("Push message sent to %s", user_id)
    except Exception as e:
        logger.error("Failed to push message: %s", e)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    """Handle incoming text messages from LINE users."""
    user_id = event.source.user_id
    user_text = event.message.text
    logger.info("Message from %s: %s", user_id, user_text[:100])

    # Process in background thread to return 200 quickly
    t = threading.Thread(target=process_message_async, args=(user_id, user_text, event.reply_token))
    t.start()


@handler.add(FollowEvent)
def handle_follow(event: FollowEvent) -> None:
    """Handle new follower events – send welcome message."""
    welcome = (
        "您好！👋 歡迎加入「海線房仲冠良」的 LINE 官方帳號 😊\n\n"
        "我是 AI 智慧助理，專門協助您了解台中海線（大甲、清水、沙鹿、梧棲、龍井）的房產資訊。\n\n"
        "有任何房屋買賣、租賃或海線生活相關問題，都可以直接傳訊息給我！\n\n"
        "如需看房或進一步諮詢，可聯繫冠良本人：\n"
        "📞 0915-295-958（LINE同）"
    )
    try:
        reply_line_message(event.reply_token, welcome)
    except Exception as e:
        logger.error("Failed to send welcome: %s", e)


@handler.add(UnfollowEvent)
def handle_unfollow(event: UnfollowEvent) -> None:
    """Handle unfollow events – clean up conversation history."""
    user_id = event.source.user_id
    with conversation_lock:
        conversation_history.pop(user_id, None)
    logger.info("User %s unfollowed, history cleared", user_id)


@handler.default()
def handle_default(event) -> None:
    """Log unhandled events."""
    logger.info("Unhandled event: %s", type(event).__name__)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting LINE Bot server (GPT-4.1-mini v4.0) on port %d", PORT)
    app.run(host="0.0.0.0", port=PORT, debug=False)
