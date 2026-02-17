#!/usr/bin/env python3
"""
PDF功能诊断工具
用于检查PDF生成功能的依赖和配置是否正确
"""

import os
import sys

# Avoid Windows GBK console crashes on symbols such as "✓"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def print_header(text):
    """打印带格式的标题"""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)

def print_section(text):
    """打印章节标题"""
    print(f"\n{text}")
    print("-" * 60)

def check_python_version():
    """检查Python版本"""
    print_section("1. Python环境")
    print(f"   Python版本: {sys.version}")
    print(f"   Python路径: {sys.executable}")

    major, minor = sys.version_info[:2]
    if major == 3 and minor >= 7:
        print("   ✓ Python版本符合要求 (>= 3.7)")
        return True
    else:
        print("   ✗ Python版本过低，建议使用Python 3.7+")
        return False

def check_packages():
    """检查依赖包"""
    print_section("2. Python依赖包")

    packages = {
        'weasyprint': 'WeasyPrint',
        'markdown': 'Markdown',
        'reportlab': 'ReportLab',
        'PyPDF2': 'PyPDF2',
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'openai': 'OpenAI',
        'dotenv': 'python-dotenv'
    }

    results = {}
    for pkg_import, pkg_name in packages.items():
        try:
            module = __import__(pkg_import)
            version = getattr(module, '__version__', '未知版本')
            print(f"   ✓ {pkg_name}: {version}")
            results[pkg_import] = True
        except ImportError as e:
            print(f"   ✗ {pkg_name}: 未安装")
            print(f"      错误: {e}")
            results[pkg_import] = False

    all_ok = all(results.values())
    if all_ok:
        print("\n   所有依赖包已安装 ✓")
    else:
        print("\n   ⚠ 缺少以下包，请运行:")
        print("   pip3 install -r requirements.txt")

    return all_ok

def test_weasyprint():
    """测试WeasyPrint功能"""
    print_section("3. WeasyPrint功能测试")

    try:
        from weasyprint import HTML, CSS
        print("   ✓ WeasyPrint模块导入成功")

        # 尝试生成简单的PDF
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; }
                h1 { color: #2c3e50; }
            </style>
        </head>
        <body>
            <h1>PDF测试</h1>
            <p>这是一个测试PDF文件。</p>
            <p>中文测试：你好，世界！</p>
        </body>
        </html>
        """

        test_pdf = "test_output.pdf"
        print(f"   生成测试PDF: {test_pdf}")

        HTML(string=html_content).write_pdf(test_pdf)

        if os.path.exists(test_pdf):
            size = os.path.getsize(test_pdf)
            print(f"   ✓ PDF生成成功 ({size} bytes)")
            os.remove(test_pdf)
            print(f"   ✓ 测试文件已删除")
            return True
        else:
            print("   ✗ PDF文件未生成")
            return False

    except Exception as e:
        print(f"   ✗ WeasyPrint测试失败:")
        print(f"      错误: {e}")
        print(f"\n   可能原因:")
        print(f"   1. 缺少系统依赖库")
        print(f"   2. 运行: sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0")
        return False

def check_directory_permissions():
    """检查目录权限"""
    print_section("4. 目录权限检查")

    directories = ['reports', 'uploads']
    all_ok = True

    for dir_name in directories:
        try:
            # 创建目录（如果不存在）
            os.makedirs(dir_name, exist_ok=True)
            print(f"   ✓ {dir_name}/ 目录存在")

            # 测试写入权限
            test_file = os.path.join(dir_name, 'test_permissions.txt')
            with open(test_file, 'w') as f:
                f.write('test')

            # 测试读取权限
            with open(test_file, 'r') as f:
                content = f.read()

            # 删除测试文件
            os.remove(test_file)
            print(f"   ✓ {dir_name}/ 目录可读写")

        except Exception as e:
            print(f"   ✗ {dir_name}/ 目录权限问题:")
            print(f"      错误: {e}")
            print(f"      请运行: chmod 755 {dir_name}")
            all_ok = False

    return all_ok

def check_fonts():
    """检查中文字体"""
    print_section("5. 中文字体检查")

    try:
        import subprocess
        result = subprocess.run(['fc-list', ':lang=zh'],
                              capture_output=True,
                              text=True,
                              timeout=5)

        if result.returncode == 0:
            fonts = [f for f in result.stdout.strip().split('\n') if f]
            if fonts:
                print(f"   ✓ 找到 {len(fonts)} 个中文字体")
                print(f"   示例字体:")
                for font in fonts[:3]:
                    # 截取字体名称（去除路径）
                    font_name = font.split(':')[0].split('/')[-1] if ':' in font else font
                    print(f"      - {font_name[:80]}")
                if len(fonts) > 3:
                    print(f"      ... (还有 {len(fonts)-3} 个)")
                return True
            else:
                print("   ⚠ 未找到中文字体")
                print("   PDF中的中文可能无法正常显示")
                print("   建议安装: sudo apt-get install -y fonts-noto-cjk fonts-wqy-microhei")
                return False
        else:
            print("   ⚠ 无法执行fc-list命令")
            print("   请安装: sudo apt-get install -y fontconfig")
            return False

    except FileNotFoundError:
        print("   ⚠ fc-list命令不存在")
        print("   请安装: sudo apt-get install -y fontconfig")
        return False
    except subprocess.TimeoutExpired:
        print("   ⚠ fc-list命令超时")
        return False
    except Exception as e:
        print(f"   ⚠ 字体检查失败: {e}")
        return False

def check_config_files():
    """检查配置文件"""
    print_section("6. 配置文件检查")

    files = {
        '.env': '环境配置',
        'requirements.txt': 'Python依赖',
        'system_prompt.txt': '系统提示词',
    }

    for filename, description in files.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"   ✓ {filename} ({description}, {size} bytes)")
        else:
            print(f"   ⚠ {filename} 不存在 ({description})")

def test_pdf_conversion():
    """完整的PDF转换测试"""
    print_section("7. 完整PDF转换测试")

    try:
        import markdown
        from weasyprint import HTML

        # 创建测试Markdown内容
        md_content = """
# 测试报告

## 第一章 项目概述

这是一个测试章节。

### 1.1 项目基本信息

- 项目名称：测试项目
- 建设单位：测试单位
- 项目类型：测试类型

## 第二章 市场分析

这是市场分析内容。

**重点内容：**

1. 市场需求分析
2. 竞争对手分析
3. 市场趋势预测

## 结论

测试报告生成成功。
"""

        print("   生成HTML...")
        html_content = markdown.markdown(
            md_content,
            extensions=['extra', 'codehilite', 'tables', 'fenced_code']
        )

        # 添加样式
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: "Microsoft YaHei", "SimSun", Arial, sans-serif;
                    line-height: 1.8;
                    color: #333;
                    max-width: 800px;
                    margin: 40px auto;
                    padding: 20px;
                }}
                h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                h2 {{ color: #34495e; margin-top: 30px; }}
                h3 {{ color: #7f8c8d; }}
                ul, ol {{ margin-left: 20px; }}
                strong {{ color: #e74c3c; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        test_pdf = "test_complete_report.pdf"
        print(f"   生成PDF: {test_pdf}")

        HTML(string=styled_html).write_pdf(test_pdf)

        if os.path.exists(test_pdf):
            size = os.path.getsize(test_pdf)
            print(f"   ✓ PDF生成成功!")
            print(f"   文件: {test_pdf}")
            print(f"   大小: {size} bytes ({size/1024:.2f} KB)")
            print(f"\n   请打开文件检查:")
            print(f"   1. 中文是否正常显示")
            print(f"   2. 格式是否正确")
            print(f"   3. 样式是否生效")
            print(f"\n   ⚠ 测试文件未自动删除，请手动删除")
            return True
        else:
            print("   ✗ PDF文件未生成")
            return False

    except Exception as e:
        print(f"   ✗ PDF转换测试失败:")
        print(f"      错误: {e}")
        import traceback
        print(f"\n   详细错误:")
        print(traceback.format_exc())
        return False

def print_summary(results):
    """打印总结"""
    print_header("诊断总结")

    total = len(results)
    passed = sum(1 for r in results.values() if r)

    print(f"\n检查项: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")

    if all(results.values()):
        print("\n✓ 所有检查通过，PDF功能应该可以正常使用！")
    else:
        print("\n⚠ 部分检查未通过，请按照上述提示修复问题")
        print("\n未通过的检查项:")
        for name, result in results.items():
            if not result:
                print(f"   - {name}")

    print("\n建议:")
    if not results.get('packages', True):
        print("   1. 安装Python依赖: pip3 install -r requirements.txt")
    if not results.get('weasyprint', True):
        print("   2. 安装系统依赖: sudo bash fix_pdf_issues.sh")
    if not results.get('fonts', True):
        print("   3. 安装中文字体: sudo apt-get install -y fonts-noto-cjk")
    if not results.get('permissions', True):
        print("   4. 修复目录权限: chmod 755 reports uploads")

def main():
    """主函数"""
    print_header("PDF功能诊断工具")
    print("此工具将检查PDF生成功能的所有依赖和配置")

    results = {}

    # 执行所有检查
    results['python'] = check_python_version()
    results['packages'] = check_packages()
    results['weasyprint'] = test_weasyprint()
    results['permissions'] = check_directory_permissions()
    results['fonts'] = check_fonts()
    check_config_files()  # 信息性检查，不影响结果
    results['conversion'] = test_pdf_conversion()

    # 打印总结
    print_summary(results)

    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

    # 返回状态码
    sys.exit(0 if all(results.values()) else 1)

if __name__ == '__main__':
    main()
