import os
os.environ['PYTHONUTF8'] = '1'
import re
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
from datetime import datetime
from pypinyin import lazy_pinyin

# ===================== 配置区 =====================
# Git 仓库目录
GIT_REPO_DIR= os.path.dirname(os.path.abspath(__file__))

# 源地址列表
SOURCE_URLS = [
    "https://gitee.com/hzxs800274/iptv/raw/master/live/TV",
    "https://gitee.com/zwssina/yunduanyuan/raw/master/SB",
    "https://gitee.com/gly358617629/iptv/raw/master/IPTV.txt",
    "https://gitee.com/gclgg/zubo/raw/main/IPTV.txt",
    "https://gh-proxy.com/https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/interface.txt",
    "https://raw.githubusercontent.com/gclgg/iptv-api/refs/heads/master/output/result.m3u"
]

# CCTV 名称规范化正则（批量生成，避免手写冗余）
CCTV_CHANNELS = [
    "CCTV-1 综合", 
    "CCTV-2 财经",
    "CCTV-3 综艺",
    "CCTV-4 中文国际",
    "CCTV-5 体育",
    "CCTV-6 电影",
    "CCTV-7 国防军事",
    "CCTV-8 电视剧",
    "CCTV-9 纪录",
    "CCTV-10 科教",
    "CCTV-11 戏曲",
    "CCTV-12 社会与法制",
    "CCTV-13 新闻",
    "CCTV-14 少儿",
    "CCTV-15 音乐",
    "CCTV-16 奥林匹克",
    "CCTV-17 农业农村"
]

CCTV_PATTERNS = []
for i in range(1, 18):
    if i == 5:
        CCTV_PATTERNS.append((re.compile(r'CCTV[ -_\s]?5\+', re.I),'CCTV-5+ 体育赛事'))
        CCTV_PATTERNS.append((re.compile(r'CCTV[ -_\s]?5', re.I),CCTV_CHANNELS[i-1]))
    else:
        CCTV_PATTERNS.append((re.compile(r'CCTV[-_\s]?{}(?![0-9])'.format(i), re.I),CCTV_CHANNELS[i-1]))

# 频道后缀清理正则
SATELLITE_PATTERNS = [
    re.compile(r'\s*4K', re.I),
    re.compile(r'\s*HD', re.I),
    re.compile(r'\s*\[\d+\*?\d+\]'),
    re.compile(r'\s*\(\d+[Pp]\)'),
    re.compile(r'\s*-\s*(高清|标清|4K)', re.I),
    re.compile(r'[-_]\d+[MK]\d+', re.I),
]


# CCTV 排序顺序（包含完整频道名）
CCTV_ORDER = [
    "CCTV-1 综合",
    "CCTV-2 财经",
    "CCTV-3 综艺",
    "CCTV-4 中文国际",
    "CCTV-5 体育",
    "CCTV-5+ 体育赛事", 
    "CCTV-6 电影",
    "CCTV-7 国防军事",
    "CCTV-8 电视剧",
    "CCTV-9 纪录",
    "CCTV-10 科教",
    "CCTV-11 戏曲",
    "CCTV-12 社会与法制",
    "CCTV-13 新闻",
    "CCTV-14 少儿",
    "CCTV-15 音乐",
    "CCTV-16 奥林匹克",
    "CCTV-17 农业农村"
]

# 特殊名称映射
NAME_MAPPING = {
    '咪咕': '咪咕视频',
    '咪视': '咪咕视频',
    '珠江': '广东珠江',
    '广东民生': '广东民生',
    '寰宇新闻': '寰宇新闻',
    '环宇新闻': '寰宇新闻',
    '中国教育1':'CETV1',
    '中国教育2':'CETV2',
    '中国教育3':'CETV3',
    '中国教育4':'CETV4',
}

# 卫视频道关键词
SATELLITE_KEYWORDS = r'卫视|东方|北京|天津|重庆|湖南|浙江|江苏|广东'

# ===================== 工具函数 =====================
def normalize_cctv_name(name):
    """规范化 CCTV 频道名称"""
    for pat, target in CCTV_PATTERNS:
        if pat.search(name):
            return target
    return name

def normalize_satellite_name(name):
    """规范化卫视频道名称"""
    # 优先映射
    for keyword, target in NAME_MAPPING.items():
        if keyword in name:
            return target
    # 清理后缀
    for pat in SATELLITE_PATTERNS:
        name = pat.sub('', name)
    return name.strip()

def natural_sort_key(s):
    #自然排序键（用于非 CCTV 频道排序）
    #return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]
    #字典排序
    pinyin = lazy_pinyin(s, style=0) 
    first_letters = ''.join([p[0] for p in pinyin])  
    parts = re.split(r'(\d+)', s)
    num_part = [int(p) if p.isdigit() else p for p in parts[1:]]
    return [first_letters] + num_part

# ===================== 排序函数 =====================
def sort_cctv_channels(df):
    """按 CCTV 序号排序，其他频道自然排序"""
    # CCTV 频道
    cctv_mask = df['program_name'].str.startswith('CCTV-')
    cctv_df = df[cctv_mask].copy()
    cctv_df['sort_key'] = cctv_df['program_name'].map(
        lambda x: CCTV_ORDER.index(x) if x in CCTV_ORDER else 999
    )
    cctv_sorted = cctv_df.sort_values('sort_key').drop(columns='sort_key')
    
    # 其他频道
    other_df = df[~cctv_mask]
    other_sorted = other_df.sort_values(
        'program_name',
        key=lambda x: x.apply(natural_sort_key)
    )
    
    return pd.concat([cctv_sorted, other_sorted], ignore_index=True)

# ===================== 地址有效性检测 =====================
def is_url_valid(url, timeout=3):
    """检测 URL 是否有效"""
    try:
        clean_url = url.split('$')[0]
        resp = requests.get(clean_url, stream=True, timeout=timeout, allow_redirects=True)
        valid = 200 <= resp.status_code < 400
        resp.close()
        return valid
    except:
        return False


def filter_valid_streams(df, max_workers=50):
    """多线程过滤有效流地址"""
    total = len(df)
    print(f"\n正在多线程检测 {total} 个地址...")
    valid_list = []
    count = valid_count = 0

    with ThreadPoolExecutor(max_workers) as executor:
        future_map = {
            executor.submit(is_url_valid, row['stream_url']): row
            for _, row in df.iterrows()
        }
        for f in as_completed(future_map):
            row = future_map[f]
            count += 1
            ok = f.result()
            if ok:
                valid_list.append(row)
                valid_count += 1
                print(f"✅ [{count}/{total}/有效:{valid_count}] {row['program_name']} -> 有效")
            else:
                print(f"❌ [{count}/{total}/有效:{valid_count}] {row['program_name']} -> 失效")
    speed = datetime.now().strftime("%Y-%m-%d %H:%M:%S 更新")
    speed += f' [有效 {len(valid_list)}: 失效 {total-len(valid_list)}]'
    with open("更新日志.ini", "a", encoding="utf-8") as f:
        f.write(f"{speed}\n")
    print(f"\n🎯 检测完成：{speed}")
    return pd.DataFrame(valid_list)

# ===================== 获取与解析 =====================
def _parse_line(line):
    """解析单行频道数据"""
    line = line.strip()
    if not line or ',' not in line or line.startswith('#'):
        return None
    name, url_txt = line.split(',', 1)
    return name.strip(), url_txt.strip()

def _classify_channel(name):
    """分类频道：央视/卫视/其他"""
    if name.startswith('CCTV'):
        return 'CCTV'
    elif re.search(SATELLITE_KEYWORDS, name):
        return '卫视'
    else:
        return '其他'

def fetch_streams_from_url(url):
    """从单个 URL 获取并分类频道"""
    print(f"\n正在获取: {url}")
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"获取失败 {resp.status_code}")
            return None
        text = resp.text
        ys, ws, qt = ['央视频道\n'], ['卫视频道\n'], ['其他频道\n']

        # 处理 M3U 格式
        if url.endswith('m3u') or text.startswith('#EXTM3U'):
            groups = re.findall(r'group-title="(.*?)",', text)
            names = re.findall(r'group-title=".*?",(.*?)[\r]?\n', text)
            urls_m3u = re.findall(r'https?://.*?\.m3u8?', text)
            for g, n, u in zip(groups, names, urls_m3u):
                n, u = n.strip(), u.strip()
                if '央视' in g or n.startswith('CCTV'):
                    ys.append(f'{normalize_cctv_name(n)}, {u}\n')
                elif '卫视' in g:
                    ws.append(f'{normalize_satellite_name(n)}, {u}\n')
                else:
                    qt.append(f'{normalize_satellite_name(n)}, {u}\n')
        # 处理普通文本格式
        else:
            for line in text.splitlines():
                parsed = _parse_line(line)
                if not parsed:
                    continue
                name, url_txt = parsed
                category = _classify_channel(name)
                if category == 'CCTV':
                    ys.append(f'{normalize_cctv_name(name)}, {url_txt}\n')
                elif category == '卫视':
                    ws.append(f'{normalize_satellite_name(name)}, {url_txt}\n')
                else:
                    qt.append(f'{normalize_satellite_name(name)}, {url_txt}\n')
        return ''.join(ys) + '\n' + ''.join(ws) + '\n' + ''.join(qt)
    except requests.exceptions.RequestException as e:
        print(f'获取异常: {e}')
        return None

def fetch_all_streams():
    """批量获取所有源"""
    all_data = []
    for url in SOURCE_URLS:
        content = fetch_streams_from_url(url)
        if content:
            all_data.append(content)
        else:
            print(f"❌ 无效源: {url}")
    return '\n'.join(all_data)

def parse_content(content):
    """解析合并后的内容为 DataFrame"""
    streams = []
    for line in content.splitlines():
        line = line.strip()
        if line and ',' in line and not line.startswith(('央视频道', '卫视频道', '其他频道')):
            name, url = line.split(',', 1)
            url = url.strip()
            if url.startswith('http'):
                norm_name = (
                    normalize_cctv_name(name)
                    if name.lower().startswith('cctv')
                    else normalize_satellite_name(name)
                )
                streams.append({'program_name': norm_name, 'stream_url': url})
    return pd.DataFrame(streams).drop_duplicates(
        subset=['program_name', 'stream_url'], keep='first'
    )

# ===================== 保存与推送 =====================
def save_to_txt(df, filename='list.txt'):
    """保存为 TXT 格式"""
    ys = ['🔹央视频道🔹,#genre#']
    ws = ['🔹卫视频道🔹,#genre#']
    qt = ['🔹其他频道🔹,#genre#']
    ktv = ['🔹盲盒点歌🔹,#genre#', '\n盲盒点歌,https://2025.xn--jfx065ba424q.top/1.m3u8''\n盲盒点歌1,https://2025.xn--jfx065ba424q.top/1.m3u8']
    
    for _, row in df.iterrows():
        line = f'{row["program_name"]},{row["stream_url"]}'
        if row['program_name'].startswith('CCTV-'):
            ys.append(line)
        elif '卫视' in row['program_name']:
            ws.append(line)
        else:
            qt.append(line)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ys) + '\n\n' + '\n'.join(ws) + '\n\n' + '\n'.join(qt) + '\n\n' + '\n'.join(ktv))
    print(f'\n📄 TXT 已保存: {os.path.abspath(filename)}')

def save_to_m3u(df, filename='list.m3u'):
    """保存为 M3U 格式"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n# 电视整合源\n')
        for _, row in df.iterrows():
            name = row['program_name']
            url = row['stream_url']
            if name.startswith('CCTV-'):
                group = '央视频道'
            elif '卫视' in name:
                group = '卫视频道'
            else:
                group = '其他频道'
            f.write(f'#EXTINF:-1 tvg-name="{name}" group-title="{group}",{name}\n{url}\n')
        # 盲盒点歌
        f.write(f'#EXTINF:-1 tvg-name="盲盒点歌" group-title="盲盒点歌",盲盒点歌\nhttps://2025.xn--jfx065ba424q.top/1.m3u8\n')
        f.write(f'#EXTINF:-1 tvg-name="盲盒点歌1" group-title="盲盒点歌",盲盒点歌1\nhttps://2025.xn--jfx065ba424q.top/1.m3u8\n')
    print(f'📺 M3U 已保存: {os.path.abspath(filename)}')

def push_gitee():
    """推送更新到 Gitee"""
    os.chdir(GIT_REPO_DIR)
    now = datetime.now()
    commit_msg = f"自动更新 {now.strftime('%Y-%m-%d %H:%M:%S')}"
    try:
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        subprocess.run(['git', 'push', 'origin', 'master'], check=True)
        print("✅ 推送成功！")
    except subprocess.CalledProcessError as e:
        print(f"❌ 推送失败: {e}")

# ===================== 主程序 =====================
if __name__ == '__main__':
    print('='*50)
    print('  电视源自动获取+去重+多线程检测+排序+双格式保存')
    print('='*50)

    content = fetch_all_streams()
    if not content.strip():
        print('\n❌ 无有效数据')
        exit()

    df = parse_content(content)
    df_valid = filter_valid_streams(df)
    df_sorted = sort_cctv_channels(df_valid)

    save_to_txt(df_sorted)
    save_to_m3u(df_sorted)
    push_gitee()
    input("任务全部完成，按回车退出...")
