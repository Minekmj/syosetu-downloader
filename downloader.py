import os
import re
import sys
import shutil
import zipfile
import requests
import json
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

    # 💡 카쿠요무 방점(.bouten) 스타일 정의 포함
    css_content = """body { font-family: sans-serif; line-height: 1.7; margin: 6%; }
h2.subtitle { text-align: center; font-size: 1.5em; font-weight: bold; margin-top: 1.5em; margin-bottom: 2.0em; }
p { text-align: justify; margin-bottom: 0.8em; text-indent: 1em; }
em.bouten { font-style: normal; text-combine-upright: all; -webkit-text-combine-upright: all; text-emphasis-style: sesame; -webkit-text-emphasis-style: sesame; layout-grid-mode: both; }"""
    
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
        
        # 본문이 HTML 구조(<p>...</p> 또는 <div>)를 가지고 있으면 중복 감싸기 방지
        first_body_line = lines[1].strip() if len(lines) > 1 else ""
        if first_body_line.startswith("<p") or first_body_line.startswith("<div"):
            paragraphs = "".join(lines[1:])
        else:
            paragraphs = "".join([f"<p>{line.strip().replace('「','“').replace('」','”')}</p>\n" for line in lines[1:] if line.strip()])

        html_content = f"""<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"><html xmlns="http://www.w3.org/1999/xhtml"><head><title>{subtitle}</title><link rel="stylesheet" type="text/css" href="css/style.css"/></head><body><h2 class="subtitle">{subtitle}</h2>{paragraphs}</body></html>"""

        ch_id, ch_filename = f"chapter_{idx}", f"chapter_{idx}.xhtml"
        with open(os.path.join(build_dir, "OEBPS", ch_filename), "w", encoding="utf-8") as f: f.write(html_content)

        manifest_items.append(f'<item id="{ch_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'<itemref idref="{ch_id}"/>')
        toc_items.append(f'<navPoint id="{ch_id}" playOrder="{idx}"><navLabel><text>{subtitle}</text></navLabel><content src="{ch_filename}"/></navPoint>')
        idx += 1

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


# --- 🌐 크롤러 엔진 구역 ---

def download_syosetu(novel_code, start, end, trs_path):
    """ 소설가가 되자 크롤링 엔진 """
    url = f"https://ncode.syosetu.com/{novel_code}/"
    book_title = novel_code

    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            t = soup.find("p", class_="p-novel__title") or soup.find("h1")
            if t: book_title = t.get_text(strip=True)
    except: pass

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
            print(f"📥 [소설가] [{i}화 완료] {title}")
        except Exception as e: print(f"오류: {e}")

    return book_title


def download_kakuyomu(novel_code, start, end, trs_path):
    """ 문단 앞머리에 연속된 모든 종류의 공백을 글자가 나올 때까지 완전히 지우는 카쿠요무 엔진 """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ja,ko-KR;q=0.9,ko;q=0.8,en-US;q=0.7,en;q=0.6"
    }
    
    url = f"https://kakuyomu.jp/works/{novel_code}"
    headers["Referer"] = url
    
    try:
        res = requests.get(url, headers=headers)
        res.encoding = "utf-8"
        if res.status_code != 200:
            print(f"❌ 카쿠요무 소설 정보를 가져오지 못했습니다. (상태코드: {res.status_code})")
            return novel_code
            
        soup = BeautifulSoup(res.text, "html.parser")
        full_title = soup.title.string if soup.title else ""
        book_title = re.sub(r'（.+） - カクヨム$', '', full_title).strip()
        
        episodes = []
        html_text = res.text

        pattern = r'\{"__typename":"Episode","id":"(\d+)","title":"(.+?)"'
        matches = re.findall(pattern, html_text)

        seen_ids = set()
        for ep_id, ep_title in matches:
            if ep_id not in seen_ids:
                try:
                    decoded_title = json.loads(f'"{ep_title}"')
                except Exception:
                    decoded_title = ep_title

                episodes.append({
                    "id": ep_id,
                    "subtitle": decoded_title,
                    "url": f"https://kakuyomu.jp/works/{novel_code}/episodes/{ep_id}"
                })
                seen_ids.add(ep_id)

        print(f"확인: {len(episodes)} 개의 에피소드를 검출했습니다.")
    except Exception as e:
        print(f"카쿠요무 초기 정보 획득 실패: {e}")
        return novel_code

    start_idx = max(0, start - 1)
    end_idx = min(len(episodes), end)
    target_episodes = episodes[start_idx:end_idx]

    current_idx = 0
    for idx, ep in enumerate(target_episodes, start=start):
        try:
            ep_res = requests.get(ep["url"], headers=headers)
            ep_res.encoding = "utf-8"
            if ep_res.status_code != 200: continue

            ep_soup = BeautifulSoup(ep_res.text, "html.parser")
            subtitle_tag = ep_soup.select_one(".widget-episodeTitle") or ep_soup.find("h1")
            subtitle = subtitle_tag.get_text(strip=True) if subtitle_tag else ep["subtitle"]

            content_element = ep_soup.select_one(".widget-episodeBody")
            if not content_element: continue

            # 루비 태그 정리
            for tag in content_element.find_all(['rt', 'rp']):
                tag.decompose()
            for ruby in content_element.find_all('ruby'):
                ruby.replace_with(ruby.get_text(strip=True))

            body_paragraphs = []
            for p in content_element.find_all('p'):
                p_text = p.get_text(" ")
                
                # 💡 [핵심 수정] 문단 왼쪽에 스페이스가 몇 개가 있든 '완전 삭제' 처리
                # 일반 스페이스(' '), 일본어 전각 스페이스('　'), 탭('\t') 기호가 없어질 때까지 통째로 지웁니다.
                p_text = p_text.lstrip(' 　\t') 
                
                # 우측 공백도 깔끔하게 마감
                p_text = p_text.rstrip()
                
                if p_text:
                    # 강조 기호 제거 및 정제
                    p_text = re.sub(r'《《(.+?)》》', r'\1', p_text) 
                    body_paragraphs.append(p_text)
            
            body = "\n".join(body_paragraphs)

            current_idx += 1
            safe_title = re.sub(r'[\/:*?"<>|]', '_', subtitle)
            with open(os.path.join(trs_path, f"{current_idx}번_{safe_title}.txt"), "w", encoding="utf-8") as f:
                f.write(subtitle + "\n\n" + body + "\n\n")
            print(f"📥 [카쿠요무] [{idx}화 완료] {subtitle}")
        except Exception as e:
            print(f"카쿠요무 에피소드 다운로드 오류 ({ep['id']}): {e}")

    return book_title



# --- 🚀 메인 제어 구역 ---

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("사용법: python downloader.py [소설코드/사이트구분] [시작화수] [끝화수] [선택:site]")
        sys.exit(1)

    novel_code = sys.argv[1]
    start = int(sys.argv[2])
    end = int(sys.argv[3])
    site_type = sys.argv[4] if len(sys.argv) > 4 else 'syosetu'

    # URL 형태로 주어졌을 때 코드만 정밀 파싱
    if "syosetu.com" in novel_code:
        novel_code = novel_code.split("/")[-2]
        site_type = "syosetu"
    elif "kakuyomu.jp" in novel_code:
        novel_code = novel_code.split("/")[-1]
        site_type = "kakuyomu"

    trs_path = "./temp_trs"
    os.makedirs(trs_path, exist_ok=True)

    # 최종 판정 분기 (수동 site_type 입력 및 자동 숫자 판정 보완)
    is_kakuyomu = (site_type == 'kakuyomu') or novel_code.isdigit()

    if is_kakuyomu:
        book_title = download_kakuyomu(novel_code, start, end, trs_path)
    else:
        book_title = download_syosetu(novel_code, start, end, trs_path)

    # 파일 이름 및 타이틀 최종 마감 작업
    book_title = f"{book_title} | {start} ~ {end}"
    clean_title = re.sub(r'[\/:*?"<>|]', '_', book_title)

    os.makedirs("./output", exist_ok=True)
    create_epub_from_folder(trs_path, f"./output/{clean_title}.epub", book_title, ".")
    shutil.rmtree(trs_path)
    print("✨ EPUB 생성 완료")
