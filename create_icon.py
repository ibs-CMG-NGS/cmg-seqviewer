"""
CMG-SeqViewer Icon Generator
Create a simple icon for the application
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    """Create application icon with DNA helix theme"""
    
    # 아이콘 크기 (여러 크기 생성)
    sizes = [256, 128, 64, 48, 32, 16]
    images = []
    
    for size in sizes:
        # 이미지 생성
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 배경 원 (그라디언트 효과를 위한 여러 원)
        center = size // 2
        for i in range(5):
            radius = size // 2 - i * 2
            alpha = 255 - i * 30
            color = (45 + i * 10, 140 - i * 10, 200 + i * 10, alpha)
            draw.ellipse([center - radius, center - radius, 
                         center + radius, center + radius], 
                        fill=color)
        
        # DNA 이중 나선을 표현하는 선들
        line_width = max(2, size // 64)
        
        # 상단 나선
        for j in range(3):
            y_offset = size * (0.2 + j * 0.2)
            x1 = size * 0.3
            x2 = size * 0.7
            
            # 연결선
            draw.line([(x1, y_offset), (x2, y_offset)], 
                     fill=(255, 255, 255, 200), width=line_width)
            
            # 양쪽 점
            point_size = max(3, size // 32)
            draw.ellipse([x1 - point_size, y_offset - point_size,
                         x1 + point_size, y_offset + point_size],
                        fill=(100, 200, 255, 255))
            draw.ellipse([x2 - point_size, y_offset - point_size,
                         x2 + point_size, y_offset + point_size],
                        fill=(100, 200, 255, 255))
        
        # 텍스트 추가 (큰 아이콘만)
        if size >= 64:
            try:
                # 시스템 폰트 사용
                font_size = max(size // 8, 12)
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                
                text = "CMG"
                # 텍스트 크기 계산
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # 텍스트 위치 (하단)
                text_x = (size - text_width) // 2
                text_y = size - text_height - size // 10
                
                # 텍스트 그림자
                draw.text((text_x + 1, text_y + 1), text, 
                         fill=(0, 0, 0, 128), font=font)
                # 텍스트
                draw.text((text_x, text_y), text, 
                         fill=(255, 255, 255, 255), font=font)
            except:
                pass
        
        images.append(img)
    
    # ICO 파일로 저장 (여러 크기 포함)
    images[0].save('cmg-seqviewer.ico', format='ICO', 
                   sizes=[(s, s) for s in sizes])
    print(f"Icon saved: cmg-seqviewer.ico")
    
    # PNG로도 저장 (미리보기용)
    images[0].save('cmg-seqviewer.png', format='PNG')
    print(f"Preview saved: cmg-seqviewer.png")

if __name__ == "__main__":
    create_icon()
