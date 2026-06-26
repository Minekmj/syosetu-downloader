import os
import re
import sys
import shutil
import zipfile
import requests
from bs4 import BeautifulSoup

def extract_number(filename):
    match = re.search(r'(\d+)번', filename)
    return int(match.group(1)) if match else 9999

def create_epub_from_folder(folder_path, output_epub_path, book_title, base_dir):
    if not os.path.exists(folder_path): return False
    all_files = os.listdir(folder_path)
    txt_files = [f for f in all_files if f.endswith('.txt') and not os.path.isdir(os.path.join(folder_path, f))]
    txt_files.sort(key=extract_number)
    if not txt_files: return False

    build_dir = os.path.join(base_dir, "temp_epub_build")
    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(os.path.join(build_dir, "META-INF"), exist_ok=True)
    os.makedirs(os.path.join(build_dir, "OEBPS"), exist_ok=True)
    os.makedirs(os.path.join(build_dir, "OEBPS", "css"), exist_ok=True)
    
    with open(os.path.join(build_dir, "mimetype"), "w", encoding="utf-8") as f:
        f.write("application/epub+zip")
        
    container_xml = """<?xml version="1.0" encoding="UTF-8"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>"""
    with open(os.path.join(build_dir, "META-INF", "container.xml"), "w", encoding="utf-8") as f:
        f.write(container_xml)
        
    css_content = "body { font-family: sans-serif; line-height: 1.7; margin: 6%; }\nh2.subtitle { text-align: center; font-size: 1.5em; font-weight: bold; margin-top: 1.5em; margin-bottom: 2.0em; }\np { text-align: justify; margin-bottom: 0.8em; text-indent: 1em; }"
    with open(os.path.join(build_dir, "OEBPS", "css", "style.css"), "w", encoding="utf-8") as f:
        f.write(css_content)
        
    manifest_items = ['<item id="css" href="css/style.css" media-type="text/css"/>', '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>']
    spine_items, toc_items = [], []
    
    idx = 1
    for file_name in txt_files:
        file_path = os.path.join(folder_path, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f: lines = f.readlines()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='cp949') as f: lines = f.readlines()
        if not lines: continue
            
        subtitle = lines[0].strip()
        paragraphs = "".join([f"<p>{line.strip().replace('「','“').replace('」','”')}</p>\n" for line in lines[1:] if line.strip()])
        
        html_content = f"""<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"><html xmlns="http://www.w3.org/1999/xhtml"><head><title>{subtitle}</title><link rel="stylesheet" type="text/css" href="css/style.css"/></head><body><h2 class="subtitle">{subtitle}</h2>{paragraphs}</body></html>"""
        
        ch_id, ch_filename = f"chapter_{idx}", f"chapter_{idx}.xhtml"
        with open(os.path.join(build_dir, "OEBPS", ch_filename), "w", encoding="utf-8") as f: f.write(html_content)
            
        manifest_items.append(f'<item id="{ch_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'<itemref idref="{ch_id}"/>')
        toc_items.append(f'<navPoint id="{ch_id}" playOrder="{idx}"><navLabel><text>{subtitle}</text></navLabel><content src="{ch_filename}"/></navPoint>')
        idx += 1

    # 에러 방지: 백슬래시 조인을 f-string 외부에서 미리 처리
    manifest_str = "\n ".join(manifest_items)
    spine_str = "\n ".join(spine_items)
    toc_str = "\n".join(toc_items)

    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{book_title}</dc:title><dc:language>ko</dc:language><dc:identifier id="BookId">urn:uuid:550e8400-e29b-41d4-a716-446655440000</dc:identifier></metadata><manifest>{manifest_str}</manifest><spine toc="ncx">{spine_str}</spine></package>"""
    with open(os.path.join(build_dir, "OEBPS", "content.opf"), "w", encoding="utf-8") as f: f.write(content_opf)
        
    toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE ncx PUBLIC "-//NISO//Z39.86-2005//EN" "http://www.daisy.org/z3986/2005/ncx-1.0.dtd"><ncx xmlns="http://www.daisy.org/z3986/2005/ncx-1.0.dtd" version="1.0"><head><meta name="dtb:uid" content="urn:uuid:550e8400-e29b-41d4-a716-446655440000"/><meta name="dtb:depth" content="1"/></head><docTitle><text>{book_title}</text></docTitle><navMap>{toc_str}</navMap></ncx>"""
    with open(os.path.join(build_dir, "OEBPS", "toc.ncx"), "w", encoding="utf-8") as f: f.write(toc_ncx)
        
    with zipfile.ZipFile(output_epub_path, 'w', zipfile.ZIP_DEFLATED) as epub_zip:
        epub_zip.write(os.path.join(build_dir, "mimetype"), "mimetype", compress_type=zipfile.ZIP_STORED)
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                if file == "mimetype": continue
                full_path = os.path.join(root, file)
                epub_zip.write(full_path, os.path.relpath(full_path, build_dir))
    shutil.rmtree(build_dir)
    return True

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("사용법: python downloader.py [소설코드] [시작화수] [끝화수]")
        sys.exit(1)

    novel_code = sys.argv[1]
    start = int(sys.argv[2])
    end = int(sys.argv[3])
    
    url = f"https://ncode.syosetu.com/{novel_code}/"
    book_title = novel_code
    
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            t = soup.find("p", class_="p-novel__title") or soup.find("h1")
            if t: book_title = t.get_text(strip=True)
    except: pass
        
    book_title = f"{book_title} | {start} ~ {end}"
    clean_title = re.sub(r'[\/:*?"<>|]', '_', book_title)
    
    trs_path = "./temp_trs"
    os.makedirs(trs_path, exist_ok=True)
    
    current_idx = 0
    for i in range(start, end + 1):
        try:
            res = requests.get(f"{url}{i}/", headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code != 200: continue
            soup = BeautifulSoup(res.text, "html.parser")
            title_tag = soup.find("h1", class_="p-novel__title p-novel__title--rensai")
            body_tag = soup.find("div", class_="js-novel-text p-novel__text")
            if not title_tag or not body_tag: continue
            
            title = title_tag.get_text(strip=True)
            for tag in body_tag.find_all(['rp', 'rt']): tag.decompose()
            for ruby in body_tag.find_all('ruby'): ruby.replace_with(ruby.get_text(strip=True))
            
            body = "\n".join([p.get_text(" ", strip=True) for p in body_tag.find_all('p') if p.get_text(strip=True)])
            current_idx += 1
            with open(os.path.join(trs_path, f"{current_idx}번_{title}.txt"), "w", encoding="utf-8") as f:
                f.write(title + "\n\n" + body + "\n\n")
            print(f"📥 [{i}화 완료] {title}")
        except Exception as e: print(f"오류: {e}")
            
    os.makedirs("./output", exist_ok=True)
    create_epub_from_folder(trs_path, f"./output/{clean_title}.epub", book_title, ".")
    shutil.rmtree(trs_path)
    print("✨ EPUB 생성 완료")
