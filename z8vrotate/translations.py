"""Frozen 36-language title table for the vrotate menu row (T6).

Derivation rule (run offline against the stock C3.11 string tables; the
result is this static table, fingerprinted below):

* Base string: official id 2458 "Record camera orientation" -- the photo
  menu row with the same function, translated by Nikon into all 36 slots.
* Per language, the camera/photo word is swapped for that language's video
  word taken from official id 2214 "Video quality (N-RAW)":
  en camera->video, de Kamera->Video (hyphen kept from the compound),
  fr appareil->vidéo, es cámara->vídeo, it fotocamera->video,
  sv kamera->film, nl camera->video, zh-CN 照相机->视频, zh-TW 相機->短片,
  ko 카메라->동영상, th กล้อง->วิดีโอ, id kamera->film,
  pt câmara->filmagem, pl aparatu->video, fi kameran->videon (genitive as in
  id 2214 "Videon laatu"), da kamera->video, no kamera->film,
  cs fotoaparátu->videa, tr Kamera->Video, hu Fgép->Videó (Nikon spells the
  video word with a plain o, as in id 2214 "Videominőség"),
  el φωτ μηχ->video, ro aparat foto->video, uk фотокам.->відео,
  hi कैमरा->वीडियो, bg Фотоапарата->филма (definite singular, from
  филмите), hr fotoaparata->filma, ar الكاميرا->الفيلم (the trailing
  right-to-left mark of id 2458 is kept).
* Russian editorial case: id 2458 ru "Ориентация при записи" carries no
  camera word to swap, so the video word is inserted where the camera word
  sits in the sibling languages: "Ориентация видео при записи".
* Japanese builds its own phrase with the 動画の prefix on the stock words:
  動画の縦横位置情報の記録.  Slots 25/26/28-31/35 are Japanese fallbacks in
  the stock language directory and repeat slot 0.

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
    'Ориентация видео при записи',        # 11 ru
    'บันทึกมุมวิดีโอ',                   # 12 th
    'Rekam orientasi film',               # 13 id
    'Gravar orientação da filmagem',      # 14 pt
    'Rejestruj orientację video',         # 15 pl
    'Tallenna videon suunta',             # 16 fi
    'Optag videoretning',                 # 17 da
    'Registrer filmretning',              # 18 no
    'Záznam orientace videa',             # 19 cs
    'Video yönünü kaydet',                # 20 tr
    'Videó tájolásának rögzítése',        # 21 hu
    'Καταγρ προσαν/σμού video',           # 22 el
    'Înregistrare orientare video',       # 23 ro
    'Зберігати орієнт. відео',            # 24 uk
    '動画の縦横位置情報の記録',            # 25 ja fallback
    '動画の縦横位置情報の記録',            # 26 ja fallback
    'वीडियो समन्वयन रिकॉर्ड करें',          # 27 hi
    '動画の縦横位置情報の記録',            # 28 ja fallback
    '動画の縦横位置情報の記録',            # 29 ja fallback
    '動画の縦横位置情報の記録',            # 30 ja fallback
    '動画の縦横位置情報の記録',            # 31 ja fallback
    'Запис ориент. филма',                # 32 bg
    'Smer snimanja filma',                # 33 hr
    'تسجيل اتجاه الفيلم\u200f',            # 34 ar (trailing RLM as in id 2458)
    '動画の縦横位置情報の記録',            # 35 ja fallback
)

assert len(TITLES) == 36 and all(TITLES[i] == TITLES[0] for i in JAPANESE_SLOTS)
# Fingerprint of the frozen table (sha256 of the newline-joined titles);
# tests recompute this so the table cannot drift silently.
FINGERPRINT = '1b09a633ac370e98f891eb6858261f6f22a78b88c51768d4bcb9820f6bef3716'
assert hashlib.sha256('\n'.join(TITLES).encode()).hexdigest() == FINGERPRINT
