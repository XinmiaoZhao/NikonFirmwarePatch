"""Frozen 36-language title table for the vrotate menu row (T6).

The table is the user-confirmed verbatim baseline of 2026-11-08,
transcribed from docs/t14-video-orientation-re.md §7 "用户确认的 36
语言行标题表" (outer repo); any deviation from that table is a spec
defect.  The strings were originally derived offline from the official
stock strings (provenance notes below) and then corrected against the
confirmed baseline in the slots where the user's wording differs:

* Base string: official id 2458 "Record camera orientation" -- the photo
  menu row with the same function, translated by Nikon into all 36 slots.
* Per language, the camera/photo word is swapped for that language's video
  word taken from official id 2214 "Video quality (N-RAW)": e.g. en
  camera->video, de Kamera->Video (hyphen kept), zh-CN 照相机->视频,
  zh-TW 相機->短片, ko 카메라->동영상, th กล้อง->วิดีโอ, sv kamera->film.
* Japanese builds its own phrase with the 動画の prefix on the stock words:
  動画の縦横位置情報の記録.  Slots 25/26/28-31/35 are Japanese fallbacks in
  the stock language directory and repeat slot 0.
* Confirmed-baseline wording overrides the mechanical derivation in slots
  11 (ru drops "при записи"), 14 (pt "do vídeo"), 21 (hu plain-o "Video"),
  22 (el "Καταγρ. προσανατ." with periods and the fuller word), 32 (bg "на
  видеото"), 33 (hr "videa") and 34 (ar الفيديو and no trailing RLM).

Every glyph is drawn from the same language's own stock strings (ids 2458
and 2214 among them); z8vrotate.patcher.strings() re-proves that against
the firmware at build time.
"""
import hashlib

# Language slots: 0=ja,1=en,2=de,3=fr,4=es,5=it,6=sv,7=nl,8=zh-CN,9=zh-TW,
# 10=ko,11=ru,12=th,13=id,14=pt,15=pl,16=fi,17=da,18=no,19=cs,20=tr,21=hu,
# 22=el,23=ro,24=uk,25/26/28-31/35=ja fallback,27=hi,32=bg,33=hr,34=ar.
JAPANESE_SLOTS = (0, 25, 26, 28, 29, 30, 31, 35)

TITLES = (
    '動画の縦横位置情報の記録',            # 0  ja
    'Record video orientation',           # 1  en
    'Video-Ausrichtung speichern',        # 2  de
    'Enreg. orientation vidéo',           # 3  fr
    'Grabar orientación vídeo',           # 4  es
    'Registra orient. video',             # 5  it
    'Spara filmorientering',              # 6  sv
    'Videorichting vastleggen',           # 7  nl
    '记录视频方向',                        # 8  zh-CN
    '記錄短片方向',                        # 9  zh-TW
    '동영상 방향 기록',                    # 10 ko
    'Ориентация видео',                  # 11 ru (confirmed table)
    'บันทึกมุมวิดีโอ',                   # 12 th
    'Rekam orientasi film',               # 13 id
    'Gravar orientação do vídeo',         # 14 pt (confirmed table)
    'Rejestruj orientację video',         # 15 pl
    'Tallenna videon suunta',             # 16 fi
    'Optag videoretning',                 # 17 da
    'Registrer filmretning',              # 18 no
    'Záznam orientace videa',             # 19 cs
    'Video yönünü kaydet',                # 20 tr
    'Video tájolásának rögzítése',        # 21 hu (confirmed table)
    'Καταγρ. προσανατ. video',            # 22 el (confirmed table)
    'Înregistrare orientare video',       # 23 ro
    'Зберігати орієнт. відео',            # 24 uk
    '動画の縦横位置情報の記録',            # 25 ja fallback
    '動画の縦横位置情報の記録',            # 26 ja fallback
    'वीडियो समन्वयन रिकॉर्ड करें',          # 27 hi
    '動画の縦横位置情報の記録',            # 28 ja fallback
    '動画の縦横位置情報の記録',            # 29 ja fallback
    '動画の縦横位置情報の記録',            # 30 ja fallback
    '動画の縦横位置情報の記録',            # 31 ja fallback
    'Запис ориент. на видеото',           # 32 bg (confirmed table)
    'Smer snimanja videa',                # 33 hr (confirmed table)
    'تسجيل اتجاه الفيديو',                 # 34 ar (confirmed table; no RLM)
    '動画の縦横位置情報の記録',            # 35 ja fallback
)

assert len(TITLES) == 36 and all(TITLES[i] == TITLES[0] for i in JAPANESE_SLOTS)
# Fingerprint of the frozen table (sha256 of the newline-joined titles);
# tests recompute this so the table cannot drift silently.
FINGERPRINT = '317418fe64b91753c3fda9d438a418215a1353cd3f976069a4c8421340ddd18a'
assert hashlib.sha256('\n'.join(TITLES).encode()).hexdigest() == FINGERPRINT
