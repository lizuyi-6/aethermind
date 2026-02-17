"""
Mermaid图表渲染模块
将Mermaid代码转换为图片URL
"""

import re
import base64
import zlib

def mermaid_to_image_url(mermaid_code: str, theme: str = 'default') -> str:
    """
    将Mermaid代码转换为mermaid.ink图片URL

    Args:
        mermaid_code: Mermaid代码
        theme: 主题 (default, dark, forest, neutral)

    Returns:
        图片URL
    """
    # 清理代码
    code = mermaid_code.strip()

    # 构建JSON字符串
    json_str = '{"code":"' + code.replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"') + '","mermaid":{"theme":"' + theme + '"}}'

    # 压缩
    compressed = zlib.compress(json_str.encode('utf-8'), 9)
    # 去掉zlib头部(前2字节)和尾部校验(后4字节)得到原始deflate数据
    deflated = compressed[2:-4]
    # Base64编码，使用URL安全字符
    encoded = base64.urlsafe_b64encode(deflated).decode('utf-8').rstrip('=')

    return f'https://mermaid.ink/img/pako:{encoded}'

def extract_mermaid_blocks(markdown_content: str) -> list:
    """
    从Markdown内容中提取所有Mermaid代码块

    Returns:
        [(full_match, mermaid_code), ...]
    """
    # 匹配 ```mermaid ... ``` 代码块
    pattern = r'```mermaid\s*([\s\S]*?)```'

    result = []
    for match in re.finditer(pattern, markdown_content, re.IGNORECASE):
        full_match = match.group(0)
        mermaid_code = match.group(1).strip()
        result.append((full_match, mermaid_code))

    return result

def replace_mermaid_with_images(markdown_content: str) -> str:
    """
    将Markdown中的Mermaid代码块替换为图片

    Args:
        markdown_content: Markdown内容

    Returns:
        替换后的Markdown内容
    """
    blocks = extract_mermaid_blocks(markdown_content)
    result = markdown_content

    for full_match, mermaid_code in blocks:
        try:
            img_url = mermaid_to_image_url(mermaid_code)

            # 替换为HTML img标签
            img_html = f'<img src="{img_url}" alt="Mermaid图表" style="max-width:100%;height:auto;display:block;margin:20px auto;">'
            result = result.replace(full_match, img_html)
        except Exception as e:
            print(f'Mermaid转换失败: {e}')
            # 保留原始代码块
            continue

    return result

if __name__ == '__main__':
    # 测试
    test_code = '''pie title 测试饼图
    "A" : 30
    "B" : 40
    "C" : 30'''

    url = mermaid_to_image_url(test_code)
    print(f'图片URL: {url}')
