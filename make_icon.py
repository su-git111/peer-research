from PIL import Image, ImageDraw

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 배경 둥근 사각형 (연한 라벤더)
d.rounded_rectangle((36, 36, S - 36, S - 36), radius=220, fill=(233, 226, 250, 255))

# 노트 페이지(흰색)가 뒤에서 살짝 보이게
d.rounded_rectangle((225, 205, 895, 915), radius=95, fill=(255, 255, 255, 255))
# 노트 표지 (코랄 핑크)
d.rounded_rectangle((150, 160, 815, 880), radius=95, fill=(255, 138, 155, 255))

# 스프링 제본 (표지 윗변에 링 5개)
for cx in [250, 383, 516, 649, 782]:
    d.ellipse((cx - 36, 120, cx + 36, 196), fill=(255, 255, 255, 255), outline=(255, 138, 155, 255), width=12)
    d.ellipse((cx - 11, 148, cx + 11, 170), fill=(150, 60, 78, 255))

# 얼굴 - 눈
for ex in [372, 592]:
    d.ellipse((ex - 36, 470, ex + 36, 566), fill=(74, 52, 58, 255))
    d.ellipse((ex + 2, 490, ex + 22, 516), fill=(255, 255, 255, 255))

# 볼터치
for bx in [300, 664]:
    d.ellipse((bx - 44, 582, bx + 44, 632), fill=(255, 148, 164, 170))

# 미소
d.arc((402, 512, 562, 648), start=20, end=160, fill=(74, 52, 58, 255), width=22)

# 반짝임 (오른쪽 위 4각별)
sx, sy, a, b = 720, 300, 60, 20
d.polygon([(sx, sy - a), (sx + b, sy), (sx, sy + a), (sx - b, sy)], fill=(255, 255, 255, 235))
d.polygon([(sx - a, sy), (sx, sy + b), (sx + a, sy), (sx, sy - b)], fill=(255, 255, 255, 235))

out = r"C:\Users\ssu\Downloads\research-cowork\icon.ico"
small = img.resize((256, 256), Image.LANCZOS)
small.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.resize((256, 256), Image.LANCZOS).save(
    r"C:\Users\ssu\AppData\Local\Temp\claude\C--Users-ssu-Downloads\e320a984-ab7c-4df3-bff2-647eee37d875\scratchpad\icon_preview.png")
print("icon.ico 생성 완료")
