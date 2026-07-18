# คู่มือการติดตั้ง (ภาษาไทย)

ใช้งาน Claude Code ร่วมกับ NotebookLM ผ่านมือถือด้วย Telegram โดยทำตาม 5 ขั้นตอนนี้

## สิ่งที่ต้องเตรียม

บนคอมพิวเตอร์หรือ VPS ที่จะรันระบบ:

- **Python 3.10 ขึ้นไป**
- **Anthropic API key** ([console.anthropic.com](https://console.anthropic.com))
- บัญชี Google ที่เข้าถึงสมุดบันทึก **NotebookLM** ของคุณได้
- เบราว์เซอร์ **หนึ่งครั้ง** เพื่อล็อกอิน NotebookLM (`notebooklm login`) ทำบนโน้ตบุ๊กของคุณ
  แล้วค่อยคัดลอกเซสชันไปยังเซิร์ฟเวอร์ได้ (ดูขั้นที่ 4)

## 1. เตรียมระบบพื้นฐานบนคอมพิวเตอร์หรือ VPS

โคลนโปรเจกต์นี้และติดตั้งบนเครื่อง (PC หรือ VPS) ที่จะเปิดทิ้งไว้:

```bash
git clone <your-fork-url> claude4nblm && cd claude4nblm
pip install -e .
```

คำสั่งนี้จะติดตั้งตัวเชื่อมต่อ พร้อมกับ **Claude Agent SDK** (ซึ่งมาพร้อม Claude Code CLI ในตัว),
**python-telegram-bot** และ **`notebooklm-py`** (คำสั่ง `notebooklm`) โดย Claude จะเข้าถึง
NotebookLM ในฐานะแหล่งข้อมูล RAG ผ่านการเรียก CLI นี้ และมี skill ของ NotebookLM แถมมาที่
`.claude/skills/notebooklm/` เพื่อให้ Claude รู้จักคำสั่งต่าง ๆ

## 2. สร้าง Bot ใน Telegram (@BotFather)

1. เปิดแอป Telegram ค้นหาบัญชี **@BotFather** (สังเกตเครื่องหมายติ๊กถูกสีฟ้าทางการ)
2. พิมพ์คำสั่ง `/newbot`
3. ตั้ง **ชื่อ (Name)** และ **Username** โดย Username **ต้องลงท้ายด้วยคำว่า `bot` เสมอ**
   (เช่น `my_research_bot`)
4. เมื่อสร้างเสร็จ BotFather จะให้รหัส **API Token** มา ให้คัดลอกเก็บไว้ในที่ปลอดภัย

## 3. ติดตั้งและตั้งค่าในตัวเชื่อมต่อ

```bash
cp .env.example .env
```

แก้ไขไฟล์ `.env`:

- `TELEGRAM_BOT_TOKEN=` → วางรหัส Token จาก BotFather
- `ANTHROPIC_API_KEY=` → วาง Anthropic API key ของคุณ

หากต้องการ สามารถตั้งค่า `WORKDIR`, `NOTEBOOKLM_NOTEBOOK` หรือกำหนดสิทธิ์ล่วงหน้าด้วย
`ALLOWED_CHAT_IDS` ได้

### เข้าสู่ระบบ NotebookLM (ทำครั้งเดียว)

`notebooklm-py` ต้องใช้เซสชัน Google ให้ติดตั้งส่วนเสริมเบราว์เซอร์แล้วล็อกอินหนึ่งครั้ง
ระบบจะเปิดเบราว์เซอร์ให้คุณล็อกอิน Google จากนั้นเซสชันจะถูกบันทึกไว้ที่
`~/.notebooklm/profiles/default/storage_state.json`:

```bash
pip install "notebooklm-py[browser]"
notebooklm login
notebooklm list        # ทดสอบ: ควรแสดงรายการสมุดบันทึกของคุณ
```

ถ้าใช้ **VPS แบบ headless** ให้ล็อกอินบนโน้ตบุ๊กก่อนแล้วค่อยย้ายเซสชันไปเซิร์ฟเวอร์ — ดู
[vps-deployment.md](vps-deployment.md) (คัดลอก `storage_state.json` หรือนำเนื้อหาไปใส่ใน
`NOTEBOOKLM_AUTH_JSON`)

## 4. รีสตาร์ทและจับคู่ระบบ (Pairing)

เริ่มรันระบบ:

```bash
python -m claude4nblm
```

จะเห็นข้อความ **"Listening for channel messages…"** จากนั้นบนมือถือ:

1. เปิดแชตบอทที่เพิ่งสร้างใน Telegram แล้วพิมพ์ทักทาย เช่น `hi`
2. บอทจะส่ง **รหัสจับคู่ (Pairing code)** กลับมาในแชต
3. นำรหัสนั้นไปกรอกใน **Terminal** ของเครื่องที่รันระบบอยู่ แล้วกด Enter
4. บอทจะยืนยันว่า *"This chat is now authorized."* (แชตนี้ได้รับอนุญาตแล้ว)

เนื่องจากการอนุญาตต้องกรอกรหัสบนเครื่องโดยตรง จึงมีแต่คุณ — ผู้ควบคุมเครื่องนั้น —
เท่านั้นที่อนุญาตแชตได้ ช่วยป้องกันไม่ให้คนแปลกหน้าเข้ามาใช้งาน หากต้องการอนุญาตล่วงหน้า
โดยไม่ต้องจับคู่ ให้ใส่ Chat ID ของคุณในตัวแปร `ALLOWED_CHAT_IDS`

## 5. เริ่มสั่งงานผ่านมือถือ

พิมพ์คำสั่งหรือคำถามส่งเข้าไปในแชตได้เลย เช่น:

- *"แสดงรายการสมุดบันทึก NotebookLM ของฉัน"*
- *"ในสมุด 'วิทยานิพนธ์' ช่วยสรุปประเด็นหลักพร้อมการอ้างอิง"*
- *"อ่านไฟล์ report.md ในไดเรกทอรีงาน แล้วตรวจสอบกับสมุดบันทึกของฉัน"*

Claude จะใช้เครื่องมือ NotebookLM ดึงคำตอบที่อ้างอิงจากแหล่งข้อมูลจริงและตอบกลับมาในแชต
Telegram ใช้คำสั่ง `/reset` เพื่อเริ่มบทสนทนาใหม่

สำหรับการเปิดใช้งานตลอด 24 ชั่วโมง ดูที่ **[vps-deployment.md](vps-deployment.md)**
