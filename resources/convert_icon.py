#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess


def convert_svg_to_ico():
    """Конвертирует SVG иконку в ICO формат для Windows"""
    try:
        # Проверка наличия файла SVG
        svg_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
        ico_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
        
        if not os.path.exists(svg_path):
            print(f"Ошибка: Файл {svg_path} не найден.")
            return 1
        
        # Проверка наличия Inkscape для конвертации
        try:
            # Попытка использовать Inkscape для конвертации
            print("Попытка использовать Inkscape для конвертации...")
            subprocess.run(
                [
                    "inkscape", 
                    "--export-filename=temp.png", 
                    "--export-width=256", 
                    "--export-height=256", 
                    svg_path
                ], 
                check=True
            )
            
            # Конвертация PNG в ICO с помощью PIL
            print("Конвертация PNG в ICO...")
            from PIL import Image
            img = Image.open("temp.png")
            img.save(ico_path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            
            # Удаление временного файла
            os.remove("temp.png")
            
        except (subprocess.SubprocessError, FileNotFoundError):
            # Если Inkscape не установлен, используем прямую конвертацию через PIL
            print("Inkscape не найден. Попытка использовать cairosvg...")
            try:
                import cairosvg
                import io
                from PIL import Image
                
                # Конвертация SVG в PNG в памяти
                png_data = cairosvg.svg2png(url=svg_path, output_width=256, output_height=256)
                img = Image.open(io.BytesIO(png_data))
                img.save(ico_path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
                
            except ImportError:
                print("Ошибка: Для конвертации необходимо установить cairosvg и Pillow:")
                print("pip install cairosvg Pillow")
                return 1
        
        print(f"Иконка успешно сконвертирована и сохранена в {ico_path}")
        return 0
        
    except Exception as e:
        print(f"Ошибка при конвертации иконки: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(convert_svg_to_ico())