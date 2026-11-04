"""Thai / English strings. tr(key, **fmt) returns the current language."""

S = {
    "app_title": ("iPhone Photo Import", "iPhone Photo Import"),
    "tagline": ("เสียบสาย iPhone แล้วดึงรูปลงคอมได้ทันที", "Plug in your iPhone and copy photos to this computer"),
    "lang_switch": ("English", "ภาษาไทย"),
    "offline": ("ทำงานในเครื่อง 100% ไม่ส่งรูปขึ้นอินเทอร์เน็ต", "100% offline — photos never leave this computer"),

    # waiting / connection states
    "wait_title": ("เสียบสาย iPhone เข้ากับคอมพิวเตอร์", "Plug your iPhone into this computer"),
    "wait_step1": ("ต่อสาย USB / Lightning / USB-C ระหว่าง iPhone กับคอม", "Connect the iPhone with its USB / Lightning / USB-C cable"),
    "wait_step2": ("ปลดล็อก iPhone แล้วกด \"เชื่อถือ\" (Trust) ถ้ามีถาม", "Unlock the iPhone and tap \"Trust\" if it asks"),
    "wait_step3": ("รอสักครู่ รูปจะขึ้นมาให้เลือกเอง", "Wait a moment — your photos appear here by themselves"),
    "searching": ("กำลังรอ iPhone…", "Waiting for an iPhone…"),
    "locked_title": ("ปลดล็อก iPhone ก่อนนะ", "Unlock your iPhone"),
    "locked_msg": ("เจอ \"{name}\" แล้ว ปลดล็อกหน้าจอ แล้วกด \"เชื่อถือ\" (Trust) บน iPhone",
                   "Found \"{name}\". Unlock the screen and tap \"Trust\" on the iPhone"),
    "loading_title": ("กำลังอ่านรายการรูป…", "Reading your photos…"),
    "loading_msg": ("เจอ \"{name}\" แล้ว ถ้ามีรูปเยอะอาจใช้เวลาสักครู่", "Found \"{name}\". This can take a moment if there are many photos"),
    "denied_title": ("ยังไม่ได้รับอนุญาตให้อ่านรูป", "Access to photos was not allowed"),
    "denied_msg": ("เปิด System Settings → Privacy & Security → Files & Folders (หรือ Photos) แล้วอนุญาตให้โปรแกรมนี้ จากนั้นเสียบสายใหม่",
                   "Open System Settings → Privacy & Security and allow this app, then plug the iPhone in again"),
    "nodriver_title": ("ยังไม่มีไดรเวอร์ของ Apple", "Apple's device driver is missing"),
    "nodriver_msg": ("ติดตั้งแอป \"Apple Devices\" (หรือ iTunes) จาก Microsoft Store แล้วเปิดโปรแกรมนี้ใหม่",
                     "Install the \"Apple Devices\" app (or iTunes) from the Microsoft Store, then restart this app"),
    "unsupported": ("ระบบนี้ยังไม่รองรับ (รองรับ Windows และ macOS)", "This system is not supported (Windows and macOS only)"),
    "disconnected": ("iPhone ถูกถอดออก", "The iPhone was unplugged"),

    # browsing
    "device_line": ("{photos} รูป · {videos} วิดีโอ บนเครื่อง", "{photos} photos · {videos} videos on the phone"),
    "p_today": ("วันนี้", "Today"),
    "p_week": ("7 วัน", "7 days"),
    "p_month": ("30 วัน", "30 days"),
    "p_all": ("ทั้งหมด", "All"),
    "show_videos": ("รวมวิดีโอ", "Include videos"),
    "hide_imported": ("ซ่อนรูปที่ดึงไปแล้ว", "Hide already imported"),
    "select_all": ("เลือกทั้งหมด", "Select all"),
    "select_none": ("ไม่เลือก", "Select none"),
    "selected": ("เลือก {n} จาก {total}", "{n} of {total} selected"),
    "empty_title": ("ไม่มีรูปในช่วงนี้", "No photos in this range"),
    "empty_hint": ("ลองเลือก \"7 วัน\" หรือ \"ทั้งหมด\" ด้านบน", "Try \"7 days\" or \"All\" above"),
    "imported_badge": ("ดึงแล้ว", "Imported"),
    "more_hint": ("แสดง {shown} จาก {total} รูป — กด \"เลือกทั้งหมด\" เพื่อเลือกครบทุกรูป",
                  "Showing {shown} of {total} — \"Select all\" selects every one"),

    # destination & options
    "save_to": ("บันทึกไว้ที่", "Save to"),
    "change": ("เปลี่ยน…", "Change…"),
    "open_folder": ("เปิดโฟลเดอร์", "Open folder"),
    "by_date": ("แยกโฟลเดอร์ตามวันที่ถ่าย", "One folder per day"),
    "to_jpg": ("แปลง HEIC เป็น JPG (เปิดใน Word ได้)", "Convert HEIC to JPG (opens in Word)"),
    "pick_folder": ("เลือกโฟลเดอร์ที่จะเก็บรูป", "Choose where to save photos"),
    "import_n": ("ดึง {n} รายการลงคอม", "Import {n} items"),
    "import_none": ("เลือกรูปที่ต้องการ", "Select photos to import"),

    # progress / result
    "importing": ("กำลังดึงรูป {done}/{total}", "Importing {done}/{total}"),
    "importing_file": ("{name}", "{name}"),
    "cancel": ("หยุด", "Stop"),
    "done_title": ("ดึงรูปเสร็จแล้ว 🎉", "All done 🎉"),
    "done_msg": ("ได้มา {n} ไฟล์ เก็บไว้ที่ {folder}", "Copied {n} files to {folder}"),
    "done_failed": ("มี {n} ไฟล์ที่ดึงไม่ได้: {names}", "{n} files could not be copied: {names}"),
    "done_cancel": ("หยุดแล้ว ดึงได้ {n} ไฟล์", "Stopped — {n} files copied"),
    "back": ("ดึงรูปเพิ่ม", "Import more"),
    "unplugged_during": ("iPhone ถูกถอดระหว่างดึงรูป", "The iPhone was unplugged during the import"),
    "reset_history": ("ล้างประวัติการดึงของเครื่องนี้", "Forget what was imported from this phone"),
}

_lang = 0  # 0 = Thai, 1 = English


def set_lang(code: str):
    global _lang
    _lang = 1 if code == "en" else 0


def lang() -> str:
    return "en" if _lang else "th"


def tr(key: str, **fmt) -> str:
    text = S.get(key, (key, key))[_lang]
    return text.format(**fmt) if fmt else text
