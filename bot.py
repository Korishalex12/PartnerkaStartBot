import json, os, time, urllib.parse, urllib.request
from pathlib import Path

TOKEN=os.environ["BOT_TOKEN"]
STAR_PRICE=int(os.getenv("STAR_PRICE","700"))
PDF=Path(os.getenv("PDF_PATH","partnerka_s_nulya_pervyy_zapusk.pdf"))
TERMS_URL=os.getenv("TERMS_URL","https://example.com/terms")
SUPPORT=os.getenv("SUPPORT_TEXT","По вопросам оплаты и доступа: @YOUR_USERNAME")
API=f"https://api.telegram.org/bot{TOKEN}/"
PAYLOAD="partnerka_course_v1"

def call(method,data=None,files=None):
    data=data or {}
    if files:
        boundary="----TG"
        parts=[]
        for k,v in data.items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        for k,(name,content,mime) in files.items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{name}\"\r\nContent-Type: {mime}\r\n\r\n".encode()+content+b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        req=urllib.request.Request(API+method,b"".join(parts),headers={"Content-Type":f"multipart/form-data; boundary={boundary}"})
    else:
        req=urllib.request.Request(API+method,urllib.parse.urlencode(data).encode())
    with urllib.request.urlopen(req,timeout=45) as r: return json.loads(r.read())

def msg(cid,text,kb=None):
    d={"chat_id":cid,"text":text}
    if kb:d["reply_markup"]=json.dumps(kb,ensure_ascii=False)
    return call("sendMessage",d)

def invoice(cid):
    return call("sendInvoice",{"chat_id":cid,"title":"Партнёрка с нуля — Первый запуск",
        "description":"Практический мини-курс для новичков по партнёрскому маркетингу.",
        "payload":PAYLOAD,"provider_token":"","currency":"XTR",
        "prices":json.dumps([{"label":"Мини-курс","amount":STAR_PRICE}])})

def deliver(cid):
    return call("sendDocument",{"chat_id":cid,"caption":"🎓 Спасибо за покупку! Вот ваш мини-курс «Партнёрка с нуля — Первый запуск»."},
        {"document":(PDF.name,PDF.read_bytes(),"application/pdf")})

def handle(u):
    if "pre_checkout_query" in u:
        q=u["pre_checkout_query"]
        ok=q.get("invoice_payload")==PAYLOAD and q.get("currency")=="XTR" and q.get("total_amount")==STAR_PRICE
        d={"pre_checkout_query_id":q["id"],"ok":"true" if ok else "false"}
        if not ok:d["error_message"]="Не удалось подтвердить заказ. Начните покупку заново."
        call("answerPreCheckoutQuery",d); return
    if "callback_query" in u:
        q=u["callback_query"]; call("answerCallbackQuery",{"callback_query_id":q["id"]})
        cid=q["message"]["chat"]["id"]; a=q["data"]
        if a=="buy": invoice(cid)
        elif a=="inside": msg(cid,"📚 5 уроков + 10 Telegram-шаблонов, сообщения клиентам, таблица учёта и чек-лист.")
        elif a=="terms": msg(cid,f"📜 Условия покупки: цифровой PDF выдаётся после успешной оплаты.\n\n{TERMS_URL}")
        else: msg(cid,SUPPORT)
        return
    m=u.get("message",{}); cid=m.get("chat",{}).get("id")
    if not cid:return
    p=m.get("successful_payment")
    if p:
        if p.get("invoice_payload")==PAYLOAD:
            msg(cid,"✅ Оплата подтверждена. Отправляю курс.")
            deliver(cid)
        return
    text=(m.get("text") or "").strip()
    if text.startswith("/start"):
        kb={"inline_keyboard":[[{"text":f"💳 Купить курс — {STAR_PRICE} ⭐","callback_data":"buy"}],
            [{"text":"📋 Что внутри","callback_data":"inside"},{"text":"📜 Условия","callback_data":"terms"}],
            [{"text":"🆘 Поддержка","callback_data":"support"}]]}
                                
        msg(cid,"👋 Привет!\n\n🚀 «Партнёрка для новичков»",kb)
    elif text=="/paysupport": msg(cid,SUPPORT)
    else: msg(cid,"Используйте /start.")

def main():
    offset=0
    while True:
        try:
            r=call("getUpdates",{"timeout":50,"offset":offset})
            for u in r.get("result",[]):
                offset=u["update_id"]+1; handle(u)
        except Exception as e:
            print("ERROR",e); time.sleep(3)
if __name__=="__main__": main()
