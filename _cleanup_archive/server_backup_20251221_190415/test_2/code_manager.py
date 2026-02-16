#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证码管理模块
集成验证码的生成、验证、管理功能
"""

import os
import json
import secrets
import string
import hashlib
import time
import re
from typing import Dict, Tuple, Optional


class CodeManager:
    """验证码管理器"""
    
    def __init__(self, codes_file: str = None):
        """
        初始化验证码管理器
        
        参数:
            codes_file: 验证码存储文件路径，默认为 None（使用默认路径）
        """
        if codes_file is None:
            # 默认使用"兑换码及验码"文件夹中的文件
            # 获取当前文件的目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 尝试多个可能的路径
            possible_paths = [
                # 如果"兑换码及验码"文件夹在同一工作区
                os.path.join(current_dir, '..', '兑换码及验码', 'generated_codes.json'),
                # 如果在项目根目录
                os.path.join(current_dir, '兑换码及验码', 'generated_codes.json'),
                # 如果在上级目录
                os.path.join(os.path.dirname(current_dir), '兑换码及验码', 'generated_codes.json'),
                # 绝对路径（Windows）
                os.path.join('C:', 'Users', 'Abraham', 'Desktop', '兑换码及验码', 'generated_codes.json'),
            ]
            
            # 查找存在的文件
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    codes_file = abs_path
                    break
            else:
                # 如果都不存在，使用第一个路径（会在保存时创建）
                # 优先使用相对路径
                codes_file = os.path.abspath(possible_paths[0])
        
        self.codes_file = os.path.abspath(codes_file)
        # 确保目录存在
        codes_dir = os.path.dirname(self.codes_file)
        if codes_dir:
            os.makedirs(codes_dir, exist_ok=True)
    
    def load_codes(self) -> Dict[str, int]:
        """
        从文件加载已生成的验证码列表
        
        返回:
            dict: 验证码字典，格式为 {验证码: 剩余使用次数}
        """
        if os.path.exists(self.codes_file):
            try:
                with open(self.codes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 兼容旧格式（列表格式）
                    if isinstance(data.get('codes'), list):
                        old_codes = data.get('codes', [])
                        return {code: 1 for code in old_codes}
                    # 新格式（字典格式）
                    return data.get('codes', {})
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def save_codes(self, codes: Dict[str, int]) -> bool:
        """
        将验证码字典保存到文件
        
        参数:
            codes: 验证码字典，格式为 {验证码: 剩余使用次数}
        
        返回:
            bool: 保存是否成功
        """
        try:
            data = {'codes': codes}
            with open(self.codes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存文件时发生错误: {e}")
            return False
    
    def _add_entropy(self) -> int:
        """添加额外的熵值以提高随机性"""
        entropy_sources = [
            str(time.time_ns()),
            str(os.urandom(16).hex()),
            str(len(self.load_codes())),
            str(os.getpid()),
        ]
        combined = ''.join(entropy_sources).encode()
        entropy_hash = hashlib.sha256(combined).digest()
        return int.from_bytes(entropy_hash[:8], 'big')
    
    def _generate_single_code(self, existing_codes: Dict[str, int]) -> str:
        """
        生成单个验证码（不保存）
        
        参数:
            existing_codes: 已存在的验证码字典
        
        返回:
            str: 格式为 XXXXXX-XXXXXX-XXXXXX-XXXXXX 的验证码
        """
        characters = string.ascii_uppercase + string.digits
        
        max_attempts = 1000
        for attempt in range(max_attempts):
            entropy = self._add_entropy()
            
            code_chars = []
            for i in range(24):
                if secrets.randbelow(100) < 90:
                    code_chars.append(secrets.choice(characters))
                else:
                    entropy_index = (entropy + i + attempt) % len(characters)
                    code_chars.append(characters[entropy_index])
            
            code = ''.join(code_chars)
            formatted_code = '-'.join([code[i:i+6] for i in range(0, 24, 6)])
            
            if formatted_code not in existing_codes:
                return formatted_code
        
        raise Exception("无法生成新的唯一验证码")
    
    def generate_code(self, uses: int = 1) -> str:
        """
        生成验证码并保存
        
        参数:
            uses: 验证码可使用次数，默认为1
        
        返回:
            str: 生成的验证码
        """
        if uses < 1:
            raise ValueError("使用次数必须大于0")
        
        existing_codes = self.load_codes()
        new_code = self._generate_single_code(existing_codes)
        existing_codes[new_code] = uses
        
        if not self.save_codes(existing_codes):
            raise Exception(f"无法保存验证码到文件 {self.codes_file}")
        
        return new_code
    
    def generate_multiple_codes(self, count: int = 1, uses: int = 1) -> list:
        """
        生成多个验证码
        
        参数:
            count: 要生成的验证码数量
            uses: 每个验证码可使用次数
        
        返回:
            list: 验证码列表
        """
        if uses < 1:
            raise ValueError("使用次数必须大于0")
        
        existing_codes = self.load_codes()
        codes = []
        
        for _ in range(count):
            new_code = self._generate_single_code(existing_codes)
            codes.append(new_code)
            existing_codes[new_code] = uses
        
        if not self.save_codes(existing_codes):
            raise Exception(f"无法保存验证码到文件 {self.codes_file}")
        
        return codes
    
    def verify_code(self, code: str, remove_after_verify: bool = True) -> Tuple[bool, str]:
        """
        验证验证码是否正确
        
        参数:
            code: 待验证的验证码字符串
            remove_after_verify: 验证成功后是否减少使用次数，默认为True
        
        返回:
            tuple: (是否有效(bool), 消息(str))
        """
        if not code:
            return False, "验证码为空"
        
        code = code.strip()
        
        # 检查格式
        if len(code) != 27:
            return False, f"长度错误：应为27位（24位字符+3个分隔符），实际为{len(code)}位"
        
        pattern = r'^[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}$'
        if not re.match(pattern, code):
            return False, "格式错误：应为 XXXXXX-XXXXXX-XXXXXX-XXXXXX 格式（大写字母和数字）"
        
        # 检查验证码是否存在
        valid_codes = self.load_codes()
        if not valid_codes:
            return False, "验证失败：未找到已生成的验证码记录"
        
        if code not in valid_codes:
            return False, "验证失败：该验证码不存在或已被使用完毕"
        
        # 检查剩余使用次数
        remaining_uses = valid_codes[code]
        if remaining_uses <= 0:
            return False, "验证失败：该验证码使用次数已用完"
        
        # 验证成功，减少使用次数
        if remove_after_verify:
            valid_codes[code] -= 1
            remaining_uses = valid_codes[code]
            
            if remaining_uses <= 0:
                del valid_codes[code]
                self.save_codes(valid_codes)
                return True, "验证成功：验证码有效（已使用完毕）"
            else:
                self.save_codes(valid_codes)
                return True, f"验证成功：验证码有效（剩余使用次数: {remaining_uses}）"
        else:
            return True, f"验证成功：验证码有效（剩余使用次数: {remaining_uses}）"
    
    def get_all_codes(self) -> Dict[str, int]:
        """获取所有验证码"""
        return self.load_codes()
    
    def update_code_uses(self, code: str, new_uses: int) -> bool:
        """
        更新验证码的使用次数
        
        参数:
            code: 验证码
            new_uses: 新的使用次数
        
        返回:
            bool: 更新是否成功
        """
        if new_uses < 0:
            return False
        
        codes = self.load_codes()
        if code not in codes:
            return False
        
        codes[code] = new_uses
        if new_uses == 0:
            del codes[code]
        
        return self.save_codes(codes)
    
    def delete_code(self, code: str) -> bool:
        """
        删除指定的验证码
        
        参数:
            code: 要删除的验证码
        
        返回:
            bool: 删除是否成功
        """
        codes = self.load_codes()
        if code not in codes:
            return False
        
        del codes[code]
        return self.save_codes(codes)
    
    def get_statistics(self) -> Dict:
        """
        获取验证码统计信息
        
        返回:
            dict: 统计信息
        """
        codes = self.load_codes()
        total_codes = len(codes)
        total_uses = sum(codes.values())
        available_codes = len([c for c, u in codes.items() if u > 0])
        
        return {
            'total_codes': total_codes,
            'total_uses': total_uses,
            'available_codes': available_codes
        }

