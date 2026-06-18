import subprocess
import os
import requests

def m3u8_to_mp4(m3u8_url, output_path, ffmpeg_path="ffmpeg"):
    try:
        # 检查 FFmpeg 是否可用
        subprocess.run([ffmpeg_path, "-version"], check=True, 
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 核心命令：直接通过 FFmpeg 下载并转封装
        command = [
            ffmpeg_path,
            "-i", m3u8_url,       # 输入 M3U8 地址
            "-c", "copy",         # 直接复制流（无需转码）
            "-movflags", "+faststart",  # 优化 MP4 在线播放
            "-y",                 # 覆盖已存在文件
            output_path
        ]
      
        # 执行命令（实时打印进度）
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        # 打印 FFmpeg 输出（进度信息）
        for line in process.stdout:
            print(line.strip())
    
        return True

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg 错误: {e.stderr}")
        return False

    except Exception as e:
        print(f"其他错误: {str(e)}")
        return False

# 使用示例（支持 URL 或本地文件）
if __name__ == "__main__":
    print(f"使用说明：")
    print(f"1,浏览器需要安装”迅雷下载支持“扩展")
    print(f"2,视频上方会显示下载按钮，点击后在迅雷新建下载任务页面找到显示文件大小后面的小三角形点一下，复制出里面的M3U8地址")
    print(f"3,将地址粘贴到下方回车，再填个文件名回车")
    while 1:
        m3u8_url = input("输入URL 或 本地文件地址：")
        output_path = input("输入文件名：") + ".mp4"
        success = m3u8_to_mp4(m3u8_url,output_path)
        if success:
            print("转换成功！")
        else:
            print("转换失败！")