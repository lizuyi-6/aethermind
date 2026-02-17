"""
文件处理模块
支持多种文件格式的上传和内容提取
"""

import os
import mimetypes
from typing import Optional, Tuple
from pathlib import Path


class FileProcessor:
    """文件处理器，支持多种文件格式"""
    
    # 支持的文件类型
    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.markdown',  # 文本文件
        '.pdf',  # PDF文件
        '.docx', '.doc',  # Word文档
        '.xlsx', '.xls',  # Excel文件
        '.csv',  # CSV文件
        '.json',  # JSON文件
        '.py', '.js', '.java', '.cpp', '.c', '.html', '.css',  # 代码文件
    }
    
    def __init__(self):
        """初始化文件处理器"""
        self.upload_dir = "uploads"
        self._ensure_upload_dir()
    
    def _ensure_upload_dir(self):
        """确保上传目录存在"""
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
    
    def is_supported_file(self, file_path: str) -> bool:
        """检查文件是否支持"""
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS
    
    def read_text_file(self, file_path: str) -> str:
        """读取文本文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    return f.read()
            except:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
    
    def read_pdf(self, file_path: str) -> str:
        """读取PDF文件"""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            raise ImportError("需要安装PyPDF2库: pip install PyPDF2")
        except Exception as e:
            raise Exception(f"读取PDF文件失败: {str(e)}")
    
    def read_docx(self, file_path: str) -> str:
        """读取Word文档"""
        try:
            from docx import Document
            doc = Document(file_path)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return "\n".join(text)
        except ImportError:
            raise ImportError("需要安装python-docx库: pip install python-docx")
        except Exception as e:
            raise Exception(f"读取Word文档失败: {str(e)}")
    
    def read_excel(self, file_path: str) -> str:
        """读取Excel文件"""
        try:
            import pandas as pd
            # 读取所有工作表
            excel_file = pd.ExcelFile(file_path)
            text_parts = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                text_parts.append(f"工作表: {sheet_name}\n")
                text_parts.append(df.to_string())
                text_parts.append("\n")
            
            return "\n".join(text_parts)
        except ImportError:
            raise ImportError("需要安装pandas和openpyxl库: pip install pandas openpyxl")
        except Exception as e:
            raise Exception(f"读取Excel文件失败: {str(e)}")
    
    def read_csv(self, file_path: str) -> str:
        """读取CSV文件"""
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            return df.to_string()
        except ImportError:
            raise ImportError("需要安装pandas库: pip install pandas")
        except Exception as e:
            raise Exception(f"读取CSV文件失败: {str(e)}")
    
    def read_json(self, file_path: str) -> str:
        """读取JSON文件"""
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            raise Exception(f"读取JSON文件失败: {str(e)}")
    
    def process_file(self, file_path: str) -> Tuple[str, str]:
        """
        处理文件并返回内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            (文件内容, 文件类型描述) 元组
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not self.is_supported_file(file_path):
            ext = Path(file_path).suffix.lower()
            raise ValueError(f"不支持的文件类型: {ext}")
        
        file_ext = Path(file_path).suffix.lower()
        file_name = os.path.basename(file_path)
        
        # 根据文件扩展名选择处理方法
        if file_ext in ['.txt', '.md', '.markdown']:
            content = self.read_text_file(file_path)
            file_type = "文本文件"
        elif file_ext == '.pdf':
            content = self.read_pdf(file_path)
            file_type = "PDF文档"
        elif file_ext in ['.docx', '.doc']:
            content = self.read_docx(file_path)
            file_type = "Word文档"
        elif file_ext in ['.xlsx', '.xls']:
            content = self.read_excel(file_path)
            file_type = "Excel文件"
        elif file_ext == '.csv':
            content = self.read_csv(file_path)
            file_type = "CSV文件"
        elif file_ext == '.json':
            content = self.read_json(file_path)
            file_type = "JSON文件"
        elif file_ext in ['.py', '.js', '.java', '.cpp', '.c', '.html', '.css']:
            content = self.read_text_file(file_path)
            file_type = "代码文件"
        else:
            # 默认尝试作为文本文件读取
            content = self.read_text_file(file_path)
            file_type = "文本文件"
        
        return content, file_type
    
    def copy_to_upload_dir(self, source_path: str) -> str:
        """
        将文件复制到上传目录
        
        Args:
            source_path: 源文件路径
            
        Returns:
            目标文件路径
        """
        import shutil
        file_name = os.path.basename(source_path)
        dest_path = os.path.join(self.upload_dir, file_name)
        
        # 如果目标文件已存在，添加序号
        counter = 1
        base_name, ext = os.path.splitext(file_name)
        while os.path.exists(dest_path):
            new_name = f"{base_name}_{counter}{ext}"
            dest_path = os.path.join(self.upload_dir, new_name)
            counter += 1
        
        shutil.copy2(source_path, dest_path)
        return dest_path
    
    def format_file_content_for_prompt(self, file_path: str, content: str, file_type: str, user_query: Optional[str] = None) -> str:
        """
        将文件内容格式化为提示词
        
        Args:
            file_path: 文件路径
            content: 文件内容
            file_type: 文件类型
            user_query: 用户的问题（可选）
            
        Returns:
            格式化后的提示词
        """
        file_name = os.path.basename(file_path)
        
        prompt_parts = [
            f"【文件信息】",
            f"文件名: {file_name}",
            f"文件类型: {file_type}",
            f"文件路径: {file_path}",
            f"\n【文件内容】\n",
            content
        ]
        
        if user_query:
            prompt_parts.append(f"\n【用户问题】\n{user_query}")
        
        return "\n".join(prompt_parts)

